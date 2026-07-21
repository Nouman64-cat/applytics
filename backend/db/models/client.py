import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from db.models.enums import ClientStatus


class Client(SQLModel, table=True):
    __tablename__ = "client"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    bd_id: uuid.UUID = Field(foreign_key="business_developer.id", index=True)
    full_name: str
    email: str
    current_city: str | None = None
    current_state: str | None = None
    current_country: str | None = None
    timezone: str | None = None
    status: ClientStatus = Field(default=ClientStatus.active)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
