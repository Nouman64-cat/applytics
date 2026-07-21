import uuid

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class JobSource(SQLModel, table=True):
    __tablename__ = "job_source"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)
    is_enabled: bool = Field(default=True)
    rate_limit_per_min: int | None = None
    auth_config: dict = Field(default_factory=dict, sa_column=Column(JSON))
