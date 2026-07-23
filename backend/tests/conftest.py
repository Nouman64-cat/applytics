import asyncio
import os
import re

# Redirect to a separate `..._test` database before any app module is imported —
# core.db and core.scheduler both build a module-level engine from DATABASE_URL at
# import time, so the env var must be rewritten first or tests would run against
# (and truncate) the real dev database.
_base_url = os.environ.get("DATABASE_URL", "")
if _base_url and not _base_url.rsplit("/", 1)[-1].split("?", 1)[0].endswith("_test"):
    _root, _, _tail = _base_url.rpartition("/")
    _db_name, _, _query = _tail.partition("?")
    _new_tail = f"{_db_name}_test" + (f"?{_query}" if _query else "")
    os.environ["DATABASE_URL"] = f"{_root}/{_new_tail}"

import uuid
from collections.abc import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlmodel import SQLModel

import db.models  # noqa: F401  registers tables on SQLModel.metadata
from agents.schemas import (
    ComparisonOutput,
    JobMatchOutput,
    JobMatchScore,
    KeywordAnalysisOutput,
    KeywordSuggestionOutput,
    LocationAnalysisOutput,
    MarketResearchAnswer,
    ProfileScore,
)
from core.config import get_settings
from core.db import async_session_factory, engine
from main import app

API = "/api/v1"


def _asyncpg_url(sqlalchemy_url: str) -> str:
    return sqlalchemy_url.replace("postgresql+asyncpg://", "postgresql://")


async def _ensure_database_exists() -> None:
    settings = get_settings()
    conn_url = _asyncpg_url(settings.database_url)
    base, _, db_name = conn_url.rpartition("/")
    conn = await asyncpg.connect(f"{base}/postgres")
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
def _setup_test_database():
    async def _setup():
        await _ensure_database_exists()
        async with engine.begin() as conn:
            # drop_all + create_all (not just create_all) so the test DB's schema can
            # never drift from the current models — `applytics_test` persists across
            # pytest runs in the same native Postgres, and create_all alone only adds
            # missing tables; it won't apply column-level changes (e.g. a NOT NULL ->
            # NULL migration) to tables that already exist from a previous run.
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
        async with async_session_factory() as session:
            from sqlmodel import select

            from db.models import JobSource

            for name, enabled in [("adzuna", True), ("linkedin", False), ("indeed", False), ("glassdoor", True)]:
                existing = (await session.exec(select(JobSource).where(JobSource.name == name))).first()
                if existing is None:
                    session.add(JobSource(name=name, is_enabled=enabled))
            await session.commit()

    asyncio.run(_setup())
    yield


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    # The async engine's pool is a module-level singleton bound to whichever event loop
    # first used it; pytest-asyncio gives each test its own loop, so pooled connections
    # from a prior test are invalid here ("attached to a different loop"). Disposing
    # forces fresh connections under the current test's loop.
    await engine.dispose()

    table_names = [t.name for t in SQLModel.metadata.sorted_tables if t.name != "job_source"]
    if table_names:
        async with engine.begin() as conn:
            await conn.execute(text(f'TRUNCATE TABLE {", ".join(table_names)} RESTART IDENTITY CASCADE'))
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator:
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    email = f"bd-{uuid.uuid4().hex[:10]}@example.com"
    password = "testpass123"
    await client.post(f"{API}/auth/register", json={"email": email, "password": password, "full_name": "Test BD"})
    resp = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _fake_run_structured(session, *, agent_type, related_entity_type, related_entity_id, prompt, output_model):
    if output_model is KeywordAnalysisOutput:
        return KeywordAnalysisOutput(
            extracted_keywords=["python", "fastapi"],
            missing_keywords=["aws"],
            ats_score=80,
            recruiter_attention_score=70,
            rationale="stubbed for tests",
        )
    if output_model is LocationAnalysisOutput:
        return LocationAnalysisOutput(location_penalty_score=50, recommendation="stubbed recommendation")
    if output_model is ProfileScore:
        return ProfileScore(profile_id=str(related_entity_id), strengths=["stub strength"], weaknesses=["stub weakness"], score=75)
    if output_model is ComparisonOutput:
        return ComparisonOutput(winner_profile_id=None, bottlenecks=["stub bottleneck"], summary="stubbed summary")
    if output_model is KeywordSuggestionOutput:
        return KeywordSuggestionOutput(keywords=["backend engineer", "senior backend engineer", "python developer"])
    if output_model is JobMatchOutput:
        # Pull a real candidate job id out of the prompt so the service's hallucinated-id
        # guard (matching returned ids against the actual candidate set) has something
        # genuine to accept, rather than trivially filtering everything out.
        found = re.search(r"id: ([0-9a-fA-F-]{36})", prompt)
        job_id = found.group(1) if found else "00000000-0000-0000-0000-000000000000"
        return JobMatchOutput(matches=[JobMatchScore(job_id=job_id, score=88, rationale="stubbed rationale")])
    raise AssertionError(f"unexpected output_model in test stub: {output_model}")


@pytest.fixture
def mock_llm(monkeypatch):
    """Stubs every agent's LLM call so tests are fast, free, and deterministic —
    no real OpenAI credits spent running the suite."""
    monkeypatch.setattr("agents.keyword_agent.run_structured", _fake_run_structured)
    monkeypatch.setattr("agents.location_agent.run_structured", _fake_run_structured)
    monkeypatch.setattr("agents.comparison_agent.run_structured", _fake_run_structured)
    monkeypatch.setattr("agents.keyword_suggestion_agent.run_structured", _fake_run_structured)
    monkeypatch.setattr("agents.job_match_agent.run_structured", _fake_run_structured)


async def _fake_run_gemini_structured(
    session, *, agent_type, related_entity_type, related_entity_id, contents, output_model, model_name, system_instruction=None
):
    if output_model is MarketResearchAnswer:
        return MarketResearchAnswer(
            answer="stubbed market research answer",
            key_data_points=["stub data point"],
            suggested_follow_ups=["stub follow-up question?"],
        )
    raise AssertionError(f"unexpected output_model in gemini test stub: {output_model}")


@pytest.fixture
def mock_s3(monkeypatch):
    """Stubs services.s3_service's boto3 calls with an in-memory fake, so tests don't
    hit real AWS. Both client_document_service and client_service call these via
    `s3_service.<fn>(...)` (a module-attribute lookup at call time, not a copied name
    import), so patching the functions on services.s3_service itself is enough to cover
    every caller — unlike the run_structured pattern above, no per-consumer patching
    needed."""
    store: dict[str, bytes] = {}

    def _fake_upload_file(key, content, content_type):
        store[key] = content

    def _fake_generate_presigned_url(key, expires_in=900):
        return f"https://fake-s3.test/{key}?expires_in={expires_in}"

    def _fake_delete_file(key):
        store.pop(key, None)

    monkeypatch.setattr("services.s3_service.upload_file", _fake_upload_file)
    monkeypatch.setattr("services.s3_service.generate_presigned_url", _fake_generate_presigned_url)
    monkeypatch.setattr("services.s3_service.delete_file", _fake_delete_file)
    return store


@pytest.fixture
def mock_gemini_chat(monkeypatch):
    """Stubs the Gemini-backed market-research agent so tests are fast, free, and
    deterministic — no real Gemini credits spent running the suite. Note:
    resume_extraction_agent's Gemini calls remain unmocked/untested — a pre-existing
    gap in this repo, not introduced here."""
    monkeypatch.setattr("agents.market_research_agent.run_gemini_structured", _fake_run_gemini_structured)
