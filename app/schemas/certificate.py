from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CertificateCreate(BaseModel):
    fire_event_id: UUID
    issued_to: str


class CertificateResponse(BaseModel):
    id: UUID
    issued_to: str
    data_hash: str
    created_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)
