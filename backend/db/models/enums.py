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
