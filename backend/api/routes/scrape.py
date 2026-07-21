import uuid

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.job import JobSourceRead, ScrapeRunCreate, ScrapeRunRead
from core.db import get_session
from core.deps import get_current_bd
from db.models import BusinessDeveloper
from services import scrape_service
from services.scraper.base import JobFilters

router = APIRouter(prefix="/scrape")


@router.get("/sources", response_model=list[JobSourceRead])
async def list_sources(
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[JobSourceRead]:
    sources = await scrape_service.list_job_sources(session)
    return [JobSourceRead.model_validate(s, from_attributes=True) for s in sources]


@router.post("/runs", response_model=ScrapeRunRead, status_code=201)
async def trigger_scrape(
    payload: ScrapeRunCreate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ScrapeRunRead:
    filters = JobFilters(
        keywords=payload.keywords,
        remote_only=payload.remote_only,
        country=payload.country,
        max_results=payload.max_results,
    )
    run = await scrape_service.run_scrape(session, payload.source, filters)
    return ScrapeRunRead.model_validate(run, from_attributes=True)


@router.get("/runs/{run_id}", response_model=ScrapeRunRead)
async def get_scrape_run(
    run_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ScrapeRunRead:
    run = await scrape_service.get_scrape_run(session, run_id)
    return ScrapeRunRead.model_validate(run, from_attributes=True)
