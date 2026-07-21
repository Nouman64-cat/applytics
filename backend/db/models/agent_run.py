import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_run"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_type: str = Field(index=True)
    related_entity_type: str
    related_entity_id: str
    model_name: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int
    status: str
    error_message: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
