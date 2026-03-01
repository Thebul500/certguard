"""Certificate CRUD routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Certificate, User
from ..schemas import CertificateCreate, CertificateResponse, CertificateUpdate

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post("/", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def create_certificate(
    body: CertificateCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Add a new certificate record."""
    cert = Certificate(**body.model_dump())
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


@router.get("/", response_model=list[CertificateResponse])
async def list_certificates(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List all certificate records."""
    result = await db.execute(select(Certificate).order_by(Certificate.id))
    return result.scalars().all()


@router.get("/{cert_id}", response_model=CertificateResponse)
async def get_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get a single certificate by ID."""
    result = await db.execute(select(Certificate).where(Certificate.id == cert_id))
    cert = result.scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return cert


@router.put("/{cert_id}", response_model=CertificateResponse)
async def update_certificate(
    cert_id: int,
    body: CertificateUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Update an existing certificate record."""
    result = await db.execute(select(Certificate).where(Certificate.id == cert_id))
    cert = result.scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cert, field, value)

    await db.commit()
    await db.refresh(cert)
    return cert


@router.delete("/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Delete a certificate record."""
    result = await db.execute(select(Certificate).where(Certificate.id == cert_id))
    cert = result.scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    await db.delete(cert)
    await db.commit()
