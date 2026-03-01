"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime


# --- Auth schemas ---


class UserCreate(BaseModel):
    """Request to register a new user."""

    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Public user representation."""

    id: int
    username: str
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TokenRequest(BaseModel):
    """Login credentials."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token pair."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105


# --- Certificate schemas ---


class CertificateCreate(BaseModel):
    """Request to add a certificate."""

    hostname: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=443, ge=1, le=65535)
    issuer: str | None = None
    subject: str | None = None
    sans: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    serial_number: str | None = None
    fingerprint: str | None = None
    status: str = "active"


class CertificateUpdate(BaseModel):
    """Request to update a certificate."""

    hostname: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    issuer: str | None = None
    subject: str | None = None
    sans: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    serial_number: str | None = None
    fingerprint: str | None = None
    status: str | None = None


class CertificateResponse(BaseModel):
    """Certificate record response."""

    id: int
    hostname: str
    port: int
    issuer: str | None = None
    subject: str | None = None
    sans: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    serial_number: str | None = None
    fingerprint: str | None = None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
