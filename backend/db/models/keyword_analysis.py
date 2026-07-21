import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class KeywordAnalysis(SQLModel, table=True):
    __tablename__ = "keyword_analysis"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    profile_id: uuid.UUID = Field(foreign_key="profile.id", index=True)
    target_role_id: uuid.UUID | None = Field(default=None, foreign_key="target_role.id")
    extracted_keywords: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    missing_keywords: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    ats_score: int
    recruiter_attention_score: int
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
