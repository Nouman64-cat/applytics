import uuid
from datetime import date, datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import and_, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Job, JobSource
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
