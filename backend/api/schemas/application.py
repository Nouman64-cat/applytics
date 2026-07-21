import uuid
from datetime import datetime

from pydantic import BaseModel

from db.models.enums import ApplicationStatus


class ApplicationCreate(BaseModel):
    client_id: uuid.UUID
    profile_id: uuid.UUID
    job_id: uuid.UUID
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None


class ApplicationRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    profile_id: uuid.UUID
    job_id: uuid.UUID
    applied_at: datetime
    status: ApplicationStatus
    status_updated_at: datetime
    notes: str | None
