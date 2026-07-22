import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from db.models.enums import AnalysisStatus


class JobMatchRun(SQLModel, table=True):
    __tablename__ = "job_match_run"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    profile_id: uuid.UUID = Field(foreign_key="profile.id", index=True)
    client_id: uuid.UUID = Field(foreign_key="client.id", index=True)
    candidate_job_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: AnalysisStatus = Field(default=AnalysisStatus.pending)
    result_detail: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
