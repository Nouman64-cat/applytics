import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from db.models.enums import AnalysisStatus


class ComparisonRun(SQLModel, table=True):
    __tablename__ = "comparison_run"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Nullable: a cross-client comparison (two different candidates' resumes) doesn't
    # belong to a single client. Same-client A/B comparisons still set this.
    client_id: uuid.UUID | None = Field(default=None, foreign_key="client.id", index=True)
    target_role_id: uuid.UUID | None = Field(default=None, foreign_key="target_role.id")
    profile_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: AnalysisStatus = Field(default=AnalysisStatus.pending)
    result_summary: str | None = None
    result_detail: dict = Field(default_factory=dict, sa_column=Column(JSON))
    winner_profile_id: uuid.UUID | None = Field(default=None, foreign_key="profile.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
