from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Keep only the top of the page — the profile header (name/headline/location) that guest
# view actually shows lives there; the rest is nav chrome, feed content, or an auth-wall
# modal that would just waste tokens.
MAX_CHARS = 4000


async def fetch_linkedin_profile_text(url: str) -> str:
    """Fetch the visible text of a public LinkedIn profile page in guest (no-login) mode.

    Individual profile pages are far more defended than LinkedIn's job-search pages
    (services/scraper/linkedin.py) — confirmed live during development: repeated guest
    requests can return HTTP 999, LinkedIn's own explicit bot-detection status code, and
    even successful requests may show little more than a name once a sign-in modal is
    injected. Treat a short/sparse result as an expected occasional outcome, not a bug —
    callers should surface a clear "try pasting the profile text instead" fallback.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(user_agent=USER_AGENT, viewport={"width": 1366, "height": 900})
            page = await context.new_page()
            try:
                response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except Exception as exc:
                raise RuntimeError(f"LinkedIn profile page load failed: {exc}") from exc

            if response is not None and response.status == 999:
                raise RuntimeError(
                    "LinkedIn blocked this request (bot detection) — try pasting the profile text instead"
                )
            if response is None or response.status >= 400:
                raise RuntimeError(f"LinkedIn returned HTTP {response.status if response else 'no response'}")

            await page.wait_for_timeout(2500)
            body_text = await page.inner_text("body")
        finally:
            await browser.close()

    return body_text[:MAX_CHARS]
