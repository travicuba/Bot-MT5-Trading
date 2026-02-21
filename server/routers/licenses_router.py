"""licenses_router.py — Gestión de licencias (Admin)"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from database import get_db
from dependencies import get_admin_user, get_current_user
import models
from schemas import LicenseCreate, LicenseOut, LicenseUpdate

router = APIRouter()

# Duración en días por tipo de licencia
LICENSE_DURATIONS = {
    "free":     None,
    "monthly":  30,
    "annual":   365,
    "lifetime": None,
}


def _calc_end_date(license_type: str) -> datetime | None:
    days = LICENSE_DURATIONS.get(license_type)
    if days:
        return datetime.utcnow() + timedelta(days=days)
    return None


@router.get("/user/{user_id}", response_model=List[LicenseOut], summary="Licencias de un usuario (Admin)")
def user_licenses(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    return db.query(models.License).filter(models.License.user_id == user_id).all()


@router.post("/", response_model=LicenseOut, summary="Crear/asignar licencia (Admin)")
def create_license(
    data: LicenseCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    user = db.query(models.User).filter(models.User.id == data.user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    if data.license_type not in ("free", "monthly", "annual", "lifetime"):
        raise HTTPException(400, "Tipo de licencia inválido")

    # Desactivar licencias activas previas
    db.query(models.License).filter(
        models.License.user_id == data.user_id,
        models.License.is_active == True,
    ).update({"is_active": False})

    lic = models.License(
        user_id=data.user_id,
        license_type=data.license_type,
        end_date=_calc_end_date(data.license_type),
        is_active=True,
        price_paid=data.price_paid,
        notes=data.notes,
        created_by=admin.id,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return lic


@router.put("/{license_id}", response_model=LicenseOut, summary="Actualizar licencia (Admin)")
def update_license(
    license_id: int,
    data: LicenseUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    lic = db.query(models.License).filter(models.License.id == license_id).first()
    if not lic:
        raise HTTPException(404, "Licencia no encontrada")

    if data.license_type is not None:
        if data.license_type not in ("free", "monthly", "annual", "lifetime"):
            raise HTTPException(400, "Tipo de licencia inválido")
        lic.license_type = data.license_type
        lic.end_date = _calc_end_date(data.license_type)
    if data.is_active is not None:
        lic.is_active = data.is_active
    if data.notes is not None:
        lic.notes = data.notes

    db.commit()
    db.refresh(lic)
    return lic


@router.delete("/{license_id}", summary="Eliminar licencia (Admin)")
def delete_license(
    license_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    lic = db.query(models.License).filter(models.License.id == license_id).first()
    if not lic:
        raise HTTPException(404, "Licencia no encontrada")
    db.delete(lic)
    db.commit()
    return {"message": "Licencia eliminada"}
