import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class TargetRole(SQLModel, table=True):
    __tablename__ = "target_role"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="client.id", index=True)
    title: str
    seniority: str | None = None
    must_have_keywords: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
