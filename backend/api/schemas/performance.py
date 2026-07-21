import uuid

from pydantic import BaseModel


class ProfilePerformanceRead(BaseModel):
    profile_id: uuid.UUID
    variant_label: str
    total_applications: int
    status_counts: dict[str, int]
    interview_rate: float | None
