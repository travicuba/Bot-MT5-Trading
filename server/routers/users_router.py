"""users_router.py — Gestión de usuarios (Admin)"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import get_db
from dependencies import get_admin_user, get_current_user
import models
from schemas import UserOut, UserUpdate
from auth import hash_password

router = APIRouter()


def _resolve_license(db: Session, user: models.User) -> tuple[str, bool]:
    lic = (
        db.query(models.License)
        .filter(models.License.user_id == user.id, models.License.is_active == True)
        .order_by(models.License.start_date.desc())
        .first()
    )
    if not lic:
        return "free", False
    if lic.license_type == "lifetime":
        return "lifetime", True
    if lic.end_date and lic.end_date < datetime.utcnow():
        return lic.license_type, False
    return lic.license_type, True


def _user_to_out(db: Session, user: models.User) -> UserOut:
    lt, la = _resolve_license(db, user)
    return UserOut(
        id=user.id, first_name=user.first_name, last_name=user.last_name,
        email=user.email, is_active=user.is_active, is_admin=user.is_admin,
        created_at=user.created_at, last_login=user.last_login,
        license_type=lt, license_active=la,
    )


@router.get("/", response_model=List[UserOut], summary="Listar todos los usuarios (Admin)")
def list_users(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return [_user_to_out(db, u) for u in users]


@router.get("/{user_id}", response_model=UserOut, summary="Obtener usuario por ID (Admin)")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    return _user_to_out(db, user)


@router.put("/{user_id}", response_model=UserOut, summary="Actualizar usuario (Admin)")
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.email is not None:
        existing = db.query(models.User).filter(
            models.User.email == data.email.lower(), models.User.id != user_id
        ).first()
        if existing:
            raise HTTPException(400, "Email ya en uso")
        user.email = data.email.lower()
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    if data.password:
        user.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(user)
    return _user_to_out(db, user)


@router.delete("/{user_id}", summary="Eliminar usuario (Admin)")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    if user_id == admin.id:
        raise HTTPException(400, "No puedes eliminar tu propia cuenta")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    db.delete(user)
    db.commit()
    return {"message": "Usuario eliminado correctamente"}
