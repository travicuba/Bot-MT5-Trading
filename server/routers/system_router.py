"""system_router.py — Mantenimiento, estadísticas y configuración del servidor"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from dependencies import get_admin_user, get_current_user
import models
from schemas import MaintenanceStatus, ServerStats, SettingUpdate

router = APIRouter()


def _get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.query(models.SystemSettings).filter(models.SystemSettings.key == key).first()
    return s.value if s else default


def _set_setting(db: Session, key: str, value: str, admin_id: int | None = None):
    s = db.query(models.SystemSettings).filter(models.SystemSettings.key == key).first()
    if s:
        s.value = value
        s.updated_at = datetime.utcnow()
        s.updated_by = admin_id
    else:
        db.add(models.SystemSettings(key=key, value=value, updated_by=admin_id))
    db.commit()


# ─── MAINTENANCE ───────────────────────────────────────────────────────────────

@router.get("/maintenance", response_model=MaintenanceStatus, summary="Estado de mantenimiento (público)")
def get_maintenance(db: Session = Depends(get_db)):
    enabled = _get_setting(db, "maintenance_enabled", "false").lower() == "true"
    message = _get_setting(db, "maintenance_message", "Sistema en mantenimiento. Volvemos pronto.")
    return MaintenanceStatus(enabled=enabled, message=message)


@router.put("/maintenance", response_model=MaintenanceStatus, summary="Cambiar modo mantenimiento (Admin)")
def set_maintenance(
    data: MaintenanceStatus,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    _set_setting(db, "maintenance_enabled", "true" if data.enabled else "false", admin.id)
    if data.message:
        _set_setting(db, "maintenance_message", data.message, admin.id)
    return data


# ─── SERVER STATS ──────────────────────────────────────────────────────────────

@router.get("/stats", response_model=ServerStats, summary="Estadísticas del servidor (Admin)")
def server_stats(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    total_users  = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()

    now = datetime.utcnow()
    all_licenses = db.query(models.License).filter(models.License.is_active == True).all()

    lic_counts = {"free": 0, "monthly": 0, "annual": 0, "lifetime": 0}
    for lic in all_licenses:
        lt = lic.license_type
        if lt == "lifetime" or not lic.end_date or lic.end_date > now:
            lic_counts[lt] = lic_counts.get(lt, 0) + 1

    return ServerStats(
        total_users=total_users,
        active_users=active_users,
        licenses=lic_counts,
        maintenance_mode=_get_setting(db, "maintenance_enabled", "false").lower() == "true",
        server_version=_get_setting(db, "server_version", "1.0.0"),
    )


# ─── SETTINGS ─────────────────────────────────────────────────────────────────

@router.get("/settings", summary="Obtener todas las configuraciones (Admin)")
def get_settings(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    settings = db.query(models.SystemSettings).all()
    return {s.key: s.value for s in settings}


@router.put("/settings/{key}", summary="Actualizar configuración (Admin)")
def update_setting(
    key: str,
    data: SettingUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    _set_setting(db, key, data.value, admin.id)
    return {"key": key, "value": data.value}


# ─── REGISTRATION CONTROL ──────────────────────────────────────────────────────

@router.put("/registration/{enabled}", summary="Habilitar/deshabilitar registro (Admin)")
def toggle_registration(
    enabled: bool,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    _set_setting(db, "allow_registration", "true" if enabled else "false", admin.id)
    return {"allow_registration": enabled}
