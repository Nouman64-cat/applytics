from playwright.async_api import async_playwright

from db.models.enums import RemoteType
from services.scraper.base import JobFilters, JobScraper, ScrapedJob

SEARCH_URL = "https://jobright.ai/jobs/search"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

WORK_MODEL_VALUES = {"Remote", "Hybrid", "Onsite"}


def _work_model_to_remote_type(work_model: str | None) -> RemoteType:
    if work_model == "Remote":
        return RemoteType.fully_remote
    if work_model == "Hybrid":
        return RemoteType.hybrid
    if work_model == "Onsite":
        return RemoteType.onsite
    return RemoteType.unknown


class JobrightScraper(JobScraper):
    """Guest (no-login) adapter against Jobright.ai's public job feed.

    Registered under job_source name "jobwright" to match this project's existing
    seed data/migrations — "Jobright" is the real product name (jobright.ai).

    Important limitation, confirmed live: unauthenticated visitors only get a fixed
    ~20-item generic "recommended" feed. The `keyword` query param and the on-page
    filter chips (Company / Experience / Job Type / Work Model / Date Posted) do NOT
    actually filter results without signing in — confirmed by testing: identical
    results with and without a keyword param, no <input> element exists anywhere on
    the page for free-text search, and scrolling never grows the list past 20 cards
    (no guest pagination/infinite-scroll either). Real personalized/keyword search is
    an authenticated-only feature of this product.

    So this adapter does the best it honestly can: it scrapes the fixed guest feed
    and filters by keyword client-side against the title, since there's no server-side
    guest filtering to delegate to. For a narrow technical query, expect this source
    to return few or zero results most of the time — the guest feed skews toward
    generic/non-engineering roles, and there's nothing this adapter can do about that
    without an authenticated session. Work-model (remote/hybrid/onsite) is read
    directly from Jobright's own per-card label, which is actually a *more* reliable
    signal than the title/location-text heuristics the other adapters need.
    """

    source_name = "jobwright"

    async def fetch(self, filters: JobFilters) -> list[ScrapedJob]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(user_agent=USER_AGENT, viewport={"width": 1366, "height": 900})
                page = await context.new_page()
                try:
                    response = await page.goto(SEARCH_URL, timeout=30000, wait_until="domcontentloaded")
                except Exception as exc:
                    raise RuntimeError(f"Jobright page load failed: {exc}") from exc

                if response is None or response.status >= 400:
                    raise RuntimeError(f"Jobright returned HTTP {response.status if response else 'no response'}")

                await page.wait_for_timeout(3000)
                cards = await page.query_selector_all('a[href*="/jobs/info/"]')

                jobs: list[ScrapedJob] = []
                for card in cards:
                    job_id = await card.get_attribute("id")
                    href = await card.get_attribute("href")
                    if not job_id:
                        continue

                    title_el = await card.query_selector('[class*="job-title"]')
                    title = (await title_el.inner_text()).strip() if title_el else ""

                    company_el = await card.query_selector('[class*="company-name"]')
                    company = (await company_el.inner_text()).strip() if company_el else None

                    location_el = await card.query_selector('[class*="primary-location"]')
                    location_raw = (await location_el.inner_text()).strip() if location_el else None

                    card_text = await card.inner_text()
                    work_model = next((line for line in card_text.split("\n") if line in WORK_MODEL_VALUES), None)

                    apply_url = f"https://jobright.ai{href}" if href and href.startswith("/") else href

                    jobs.append(
                        ScrapedJob(
                            external_id=job_id,
                            title=title,
                            company=company,
                            location_raw=location_raw,
                            remote_type=_work_model_to_remote_type(work_model),
                            country=filters.country.upper(),
                            description=None,
                            apply_url=apply_url,
                            posted_at=None,
                            raw_payload={
                                "title": title,
                                "company": company,
                                "location": location_raw,
                                "work_model": work_model,
                            },
                        )
                    )
            finally:
                await browser.close()

        if filters.keywords:
            needle = filters.keywords.lower()
            jobs = [j for j in jobs if needle in j.title.lower()]

        if filters.remote_only:
            jobs = [j for j in jobs if j.remote_type == RemoteType.fully_remote]

        return jobs[: filters.max_results]
