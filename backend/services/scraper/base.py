from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field

from db.models.enums import RemoteType


class JobFilters(BaseModel):
    keywords: str | None = None
    remote_only: bool = True
    country: str = "us"
    max_results: int = 50


class ScrapedJob(BaseModel):
    external_id: str
    title: str
    company: str | None = None
    location_raw: str | None = None
    remote_type: RemoteType = RemoteType.unknown
    country: str | None = None
    description: str | None = None
    apply_url: str | None = None
    posted_at: datetime | None = None
    raw_payload: dict = Field(default_factory=dict)


class JobScraper(ABC):
    source_name: str

    @abstractmethod
    async def fetch(self, filters: JobFilters) -> list[ScrapedJob]: ...
