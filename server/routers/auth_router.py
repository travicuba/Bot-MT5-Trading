"""auth_router.py — Login y Registro"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from dependencies import get_current_user
import models
from schemas import UserRegister, UserLogin, Token, UserOut
from auth import hash_password, verify_password, create_access_token

router = APIRouter()


def _resolve_license(db: Session, user: models.User) -> tuple[str, bool]:
    """Returns (license_type, is_active)."""
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


@router.post("/register", response_model=Token, summary="Registrar nuevo usuario")
def register(data: UserRegister, db: Session = Depends(get_db)):
    setting = (
        db.query(models.SystemSettings)
        .filter(models.SystemSettings.key == "allow_registration")
        .first()
    )
    if setting and setting.value.lower() == "false":
        raise HTTPException(403, "El registro está deshabilitado temporalmente")

    if db.query(models.User).filter(models.User.email == data.email.lower()).first():
        raise HTTPException(400, "El correo electrónico ya está registrado")

    user = models.User(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.flush()

    db.add(models.License(user_id=user.id, license_type="free", is_active=True))
    db.add(models.BotConfig(user_id=user.id, bot_type="mt5"))
    db.add(models.BotConfig(user_id=user.id, bot_type="bingx"))
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return Token(
        access_token=token,
        user_id=user.id,
        is_admin=user.is_admin,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        license_type="free",
        license_active=True,
    )


@router.post("/login", response_model=Token, summary="Iniciar sesión")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Correo o contraseña incorrectos")
    if not user.is_active:
        raise HTTPException(403, "Cuenta desactivada. Contacta al administrador")

    user.last_login = datetime.utcnow()
    db.commit()

    lic_type, lic_active = _resolve_license(db, user)
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return Token(
        access_token=token,
        user_id=user.id,
        is_admin=user.is_admin,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        license_type=lic_type,
        license_active=lic_active,
    )


@router.get("/me", response_model=UserOut, summary="Perfil del usuario actual")
def me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    lic_type, lic_active = _resolve_license(db, current_user)
    result = UserOut.model_validate(current_user)
    result.license_type   = lic_type
    result.license_active = lic_active
    return result
