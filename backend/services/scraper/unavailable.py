from services.scraper.base import JobFilters, JobScraper, ScrapedJob


class UnavailableScraper(JobScraper):
    """Placeholder for sources without a settled access path yet.

    LinkedIn/Indeed/Glassdoor/Jobwright ToS generally prohibit direct scraping and
    actively block it. This adapter exists so the source is registered and visible
    via GET /scrape/sources, without pretending it can fetch anything — swap in a
    real implementation once official/partner API access is sorted (see plan.md).
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    async def fetch(self, filters: JobFilters) -> list[ScrapedJob]:
        raise NotImplementedError(
            f"'{self.source_name}' scraping is not implemented — needs official API or partner "
            "data access before it can be built (direct scraping risks ToS violations and IP bans)."
        )
