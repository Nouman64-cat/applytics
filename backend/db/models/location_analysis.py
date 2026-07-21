import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class LocationAnalysis(SQLModel, table=True):
    __tablename__ = "location_analysis"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="client.id", index=True)
    target_role_id: uuid.UUID | None = Field(default=None, foreign_key="target_role.id")
    location_penalty_score: int
    recommendation: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
