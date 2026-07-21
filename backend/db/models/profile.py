import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel

from db.models.enums import ProfileType


class Profile(SQLModel, table=True):
    __tablename__ = "profile"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="client.id", index=True)
    target_role_id: uuid.UUID | None = Field(default=None, foreign_key="target_role.id")
    type: ProfileType
    variant_label: str
    source_url: str | None = None
    raw_text: str | None = None
    structured_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
