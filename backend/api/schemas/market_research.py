import uuid
from datetime import datetime

from pydantic import BaseModel


class AskRequest(BaseModel):
    session_id: uuid.UUID | None = None
    question: str


class ChatMessageRead(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    key_data_points: list[str]
    suggested_follow_ups: list[str]
    created_at: datetime


class ChatSessionRead(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
