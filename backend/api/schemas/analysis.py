import uuid
from datetime import datetime

from pydantic import BaseModel

from db.models.enums import AnalysisStatus


class KeywordAnalysisRequest(BaseModel):
    profile_id: uuid.UUID
    target_role_id: uuid.UUID | None = None


class KeywordAnalysisRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    target_role_id: uuid.UUID | None
    extracted_keywords: list[str]
    missing_keywords: list[str]
    ats_score: int
    recruiter_attention_score: int
    created_at: datetime


class LocationAnalysisRequest(BaseModel):
    client_id: uuid.UUID
    target_role_id: uuid.UUID | None = None


class LocationAnalysisRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    target_role_id: uuid.UUID | None
    location_penalty_score: int
    recommendation: str
    created_at: datetime


class ComparisonRequest(BaseModel):
    client_id: uuid.UUID
    profile_ids: list[uuid.UUID]
    target_role_id: uuid.UUID | None = None


class ComparisonRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    target_role_id: uuid.UUID | None
    profile_ids: list[str]
    status: AnalysisStatus
    result_summary: str | None
    result_detail: dict
    winner_profile_id: uuid.UUID | None
    created_at: datetime
    completed_at: datetime | None
