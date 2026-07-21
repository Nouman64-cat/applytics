import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.job import JobRead
from core.db import get_session
from core.deps import get_current_bd
from db.models import BusinessDeveloper
from db.models.enums import RemoteType
from services import job_service

router = APIRouter(prefix="/jobs")


@router.get("", response_model=list[JobRead])
async def list_jobs(
    remote_type: RemoteType | None = None,
    country: str | None = None,
    source: str | None = None,
    keyword: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[JobRead]:
    jobs = await job_service.list_jobs(
        session,
        remote_type=remote_type,
        country=country,
        source=source,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    return [JobRead.model_validate(j, from_attributes=True) for j in jobs]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> JobRead:
    job = await job_service.get_job(session, job_id)
    return JobRead.model_validate(job, from_attributes=True)
