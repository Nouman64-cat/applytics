import uuid
from datetime import date, datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import and_, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Application, Job, JobSource
from db.models.enums import RemoteType


def _filtered_statement(
    *,
    count_only: bool,
    remote_type: RemoteType | None,
    country: str | None,
    source: str | None,
    keyword: str | None,
    posted_after: date | None,
    posted_before: date | None,
):
    statement = select(func.count()).select_from(Job) if count_only else select(Job)

    if source is not None:
        statement = statement.join(JobSource, Job.job_source_id == JobSource.id).where(JobSource.name == source)
    if remote_type is not None:
        statement = statement.where(Job.remote_type == remote_type)
    if country is not None:
        statement = statement.where(Job.country == country)
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(or_(Job.title.ilike(pattern), Job.description.ilike(pattern)))
    if posted_after is not None:
        # Several sources (Indeed/Glassdoor/Jobright) don't reliably expose a real posted
        # date, so posted_at is often null. Falling back to scraped_at for those rows
        # means a date filter judges them by when we found them instead of silently
        # excluding them outright.
        cutoff = datetime.combine(posted_after, time.min, tzinfo=timezone.utc)
        statement = statement.where(
            or_(Job.posted_at >= cutoff, and_(Job.posted_at.is_(None), Job.scraped_at >= cutoff))
        )
    if posted_before is not None:
        cutoff = datetime.combine(posted_before, time.max, tzinfo=timezone.utc)
        statement = statement.where(
            or_(Job.posted_at <= cutoff, and_(Job.posted_at.is_(None), Job.scraped_at <= cutoff))
        )

    return statement


async def list_jobs(
    session: AsyncSession,
    remote_type: RemoteType | None = None,
    country: str | None = None,
    source: str | None = None,
    keyword: str | None = None,
    posted_after: date | None = None,
    posted_before: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Job]:
    statement = _filtered_statement(
        count_only=False,
        remote_type=remote_type,
        country=country,
        source=source,
        keyword=keyword,
        posted_after=posted_after,
        posted_before=posted_before,
    )
    statement = statement.order_by(Job.scraped_at.desc()).offset(offset).limit(limit)
    result = await session.exec(statement)
    return list(result.all())


async def count_jobs(
    session: AsyncSession,
    remote_type: RemoteType | None = None,
    country: str | None = None,
    source: str | None = None,
    keyword: str | None = None,
    posted_after: date | None = None,
    posted_before: date | None = None,
) -> int:
    statement = _filtered_statement(
        count_only=True,
        remote_type=remote_type,
        country=country,
        source=source,
        keyword=keyword,
        posted_after=posted_after,
        posted_before=posted_before,
    )
    result = await session.execute(statement)
    return result.scalar_one()


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


async def _referenced_job_ids(session: AsyncSession, job_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    result = await session.exec(select(Application.job_id).where(Application.job_id.in_(job_ids)).distinct())
    return set(result.all())


async def delete_job(session: AsyncSession, job_id: uuid.UUID) -> None:
    job = await get_job(session, job_id)
    if await _referenced_job_ids(session, [job_id]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete this job — it has an application logged against it.",
        )
    await session.delete(job)
    await session.commit()


async def delete_jobs(session: AsyncSession, job_ids: list[uuid.UUID]) -> dict[str, int]:
    if not job_ids:
        return {"deleted": 0, "skipped": 0}

    referenced = await _referenced_job_ids(session, job_ids)
    deletable_ids = [jid for jid in job_ids if jid not in referenced]

    deleted = 0
    if deletable_ids:
        result = await session.exec(select(Job).where(Job.id.in_(deletable_ids)))
        jobs = result.all()
        for job in jobs:
            await session.delete(job)
        deleted = len(jobs)
        await session.commit()

    return {"deleted": deleted, "skipped": len(referenced)}
