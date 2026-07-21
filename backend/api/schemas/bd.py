import uuid
from datetime import datetime

from pydantic import BaseModel

from db.models.enums import BDRole


class BDRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: BDRole
    created_at: datetime
