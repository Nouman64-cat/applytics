import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Text
from sqlmodel import Field, SQLModel


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="chat_session.id", index=True)
    role: str = Field(description="'user' or 'assistant'")
    content: str = Field(sa_column=Column(Text))
    key_data_points: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    suggested_follow_ups: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
