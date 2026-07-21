import uuid
from datetime import datetime

from pydantic import BaseModel

from db.models.enums import RemoteType, ScrapeStatus


class JobRead(BaseModel):
    id: uuid.UUID
    job_source_id: uuid.UUID
    external_id: str
    title: str
    company: str | None
    location_raw: str | None
    remote_type: RemoteType
    country: str | None
    description: str | None
    apply_url: str | None
    posted_at: datetime | None
    scraped_at: datetime


class JobSourceRead(BaseModel):
    id: uuid.UUID
    name: str
    is_enabled: bool
    rate_limit_per_min: int | None


class ScrapeRunCreate(BaseModel):
    source: str
    keywords: str | None = None
    remote_only: bool = True
    country: str = "us"
    max_results: int = 50


class ScrapeRunRead(BaseModel):
    id: uuid.UUID
    job_source_id: uuid.UUID
    filters: dict
    status: ScrapeStatus
    jobs_found_count: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime
