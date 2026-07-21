import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from db.models.enums import ScrapeStatus


class ScrapeRun(SQLModel, table=True):
    __tablename__ = "scrape_run"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_source_id: uuid.UUID = Field(foreign_key="job_source.id", index=True)
    filters: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: ScrapeStatus = Field(default=ScrapeStatus.pending)
    jobs_found_count: int = Field(default=0)
    started_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    finished_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    error_message: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
