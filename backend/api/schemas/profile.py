import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from db.models.enums import ProfileType


class ProfileCreate(BaseModel):
    client_id: uuid.UUID
    target_role_id: uuid.UUID | None = None
    type: ProfileType
    variant_label: str
    source_url: str | None = None
    raw_text: str | None = None
    structured_data: dict = Field(default_factory=dict)


class ProfileRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    target_role_id: uuid.UUID | None
    type: ProfileType
    variant_label: str
    source_url: str | None
    raw_text: str | None
    structured_data: dict
    is_active: bool
    created_at: datetime
