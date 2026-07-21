import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TargetRoleCreate(BaseModel):
    title: str
    seniority: str | None = None
    must_have_keywords: list[str] = Field(default_factory=list)


class TargetRoleRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    seniority: str | None
    must_have_keywords: list[str]
    created_at: datetime
