import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import get_settings
from core.db import async_session_factory
from services.feedback_loop_service import refresh_stale_comparisons

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _run_refresh_job() -> None:
    settings = get_settings()
    async with async_session_factory() as session:
        try:
            triggered = await refresh_stale_comparisons(
                session, min_new_applications=settings.feedback_loop_min_applications
            )
            if triggered:
                logger.info("Feedback loop refreshed %d comparison run(s)", len(triggered))
        except Exception:
            logger.exception("Feedback loop refresh job failed")


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return
    scheduler.add_job(
        _run_refresh_job,
        "interval",
        hours=settings.feedback_loop_interval_hours,
        id="refresh_stale_comparisons",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
