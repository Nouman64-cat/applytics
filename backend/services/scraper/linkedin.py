from datetime import datetime
from urllib.parse import urlencode

from playwright.async_api import async_playwright

from db.models.enums import RemoteType
from services.scraper.base import UNBOUNDED_SAFETY_CAP, JobFilters, JobScraper, ScrapedJob

SEARCH_URL = "https://www.linkedin.com/jobs/search"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MAX_PAGES = 20


def _external_id(urn: str | None, href: str | None) -> str | None:
    if urn and ":" in urn:
        return urn.rsplit(":", 1)[-1]
    return href


def _parse_posted_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


class LinkedInScraper(JobScraper):
    """Guest (no-login) adapter against LinkedIn's public job search pages.

    No account is ever authenticated here, so there's no personal/company LinkedIn
    account at risk of a ban — but this still scrapes a site whose ToS prohibits it,
    and LinkedIn has the most aggressive anti-bot posture and the most legal history
    of any source integrated so far. Expect this to be the first adapter to break,
    get CAPTCHA'd, or get rate-limited/IP-blocked — including mid-pagination, in which
    case we stop and return whatever pages succeeded rather than failing the whole run.

    Unlike Adzuna/Glassdoor, LinkedIn's guest search exposes a genuine structured
    remote filter (f_WT=2) rather than a fuzzy keyword match — confirmed live: the
    same keywords returned ~12,000 unfiltered vs. ~1,000 with f_WT=2, and a sampled
    result's detail page explicitly described itself as open to remote work. So
    remote_only is enforced via that filter rather than a post-fetch title/location
    heuristic, and matches are trusted as fully_remote.
    """

    source_name = "linkedin"

    async def fetch(self, filters: JobFilters) -> list[ScrapedJob]:
        target = filters.max_results if filters.max_results is not None else UNBOUNDED_SAFETY_CAP
        jobs: list[ScrapedJob] = []
        seen_ids: set[str] = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(user_agent=USER_AGENT, viewport={"width": 1366, "height": 900})
                page = await context.new_page()

                start = 0
                page_num = 0
                while len(jobs) < target and page_num < MAX_PAGES:
                    params = {"keywords": filters.keywords or "jobs", "location": "United States"}
                    if filters.remote_only:
                        params["f_WT"] = "2"
                    if start:
                        params["start"] = start
                    url = f"{SEARCH_URL}?{urlencode(params)}"

                    try:
                        response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    except Exception as exc:
                        if jobs:
                            break
                        raise RuntimeError(f"LinkedIn page load failed: {exc}") from exc

                    if response is None or response.status >= 400:
                        if jobs:
                            break
                        raise RuntimeError(f"LinkedIn returned HTTP {response.status if response else 'no response'}")

                    await page.wait_for_timeout(2000)
                    cards = await page.query_selector_all("div.base-card")
                    if not cards:
                        break

                    new_count = 0
                    for card in cards:
                        urn = await card.get_attribute("data-entity-urn")
                        link_el = await card.query_selector("a.base-card__full-link")
                        href = (await link_el.get_attribute("href")) if link_el else None
                        external_id = _external_id(urn, href)
                        if not external_id or external_id in seen_ids:
                            continue
                        seen_ids.add(external_id)
                        new_count += 1

                        title_el = await card.query_selector(".base-search-card__title")
                        title = (await title_el.inner_text()).strip() if title_el else ""

                        company_el = await card.query_selector(".base-search-card__subtitle")
                        company = (await company_el.inner_text()).strip() if company_el else None

                        location_el = await card.query_selector(".job-search-card__location")
                        location_raw = (await location_el.inner_text()).strip() if location_el else None

                        date_el = await card.query_selector(".job-search-card__listdate, time")
                        posted_raw = (await date_el.get_attribute("datetime")) if date_el else None

                        jobs.append(
                            ScrapedJob(
                                external_id=external_id,
                                title=title,
                                company=company,
                                location_raw=location_raw,
                                remote_type=RemoteType.fully_remote if filters.remote_only else RemoteType.unknown,
                                country=filters.country.upper(),
                                description=None,
                                apply_url=href,
                                posted_at=_parse_posted_at(posted_raw),
                                raw_payload={
                                    "title": title,
                                    "company": company,
                                    "location": location_raw,
                                    "urn": urn,
                                },
                            )
                        )

                    if new_count == 0:
                        break

                    start += len(cards)
                    page_num += 1
            finally:
                await browser.close()

        return jobs[:target]
