from datetime import datetime

import httpx

from core.config import get_settings
from db.models.enums import RemoteType
from services.scraper.base import JobFilters, JobScraper, ScrapedJob

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


def _parse_posted_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _guess_remote_type(location_raw: str | None, title: str) -> RemoteType:
    # Deliberately excludes the job description: free-text prose routinely contains
    # negated mentions ("no remote work", "not a remote position") that would false-
    # positive on a plain substring match. location/title are short, structured
    # fields where "remote" reliably means the posting is tagged remote.
    haystack = " ".join(filter(None, [location_raw, title])).lower()
    if "remote" in haystack:
        return RemoteType.fully_remote
    if "hybrid" in haystack:
        return RemoteType.hybrid
    return RemoteType.unknown


def parse_adzuna_result(item: dict) -> ScrapedJob:
    location_raw = (item.get("location") or {}).get("display_name")
    title = item.get("title", "")
    description = item.get("description")

    return ScrapedJob(
        external_id=str(item["id"]),
        title=title,
        company=(item.get("company") or {}).get("display_name"),
        location_raw=location_raw,
        remote_type=_guess_remote_type(location_raw, title),
        country=(item.get("location") or {}).get("area", [None])[0],
        description=description,
        apply_url=item.get("redirect_url"),
        posted_at=_parse_posted_at(item.get("created")),
        raw_payload=item,
    )


class AdzunaScraper(JobScraper):
    """Real adapter against Adzuna's official public Jobs API.

    Requires a free developer account at https://developer.adzuna.com/ —
    set ADZUNA_APP_ID / ADZUNA_APP_KEY in .env.
    """

    source_name = "adzuna"

    async def fetch(self, filters: JobFilters) -> list[ScrapedJob]:
        settings = get_settings()
        if not settings.adzuna_app_id or not settings.adzuna_app_key:
            raise RuntimeError(
                "Adzuna credentials not configured — set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env "
                "(free account at https://developer.adzuna.com/)"
            )

        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "results_per_page": min(filters.max_results, 50),
            "content-type": "application/json",
        }
        what = filters.keywords or ""
        if filters.remote_only:
            what = f"{what} remote".strip()
        if what:
            params["what"] = what

        url = f"{ADZUNA_BASE_URL}/{filters.country}/search/1"

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        jobs = [parse_adzuna_result(item) for item in data.get("results", [])]

        if filters.remote_only:
            jobs = [j for j in jobs if j.remote_type == RemoteType.fully_remote]

        return jobs
