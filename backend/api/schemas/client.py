import uuid
from datetime import datetime

from pydantic import BaseModel

from db.models.enums import ClientStatus


class ClientCreate(BaseModel):
    full_name: str
    email: str
    current_city: str | None = None
    current_state: str | None = None
    current_country: str | None = None
    timezone: str | None = None


class ClientUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    current_city: str | None = None
    current_state: str | None = None
    current_country: str | None = None
    timezone: str | None = None
    status: ClientStatus | None = None


class ClientRead(BaseModel):
    id: uuid.UUID
    bd_id: uuid.UUID
    full_name: str
    email: str
    current_city: str | None
    current_state: str | None
    current_country: str | None
    timezone: str | None
    status: ClientStatus
    created_at: datetime


class ResumeExtractionRead(BaseModel):
    full_name: str | None
    email: str | None
    current_city: str | None
    current_state: str | None
    current_country: str | None
    raw_text: str


class LinkedInTextExtractionRequest(BaseModel):
    text: str


class LinkedInUrlExtractionRequest(BaseModel):
    url: str
