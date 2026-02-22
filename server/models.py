"""models.py — SQLAlchemy ORM models"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, index=True)
    first_name  = Column(String(100), nullable=False)
    last_name   = Column(String(100), nullable=False)
    email       = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active   = Column(Boolean, default=True)
    is_admin    = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    last_login  = Column(DateTime, nullable=True)

    licenses = relationship("License", back_populates="user", cascade="all, delete-orphan")
    configs  = relationship("BotConfig", back_populates="user", cascade="all, delete-orphan")


class License(Base):
    __tablename__ = "licenses"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    license_type = Column(String(20), default="free")  # free | monthly | annual | lifetime
    start_date   = Column(DateTime, default=datetime.utcnow)
    end_date     = Column(DateTime, nullable=True)          # NULL = lifetime / free
    is_active    = Column(Boolean, default=True)
    price_paid   = Column(Float, nullable=True)
    notes        = Column(Text, nullable=True)
    created_by   = Column(Integer, nullable=True)           # admin user id

    user = relationship("User", back_populates="licenses")


class BotConfig(Base):
    __tablename__ = "bot_configs"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    bot_type         = Column(String(10), nullable=False)   # mt5 | bingx
    config_json      = Column(Text, default="{}")
    api_key          = Column(Text, nullable=True)
    api_secret       = Column(Text, nullable=True)
    mt5_account      = Column(String(50), nullable=True)
    mt5_password     = Column(Text, nullable=True)
    mt5_server       = Column(String(255), nullable=True)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="configs")


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id         = Column(Integer, primary_key=True, index=True)
    key        = Column(String(100), unique=True, nullable=False, index=True)
    value      = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(Integer, nullable=True)
