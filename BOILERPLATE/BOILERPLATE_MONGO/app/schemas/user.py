"""
User Schemas for MongoDB.

Pydantic schemas for User-related operations.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema
from app.config import settings


# =============================================================================
# User Base Schemas
# =============================================================================
class UserBase(BaseSchema):
    """Base user schema with common fields."""
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseSchema):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=1000)


class PasswordChange(BaseSchema):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)


# =============================================================================
# User Response Schemas
# =============================================================================
class UserResponse(UserBase, TimestampSchema):
    """Schema for user response (public data)."""
    id: str = Field(..., alias="_id")
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    @field_validator("id", mode="before")
    @classmethod
    def convert_objectid(cls, v):
        return str(v) if v else None


# =============================================================================
# Authentication Schemas
# =============================================================================
class LoginRequest(BaseSchema):
    """Schema for login request."""
    email: EmailStr
    password: str


class Token(BaseSchema):
    """Schema for token response."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenRefresh(BaseSchema):
    """Schema for token refresh request."""
    refresh_token: str
