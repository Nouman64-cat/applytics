import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from agents.comparison_agent import ComparisonState, build_comparison_graph
from agents.keyword_agent import analyze_keywords
from agents.location_agent import analyze_location
from db.models import (
    BusinessDeveloper,
    Client,
    ComparisonRun,
    KeywordAnalysis,
    LocationAnalysis,
    Profile,
    TargetRole,
)
from db.models.enums import AnalysisStatus
from services.client_service import get_client_scoped
from services.profile_service import get_profile_scoped


async def _get_target_role_scoped(
    session: AsyncSession, bd: BusinessDeveloper, target_role_id: uuid.UUID | None
) -> TargetRole | None:
    if target_role_id is None:
        return None
    target_role = await session.get(TargetRole, target_role_id)
    if target_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target role not found")
    await get_client_scoped(session, bd, target_role.client_id)
    return target_role


async def run_keyword_analysis(
    session: AsyncSession, bd: BusinessDeveloper, profile_id: uuid.UUID, target_role_id: uuid.UUID | None = None
) -> KeywordAnalysis:
    profile = await get_profile_scoped(session, bd, profile_id)
    target_role = await _get_target_role_scoped(session, bd, target_role_id or profile.target_role_id)

    output = await analyze_keywords(session, profile, target_role)

    record = KeywordAnalysis(
        profile_id=profile.id,
        target_role_id=target_role.id if target_role else None,
        extracted_keywords=output.extracted_keywords,
        missing_keywords=output.missing_keywords,
        ats_score=output.ats_score,
        recruiter_attention_score=output.recruiter_attention_score,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def run_location_analysis(
    session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID, target_role_id: uuid.UUID | None = None
) -> LocationAnalysis:
    client = await get_client_scoped(session, bd, client_id)
    target_role = await _get_target_role_scoped(session, bd, target_role_id)

    output = await analyze_location(session, client, target_role)

    record = LocationAnalysis(
        client_id=client.id,
        target_role_id=target_role.id if target_role else None,
        location_penalty_score=output.location_penalty_score,
        recommendation=output.recommendation,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def execute_comparison(
    session: AsyncSession,
    client: Client,
    profiles: list[Profile],
    target_role: TargetRole | None,
) -> ComparisonRun:
    """Core comparison logic, with no BD-ownership check.

    Callable directly by trusted system code (the feedback-loop background job) that
    doesn't act on behalf of any particular BD. User-facing callers must go through
    `run_comparison` below, which enforces client/profile ownership first.
    """
    run = ComparisonRun(
        client_id=client.id,
        target_role_id=target_role.id if target_role else None,
        profile_ids=[str(p.id) for p in profiles],
        status=AnalysisStatus.running,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    graph = build_comparison_graph(session)
    initial_state: ComparisonState = {
        "profiles": profiles,
        "target_role": target_role,
        "profile_scores": [],
        "result": None,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        result = final_state["result"]
    except Exception as exc:
        run.status = AnalysisStatus.failed
        run.result_summary = f"Comparison failed: {exc}"
        run.completed_at = datetime.now(timezone.utc)
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run

    run.status = AnalysisStatus.complete
    run.result_summary = result.summary
    run.result_detail = {
        "profile_scores": [s.model_dump() for s in final_state["profile_scores"]],
        "bottlenecks": result.bottlenecks,
    }
    run.winner_profile_id = uuid.UUID(result.winner_profile_id) if result.winner_profile_id else None
    run.completed_at = datetime.now(timezone.utc)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def run_comparison(
    session: AsyncSession,
    bd: BusinessDeveloper,
    client_id: uuid.UUID,
    profile_ids: list[uuid.UUID],
    target_role_id: uuid.UUID | None = None,
) -> ComparisonRun:
    if len(profile_ids) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least 2 profiles are required")

    client = await get_client_scoped(session, bd, client_id)
    target_role = await _get_target_role_scoped(session, bd, target_role_id)

    profiles = []
    for profile_id in profile_ids:
        profile = await get_profile_scoped(session, bd, profile_id)
        if profile.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="All profiles must belong to the same client"
            )
        profiles.append(profile)

    return await execute_comparison(session, client, profiles, target_role)


async def get_comparison_run(session: AsyncSession, bd: BusinessDeveloper, run_id: uuid.UUID) -> ComparisonRun:
    run = await session.get(ComparisonRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison run not found")
    await get_client_scoped(session, bd, run.client_id)
    return run
