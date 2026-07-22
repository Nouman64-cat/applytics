import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from db.models.enums import RemoteType


class Job(SQLModel, table=True):
    __tablename__ = "job"
    __table_args__ = (UniqueConstraint("job_source_id", "external_id", name="uq_job_source_external_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_source_id: uuid.UUID = Field(foreign_key="job_source.id", index=True)
    external_id: str = Field(index=True)
    title: str
    company: str | None = None
    location_raw: str | None = None
    remote_type: RemoteType = Field(default=RemoteType.unknown)
    country: str | None = None
    description: str | None = Field(default=None, sa_column=Column(Text))
    apply_url: str | None = None
    posted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    raw_payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    is_used: bool = Field(default=False)
