from urllib.parse import urlencode

from playwright.async_api import async_playwright

from db.models.enums import RemoteType
from services.scraper.base import UNBOUNDED_SAFETY_CAP, JobFilters, JobScraper, ScrapedJob

SEARCH_URL = "https://www.glassdoor.com/Job/jobs.htm"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MAX_PAGES = 20

# Glassdoor's search matches "remote" fuzzily against keywords/description, not as a
# hard filter — onsite roles routinely show up in a "... remote" keyword search. So we
# still apply a title/location-only heuristic post-filter, same as the Adzuna adapter
# (and for the same reason: description text false-positives on phrases like "no remote work").


def _guess_remote_type(location_raw: str | None, title: str) -> RemoteType:
    haystack = " ".join(filter(None, [location_raw, title])).lower()
    if "remote" in haystack:
        return RemoteType.fully_remote
    if "hybrid" in haystack:
        return RemoteType.hybrid
    return RemoteType.unknown


class GlassdoorScraper(JobScraper):
    """Headless-browser adapter against Glassdoor's public job search (no official API).

    Uses Playwright/Chromium since results are client-rendered. This is inherently
    more fragile than an official API adapter: Glassdoor can change its markup, rate
    limit, or serve a CAPTCHA/bot-check at any time without notice — a failure here
    should be expected occasionally, not treated as a code bug. If a later page in a
    multi-page run fails, we stop and keep whatever pages already succeeded.
    """

    source_name = "glassdoor"

    async def fetch(self, filters: JobFilters) -> list[ScrapedJob]:
        keyword = filters.keywords or "jobs"
        if filters.remote_only and "remote" not in keyword.lower():
            keyword = f"{keyword} remote"

        target = filters.max_results if filters.max_results is not None else UNBOUNDED_SAFETY_CAP
        jobs: list[ScrapedJob] = []
        seen_ids: set[str] = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(user_agent=USER_AGENT, viewport={"width": 1366, "height": 900})
                page = await context.new_page()

                page_num = 1
                loop_count = 0
                while len(jobs) < target and loop_count < MAX_PAGES:
                    params = {"sc.keyword": keyword}
                    if page_num > 1:
                        params["p"] = page_num
                    url = f"{SEARCH_URL}?{urlencode(params)}"

                    try:
                        response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    except Exception as exc:
                        if jobs:
                            break
                        raise RuntimeError(f"Glassdoor page load failed: {exc}") from exc

                    if response is None or response.status >= 400:
                        if jobs:
                            break
                        raise RuntimeError(f"Glassdoor returned HTTP {response.status if response else 'no response'}")

                    await page.wait_for_timeout(2000)
                    cards = await page.query_selector_all('[data-test="jobListing"]')
                    if not cards:
                        break

                    new_count = 0
                    for card in cards:
                        job_id = await card.get_attribute("data-jobid")
                        if not job_id or job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)
                        new_count += 1

                        title_el = await card.query_selector('[data-test="job-title"]')
                        title = (await title_el.inner_text()).strip() if title_el else ""
                        apply_url = (await title_el.get_attribute("href")) if title_el else None

                        location_el = await card.query_selector('[data-test="emp-location"]')
                        location_raw = (await location_el.inner_text()).strip() if location_el else None

                        company_el = await card.query_selector('[class*="EmployerName"]')
                        company = (await company_el.inner_text()).strip() if company_el else None

                        desc_el = await card.query_selector('[data-test="descSnippet"]')
                        description = (await desc_el.inner_text()).strip() if desc_el else None

                        jobs.append(
                            ScrapedJob(
                                external_id=job_id,
                                title=title,
                                company=company,
                                location_raw=location_raw,
                                remote_type=_guess_remote_type(location_raw, title),
                                country=filters.country.upper(),
                                description=description,
                                apply_url=apply_url,
                                posted_at=None,
                                raw_payload={"title": title, "company": company, "location": location_raw},
                            )
                        )

                    if new_count == 0:
                        break

                    page_num += 1
                    loop_count += 1
            finally:
                await browser.close()

        if filters.remote_only:
            jobs = [j for j in jobs if j.remote_type == RemoteType.fully_remote]

        return jobs[:target]
