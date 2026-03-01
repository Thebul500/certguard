"""Tests for SQLAlchemy models."""

from sqlalchemy import inspect

from certguard.models import BaseModel


def test_basemodel_is_abstract():
    """BaseModel is an abstract model (no table)."""
    assert BaseModel.__abstract__ is True


def test_basemodel_columns():
    """BaseModel defines id, created_at, updated_at columns."""
    assert hasattr(BaseModel, "id")
    assert hasattr(BaseModel, "created_at")
    assert hasattr(BaseModel, "updated_at")


def test_basemodel_id_is_primary_key():
    """id column is the primary key."""
    assert BaseModel.id.primary_key
