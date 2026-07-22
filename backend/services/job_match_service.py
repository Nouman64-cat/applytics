import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from agents.job_match_agent import match_jobs_to_resume
from db.models import BusinessDeveloper, Job, JobMatchRun
from db.models.enums import AnalysisStatus
from services.profile_service import get_profile_scoped

# Sending every scraped job to the LLM isn't viable (prompt size/cost), so candidates are
# capped — either the caller's explicit job_ids (e.g. whatever's currently filtered/visible
# on the Jobs page) or, if none given, the most recently scraped jobs as a reasonable default.
DEFAULT_CANDIDATE_LIMIT = 30
MAX_CANDIDATE_LIMIT = 50


async def match_jobs_for_profile(
    session: AsyncSession,
    bd: BusinessDeveloper,
    profile_id: uuid.UUID,
    job_ids: list[uuid.UUID] | None = None,
) -> JobMatchRun:
    profile = await get_profile_scoped(session, bd, profile_id)

    if job_ids:
        capped_ids = job_ids[:MAX_CANDIDATE_LIMIT]
        result = await session.exec(select(Job).where(Job.id.in_(capped_ids)))
        jobs = list(result.all())
    else:
        result = await session.exec(select(Job).order_by(Job.scraped_at.desc()).limit(DEFAULT_CANDIDATE_LIMIT))
        jobs = list(result.all())

    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No scraped jobs available to match against — run a scrape first.",
        )

    run = JobMatchRun(
        profile_id=profile.id,
        client_id=profile.client_id,
        candidate_job_ids=[str(job.id) for job in jobs],
        status=AnalysisStatus.running,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    try:
        output = await match_jobs_to_resume(session, profile.id, profile.raw_text or "", jobs)
    except Exception as exc:
        run.status = AnalysisStatus.failed
        run.result_detail = {"error": str(exc)}
        run.completed_at = datetime.now(timezone.utc)
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run

    jobs_by_id = {str(job.id): job for job in jobs}
    matches = []
    for match in output.matches:
        job = jobs_by_id.get(match.job_id)
        if job is None:
            continue  # guard against a hallucinated/mismatched id rather than surfacing bogus data
        matches.append(
            {
                "job_id": str(job.id),
                "score": match.score,
                "rationale": match.rationale,
                "title": job.title,
                "company": job.company,
                "location_raw": job.location_raw,
                "remote_type": job.remote_type.value,
                "apply_url": job.apply_url,
                "is_used": job.is_used,
            }
        )
    matches.sort(key=lambda m: m["score"], reverse=True)

    run.status = AnalysisStatus.complete
    run.result_detail = {"matches": matches}
    run.completed_at = datetime.now(timezone.utc)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run
