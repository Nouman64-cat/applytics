from fastapi import HTTPException, status

from services.scraper.adzuna import AdzunaScraper
from services.scraper.base import JobScraper
from services.scraper.glassdoor import GlassdoorScraper
from services.scraper.indeed import IndeedScraper
from services.scraper.jobright import JobrightScraper
from services.scraper.linkedin import LinkedInScraper

KNOWN_SOURCES = ["adzuna", "linkedin", "indeed", "glassdoor", "jobwright"]

_SCRAPERS: dict[str, JobScraper] = {
    "adzuna": AdzunaScraper(),
    "linkedin": LinkedInScraper(),
    "indeed": IndeedScraper(),
    "glassdoor": GlassdoorScraper(),
    "jobwright": JobrightScraper(),
}


def get_scraper(source_name: str) -> JobScraper:
    scraper = _SCRAPERS.get(source_name)
    if scraper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown job source '{source_name}'")
    return scraper
