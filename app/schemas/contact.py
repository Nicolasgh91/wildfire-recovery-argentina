from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=3, max_length=150)
    message: str = Field(..., min_length=10, max_length=5000)


class ContactAttachmentMeta(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


class ContactResponse(BaseModel):
    status: str
    request_id: str
    message: str
    attachment: Optional[ContactAttachmentMeta] = None
