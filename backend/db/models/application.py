import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from db.models.enums import ApplicationStatus


class Application(SQLModel, table=True):
    __tablename__ = "application"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="client.id", index=True)
    profile_id: uuid.UUID = Field(foreign_key="profile.id", index=True)
    job_id: uuid.UUID = Field(foreign_key="job.id", index=True)
    applied_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    status: ApplicationStatus = Field(default=ApplicationStatus.applied)
    status_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    notes: str | None = None
