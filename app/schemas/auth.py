"""
Authentication schemas for ForestGuard
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# User schemas
class UserBase(BaseModel):
    """Base user data."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=100)
    dni: str = Field(..., min_length=7, max_length=20)
    
    @field_validator('dni')
    @classmethod
    def validate_dni(cls, v: str) -> str:
        """Validate Argentine DNI format."""
        # Remove dots and spaces
        cleaned = re.sub(r'[\.\s]', '', v)
        # DNI should be 7-8 digits
        if not re.match(r'^\d{7,8}$', cleaned):
            raise ValueError('DNI debe tener 7-8 dígitos')
        return cleaned


class UserLogin(BaseModel):
    """Schema for email/password login."""
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Schema for Google OAuth login."""
    credential: str = Field(..., description="Google JWT credential token")


class UserRead(UserBase):
    """Schema for reading user data."""
    id: str
    dni: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    created_at: datetime
    is_verified: bool
    
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)


# Auth response schemas
class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Authentication response with token and user."""
    access_token: str
    token_type: str = "bearer"
    user: UserRead


# Password reset schemas (for future use)
class PasswordResetRequest(BaseModel):
    """Request password reset."""
    email: EmailStr


class PasswordReset(BaseModel):
    """Reset password with token."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
