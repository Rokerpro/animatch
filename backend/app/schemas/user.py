"""Pydantic schemas for authentication and user accounts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(
        ..., min_length=10, max_length=128, description="Between 10 and 128 characters"
    )
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip() if isinstance(v, str) else v

    @field_validator("display_name", mode="before")
    @classmethod
    def normalize_display_name(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v


class UserLoginRequest(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip() if isinstance(v, str) else v


class UserUpdateRequest(BaseModel):
    """Schema for updating current user profile."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    show_mature: bool | None = Field(default=None)

    @field_validator("display_name", mode="before")
    @classmethod
    def normalize_display_name(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("display_name cannot be empty or whitespace only")
            return stripped
        return v


class GoogleLinkRequest(BaseModel):
    """Schema for linking Google account for a logged-in user."""

    id_token: str | None = None


class UserResponse(BaseModel):
    """Public user response schema - never leaks password_hash or sensitive tokens."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    show_mature: bool
    taste_profile: dict[str, Any] | None = None
    created_at: datetime


class AuthProvidersResponse(BaseModel):
    """Schema indicating which external auth providers are configured."""

    google: bool


class CsrfTokenResponse(BaseModel):
    """Double-submit CSRF value returned alongside its browser cookie."""

    csrf_token: str

