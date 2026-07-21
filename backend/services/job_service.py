import uuid

from fastapi import HTTPException, status
from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Job, JobSource
from db.models.enums import RemoteType


async def list_jobs(
    session: AsyncSession,
    remote_type: RemoteType | None = None,
    country: str | None = None,
    source: str | None = None,
    keyword: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Job]:
    statement = select(Job)

    if source is not None:
        statement = statement.join(JobSource, Job.job_source_id == JobSource.id).where(JobSource.name == source)
    if remote_type is not None:
        statement = statement.where(Job.remote_type == remote_type)
    if country is not None:
        statement = statement.where(Job.country == country)
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(or_(Job.title.ilike(pattern), Job.description.ilike(pattern)))

    statement = statement.order_by(Job.scraped_at.desc()).offset(offset).limit(limit)
    result = await session.exec(statement)
    return list(result.all())


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
