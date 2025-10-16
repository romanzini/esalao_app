"""Pydantic schemas for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password (min 8 characters)",
        examples=["SecurePassword123!"],
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="User full name",
        examples=["João Silva"],
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
        description="Contact phone number",
        examples=["+55 11 98765-4321"],
    )


class UserLoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="User password",
        examples=["SecurePassword123!"],
    )


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
    )


class TokenResponse(BaseModel):
    """Response schema for token endpoints."""

    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
    )


class UserResponse(BaseModel):
    """Response schema for user information."""

    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    phone: str | None = Field(None, description="Contact phone")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Account is active")
    is_verified: bool = Field(..., description="Email is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}
