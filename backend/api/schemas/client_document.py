import uuid
from datetime import datetime

from pydantic import BaseModel


class ClientDocumentRead(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    preview_url: str
    uploaded_at: datetime
