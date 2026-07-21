import enum


class BDRole(str, enum.Enum):
    bd = "bd"
    admin = "admin"


class ClientStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    placed = "placed"
    churned = "churned"


class ProfileType(str, enum.Enum):
    resume = "resume"
    linkedin = "linkedin"


class RemoteType(str, enum.Enum):
    fully_remote = "fully_remote"
    hybrid = "hybrid"
    onsite = "onsite"
    unknown = "unknown"


class ScrapeStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
