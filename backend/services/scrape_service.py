from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Job, JobSource, ScrapeRun
from db.models.enums import ScrapeStatus
from services.scraper.base import JobFilters
from services.scraper.registry import get_scraper


async def get_job_source(session: AsyncSession, name: str) -> JobSource:
    result = await session.exec(select(JobSource).where(JobSource.name == name))
    source = result.first()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown job source '{name}'")
    return source


async def list_job_sources(session: AsyncSession) -> list[JobSource]:
    result = await session.exec(select(JobSource))
    return list(result.all())


async def _upsert_job(session: AsyncSession, source: JobSource, scraped) -> None:
    result = await session.exec(
        select(Job).where(Job.job_source_id == source.id, Job.external_id == scraped.external_id)
    )
    job = result.first()
    if job is None:
        job = Job(job_source_id=source.id, external_id=scraped.external_id)

    job.title = scraped.title
    job.company = scraped.company
    job.location_raw = scraped.location_raw
    job.remote_type = scraped.remote_type
    job.country = scraped.country
    job.description = scraped.description
    job.apply_url = scraped.apply_url
    job.posted_at = scraped.posted_at
    job.raw_payload = scraped.raw_payload
    job.scraped_at = datetime.now(timezone.utc)
    session.add(job)


async def run_scrape(session: AsyncSession, source_name: str, filters: JobFilters) -> ScrapeRun:
    source = await get_job_source(session, source_name)
    if not source.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job source '{source_name}' is not enabled yet",
        )

    scraper = get_scraper(source_name)

    run = ScrapeRun(
        job_source_id=source.id,
        filters=filters.model_dump(),
        status=ScrapeStatus.running,
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    try:
        scraped_jobs = await scraper.fetch(filters)
    except Exception as exc:
        run.status = ScrapeStatus.failed
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run

    for scraped in scraped_jobs:
        await _upsert_job(session, source, scraped)

    run.status = ScrapeStatus.success
    run.jobs_found_count = len(scraped_jobs)
    run.finished_at = datetime.now(timezone.utc)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def get_scrape_run(session: AsyncSession, run_id) -> ScrapeRun:
    run = await session.get(ScrapeRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scrape run not found")
    return run
