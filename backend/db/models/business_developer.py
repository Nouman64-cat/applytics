import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from db.models.enums import BDRole


class BusinessDeveloper(SQLModel, table=True):
    __tablename__ = "business_developer"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: str
    role: BDRole = Field(default=BDRole.bd)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
