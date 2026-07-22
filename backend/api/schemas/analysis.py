import uuid
from datetime import datetime

from pydantic import BaseModel, Field

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


class CrossClientComparisonRequest(BaseModel):
    profile_ids: list[uuid.UUID]
    role_title: str | None = None
    role_keywords: list[str] = Field(default_factory=list)


class ComparisonRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID | None
    target_role_id: uuid.UUID | None
    profile_ids: list[str]
    status: AnalysisStatus
    result_summary: str | None
    result_detail: dict
    winner_profile_id: uuid.UUID | None
    created_at: datetime
    completed_at: datetime | None


class JobMatchRequest(BaseModel):
    profile_id: uuid.UUID
    # If omitted, matches against the most recently scraped jobs instead of a specific set
    # (e.g. whatever the BD currently has filtered/visible on the Jobs page).
    job_ids: list[uuid.UUID] | None = None


class JobMatchItem(BaseModel):
    job_id: uuid.UUID
    score: int
    rationale: str
    title: str
    company: str | None
    location_raw: str | None
    remote_type: str
    apply_url: str | None


class JobMatchRead(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    client_id: uuid.UUID
    status: AnalysisStatus
    matches: list[JobMatchItem]
    created_at: datetime
    completed_at: datetime | None
