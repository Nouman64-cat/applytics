from urllib.parse import urlencode

from playwright.async_api import async_playwright

from db.models.enums import RemoteType
from services.scraper.base import JobFilters, JobScraper, ScrapedJob

SEARCH_URL = "https://www.indeed.com/jobs"
# Indeed's own internal id for its "Remote" pay/work-type filter chip — confirmed live:
# with it, all sampled cards' location text read "Remote"/"Remote in <city>"; without it,
# the same query returns a mix of onsite roles too. Not officially documented, may rot.
REMOTE_FILTER_ID = "032b3046-06a3-4876-8dfd-474eb5e7ed11"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _guess_remote_type(location_raw: str | None, title: str) -> RemoteType:
    haystack = " ".join(filter(None, [location_raw, title])).lower()
    if "remote" in haystack:
        return RemoteType.fully_remote
    if "hybrid" in haystack:
        return RemoteType.hybrid
    return RemoteType.unknown


class IndeedScraper(JobScraper):
    """Guest (no-login) adapter against Indeed's public job search pages.

    Indeed runs Cloudflare bot-detection that can serve a "Just a moment..."
    interstitial challenge instead of results — observed live when rapidly
    re-navigating the same browser context with a different query. A fresh browser
    per fetch() call (as used here and by every other adapter) avoided this across
    repeated live tests, but it should still be treated as an occasional failure
    mode, not something this adapter can fully prevent — see the explicit check
    below, which fails loudly (recorded as a failed ScrapeRun) rather than silently
    returning zero jobs when challenged.
    """

    source_name = "indeed"

    async def fetch(self, filters: JobFilters) -> list[ScrapedJob]:
        params = {"q": filters.keywords or "jobs"}
        if filters.remote_only:
            params["remotejob"] = REMOTE_FILTER_ID

        url = f"{SEARCH_URL}?{urlencode(params)}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(user_agent=USER_AGENT, viewport={"width": 1366, "height": 900})
                page = await context.new_page()
                try:
                    response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                except Exception as exc:
                    raise RuntimeError(f"Indeed page load failed: {exc}") from exc

                if response is None or response.status >= 400:
                    raise RuntimeError(f"Indeed returned HTTP {response.status if response else 'no response'}")

                await page.wait_for_timeout(2500)

                page_title = await page.title()
                if "just a moment" in page_title.lower():
                    raise RuntimeError("Indeed served a Cloudflare bot-check instead of results")

                cards = await page.query_selector_all("div.job_seen_beacon")

                jobs: list[ScrapedJob] = []
                for card in cards[: filters.max_results]:
                    link_el = await card.query_selector("a.jcs-JobTitle")
                    job_key = (await link_el.get_attribute("data-jk")) if link_el else None
                    if not job_key:
                        continue

                    title_el = await card.query_selector("h3.jobTitle span")
                    title = (await title_el.inner_text()).strip() if title_el else ""

                    company_el = await card.query_selector('[data-testid="company-name"]')
                    company = (await company_el.inner_text()).strip() if company_el else None

                    location_el = await card.query_selector('[data-testid="text-location"]')
                    location_raw = (await location_el.inner_text()).strip() if location_el else None

                    href = (await link_el.get_attribute("href")) if link_el else None
                    apply_url = f"https://www.indeed.com{href}" if href and href.startswith("/") else href

                    jobs.append(
                        ScrapedJob(
                            external_id=job_key,
                            title=title,
                            company=company,
                            location_raw=location_raw,
                            remote_type=_guess_remote_type(location_raw, title),
                            country=filters.country.upper(),
                            description=None,
                            apply_url=apply_url,
                            posted_at=None,
                            raw_payload={"title": title, "company": company, "location": location_raw},
                        )
                    )
            finally:
                await browser.close()

        if filters.remote_only:
            jobs = [j for j in jobs if j.remote_type == RemoteType.fully_remote]

        return jobs
