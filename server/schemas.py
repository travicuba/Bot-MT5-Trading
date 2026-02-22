"""schemas.py — Pydantic request/response models"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ─── AUTH ─────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    first_name: str
    last_name:  str
    email:      EmailStr
    password:   str

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v

    @field_validator("first_name", "last_name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()


class UserLogin(BaseModel):
    email:    EmailStr
    password: str


class Token(BaseModel):
    access_token:    str
    token_type:      str = "bearer"
    user_id:         int
    is_admin:        bool
    first_name:      str
    last_name:       str
    email:           str
    license_type:    str
    license_active:  bool


# ─── USER ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id:            int
    first_name:    str
    last_name:     str
    email:         str
    is_active:     bool
    is_admin:      bool
    created_at:    datetime
    last_login:    Optional[datetime]
    license_type:  str
    license_active: bool

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: Optional[str]      = None
    last_name:  Optional[str]      = None
    email:      Optional[EmailStr] = None
    is_active:  Optional[bool]     = None
    is_admin:   Optional[bool]     = None
    password:   Optional[str]      = None


# ─── LICENSE ───────────────────────────────────────────────────────────────────

class LicenseCreate(BaseModel):
    user_id:      int
    license_type: str   # free | monthly | annual | lifetime
    price_paid:   Optional[float] = None
    notes:        Optional[str]   = None


class LicenseOut(BaseModel):
    id:           int
    user_id:      int
    license_type: str
    start_date:   datetime
    end_date:     Optional[datetime]
    is_active:    bool
    price_paid:   Optional[float]
    notes:        Optional[str]

    model_config = {"from_attributes": True}


class LicenseUpdate(BaseModel):
    license_type: Optional[str]  = None
    is_active:    Optional[bool] = None
    notes:        Optional[str]  = None


# ─── BOT CONFIG ─────────────────────────────────────────────────────────────────

class BotConfigOut(BaseModel):
    bot_type:    str
    config:      Dict[str, Any]
    api_key:     Optional[str] = None
    mt5_account: Optional[str] = None
    mt5_server:  Optional[str] = None
    updated_at:  Optional[datetime] = None


class BotConfigUpdate(BaseModel):
    config:      Optional[Dict[str, Any]] = None
    api_key:     Optional[str]            = None
    api_secret:  Optional[str]            = None
    mt5_account: Optional[str]            = None
    mt5_password: Optional[str]           = None
    mt5_server:  Optional[str]            = None


# ─── SYSTEM ────────────────────────────────────────────────────────────────────

class MaintenanceStatus(BaseModel):
    enabled: bool
    message: str = ""


class ServerStats(BaseModel):
    total_users:      int
    active_users:     int
    licenses:         Dict[str, int]
    maintenance_mode: bool
    server_version:   str


class SettingUpdate(BaseModel):
    value: str
