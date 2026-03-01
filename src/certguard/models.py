"""SQLAlchemy database models."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


class BaseModel(Base):
    """Abstract base with common fields."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class User(BaseModel):
    """Application user for authentication."""

    __tablename__ = "users"

    username = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)


class Certificate(BaseModel):
    """SSL/TLS certificate record."""

    __tablename__ = "certificates"

    hostname = Column(String(255), nullable=False, index=True)
    port = Column(Integer, nullable=False, default=443)
    issuer = Column(String(500), nullable=True)
    subject = Column(String(500), nullable=True)
    sans = Column(Text, nullable=True)
    not_before = Column(DateTime, nullable=True)
    not_after = Column(DateTime, nullable=True)
    serial_number = Column(String(255), nullable=True)
    fingerprint = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="active")
