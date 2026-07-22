from datetime import datetime, timedelta, timezone

from sqlmodel import select

from db.models import (
    Application,
    BusinessDeveloper,
    Client,
    ComparisonRun,
    Job,
    JobSource,
    KeywordAnalysis,
    Profile,
    ScrapeRun,
    TargetRole,
)
from db.models.enums import AnalysisStatus, ApplicationStatus, ScrapeStatus
from services.market_snapshot_service import build_market_snapshot
from tests.conftest import API


async def _make_job(db_session, source_name: str, external_id: str, title: str = "Backend Engineer") -> Job:
    source = (await db_session.exec(select(JobSource).where(JobSource.name == source_name))).first()
    job = Job(job_source_id=source.id, external_id=external_id, title=title)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_ask_creates_session_and_replies(client, auth_headers, mock_gemini_chat):
    resp = await client.post(
        f"{API}/market-research/ask",
        json={"session_id": None, "question": "What positions are trending right now?"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "assistant"
    assert body["content"] == "stubbed market research answer"
    assert body["key_data_points"] == ["stub data point"]
    session_id = body["session_id"]

    sessions_resp = await client.get(f"{API}/market-research/sessions", headers=auth_headers)
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert sessions[0]["title"].startswith("What positions")

    messages_resp = await client.get(f"{API}/market-research/sessions/{session_id}/messages", headers=auth_headers)
    assert messages_resp.status_code == 200
    messages = messages_resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


async def test_ask_continues_existing_session(client, auth_headers, mock_gemini_chat):
    first = await client.post(
        f"{API}/market-research/ask",
        json={"session_id": None, "question": "Is there a market dip?"},
        headers=auth_headers,
    )
    session_id = first.json()["session_id"]

    second = await client.post(
        f"{API}/market-research/ask",
        json={"session_id": session_id, "question": "Why is that happening?"},
        headers=auth_headers,
    )
    assert second.status_code == 201
    assert second.json()["session_id"] == session_id

    messages_resp = await client.get(f"{API}/market-research/sessions/{session_id}/messages", headers=auth_headers)
    assert len(messages_resp.json()) == 4

    sessions_resp = await client.get(f"{API}/market-research/sessions", headers=auth_headers)
    assert len(sessions_resp.json()) == 1


async def test_session_not_visible_to_other_bd(client, auth_headers, mock_gemini_chat):
    created = await client.post(
        f"{API}/market-research/ask",
        json={"session_id": None, "question": "Which sources produce the most jobs?"},
        headers=auth_headers,
    )
    session_id = created.json()["session_id"]

    other_email = "other-bd@example.com"
    await client.post(
        f"{API}/auth/register", json={"email": other_email, "password": "testpass123", "full_name": "Other BD"}
    )
    login = await client.post(f"{API}/auth/login", json={"email": other_email, "password": "testpass123"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get(f"{API}/market-research/sessions/{session_id}/messages", headers=other_headers)
    assert resp.status_code == 404

    other_sessions = await client.get(f"{API}/market-research/sessions", headers=other_headers)
    assert other_sessions.json() == []


async def test_market_snapshot_aggregates(db_session):
    now = datetime.now(timezone.utc)

    adzuna_job = await _make_job(db_session, "adzuna", "snap-adzuna-1", title="Backend Engineer")
    adzuna_job.scraped_at = now - timedelta(days=5)
    glassdoor_job = await _make_job(db_session, "glassdoor", "snap-glassdoor-1", title="backend engineer")
    glassdoor_job.scraped_at = now - timedelta(days=40)
    db_session.add_all([adzuna_job, glassdoor_job])
    await db_session.commit()

    source = (await db_session.exec(select(JobSource).where(JobSource.name == "adzuna"))).first()
    db_session.add(
        ScrapeRun(job_source_id=source.id, status=ScrapeStatus.success, jobs_found_count=1, created_at=now)
    )
    await db_session.commit()

    bd = BusinessDeveloper(email="snapshot-bd@example.com", hashed_password="x", full_name="Snap BD")
    db_session.add(bd)
    await db_session.commit()
    await db_session.refresh(bd)

    test_client = Client(bd_id=bd.id, full_name="Snap Client", email="snapclient@example.com")
    db_session.add(test_client)
    await db_session.commit()
    await db_session.refresh(test_client)

    target_role = TargetRole(client_id=test_client.id, title="Backend Engineer")
    db_session.add(target_role)
    await db_session.commit()
    await db_session.refresh(target_role)

    profile = Profile(client_id=test_client.id, target_role_id=target_role.id, type="resume", variant_label="A")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    db_session.add(
        Application(
            client_id=test_client.id,
            profile_id=profile.id,
            job_id=adzuna_job.id,
            status=ApplicationStatus.interview,
        )
    )
    await db_session.commit()

    snapshot = await build_market_snapshot(db_session, bd)

    assert snapshot["job_counts_by_source_last_window"].get("adzuna") == 1
    assert "adzuna" not in snapshot["job_counts_by_source_prior_window"] or (
        snapshot["job_counts_by_source_prior_window"].get("adzuna", 0) == 0
    )
    assert snapshot["job_counts_by_source_prior_window"].get("glassdoor") == 1

    titles = {t["title"]: t["count"] for t in snapshot["top_job_titles"]}
    assert titles.get("backend engineer") == 2

    assert snapshot["applications_by_source"].get("adzuna") == 1
    assert snapshot["applications_by_target_role"].get("Backend Engineer") == 1
    assert snapshot["application_status_funnel"].get("interview") == 1
    assert snapshot["scrape_health_by_source"].get("adzuna", {}).get("success") == 1

    candidate_rows = snapshot["candidate_resume_performance"]
    assert len(candidate_rows) == 1
    row = candidate_rows[0]
    assert row["client_name"] == "Snap Client"
    assert row["target_role"] == "Backend Engineer"
    assert row["total_applications"] == 1
    assert row["interview_rate"] == 1.0
    assert row["status_counts"] == {"interview": 1}
    assert row["ats_score"] is None


async def test_market_snapshot_compares_two_candidates_for_same_role(db_session):
    bd = BusinessDeveloper(email="two-candidate-bd@example.com", hashed_password="x", full_name="Two Candidate BD")
    db_session.add(bd)
    await db_session.commit()
    await db_session.refresh(bd)

    job = await _make_job(db_session, "adzuna", "snap-two-candidate-1", title="ServiceNow Developer")

    async def _make_candidate(name: str, ats_score: int, missing_keywords: list[str], applications: int):
        client_row = Client(bd_id=bd.id, full_name=name, email=f"{name.lower().replace(' ', '.')}@example.com")
        db_session.add(client_row)
        await db_session.commit()
        await db_session.refresh(client_row)

        target_role = TargetRole(client_id=client_row.id, title="ServiceNow Developer")
        db_session.add(target_role)
        await db_session.commit()
        await db_session.refresh(target_role)

        profile = Profile(client_id=client_row.id, target_role_id=target_role.id, type="resume", variant_label="A")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)

        db_session.add(
            KeywordAnalysis(
                profile_id=profile.id,
                target_role_id=target_role.id,
                extracted_keywords=["itsm"],
                missing_keywords=missing_keywords,
                ats_score=ats_score,
                recruiter_attention_score=ats_score,
            )
        )
        for _ in range(applications):
            db_session.add(
                Application(
                    client_id=client_row.id,
                    profile_id=profile.id,
                    job_id=job.id,
                    status=ApplicationStatus.interview,
                )
            )
        await db_session.commit()
        return client_row, profile

    strong_client, strong_profile = await _make_candidate(
        "Strong Candidate", ats_score=90, missing_keywords=[], applications=3
    )
    weak_client, weak_profile = await _make_candidate(
        "Weak Candidate", ats_score=40, missing_keywords=["itil certification"], applications=1
    )

    db_session.add(
        ComparisonRun(
            client_id=None,
            profile_ids=[str(strong_profile.id), str(weak_profile.id)],
            status=AnalysisStatus.complete,
            result_summary="Strong Candidate's resume is more directly relevant to ServiceNow development.",
            result_detail={
                "profile_scores": [
                    {"profile_id": str(strong_profile.id), "strengths": ["itsm depth"], "weaknesses": [], "score": 90},
                    {"profile_id": str(weak_profile.id), "strengths": [], "weaknesses": ["missing certs"], "score": 40},
                ],
                "bottlenecks": ["missing certs"],
            },
            winner_profile_id=strong_profile.id,
        )
    )
    await db_session.commit()

    snapshot = await build_market_snapshot(db_session, bd)
    by_name = {row["client_name"]: row for row in snapshot["candidate_resume_performance"]}

    assert by_name["Strong Candidate"]["ats_score"] == 90
    assert by_name["Strong Candidate"]["interview_rate"] == 1.0
    assert by_name["Weak Candidate"]["ats_score"] == 40
    assert by_name["Weak Candidate"]["missing_keywords"] == ["itil certification"]

    comparisons = snapshot["recent_resume_comparisons"]
    assert len(comparisons) == 1
    comparison = comparisons[0]
    assert comparison["winner"] == "Strong Candidate (A)"
    assert {c["candidate"]: c["score"] for c in comparison["candidates"]} == {
        "Strong Candidate (A)": 90,
        "Weak Candidate (A)": 40,
    }
    assert "ServiceNow" in comparison["summary"]
