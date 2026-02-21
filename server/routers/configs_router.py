"""configs_router.py — Configuración del bot por usuario"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from dependencies import get_current_user, get_admin_user
import models
from schemas import BotConfigOut, BotConfigUpdate

router = APIRouter()

BOT_TYPES = ("mt5", "bingx")

# Configuraciones por defecto para nuevas cuentas
DEFAULT_MT5_CONFIG = {
    "min_confidence": 5,
    "cooldown": 30,
    "max_daily_trades": 50,
    "max_losses": 5,
    "lot_size": 0.01,
    "start_hour": "00:00",
    "end_hour": "23:59",
    "max_concurrent_trades": 3,
    "min_signal_interval": 60,
    "avoid_repeat_strategy": True,
    "auto_optimize": True,
}

DEFAULT_BINGX_CONFIG = {
    "default_symbol": "BTC-USDT",
    "default_leverage": 10,
    "margin_type": "ISOLATED",
    "risk_percent": 1.0,
    "max_positions": 3,
    "min_confidence": 30,
    "cooldown": 60,
    "max_daily_trades": 20,
    "max_losses": 3,
}


@router.get("/{bot_type}", response_model=BotConfigOut, summary="Obtener configuración del bot")
def get_config(
    bot_type: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if bot_type not in BOT_TYPES:
        raise HTTPException(400, f"bot_type debe ser uno de: {BOT_TYPES}")

    cfg = (
        db.query(models.BotConfig)
        .filter(models.BotConfig.user_id == current_user.id, models.BotConfig.bot_type == bot_type)
        .first()
    )
    if not cfg:
        cfg = models.BotConfig(
            user_id=current_user.id,
            bot_type=bot_type,
            config_json=json.dumps(DEFAULT_MT5_CONFIG if bot_type == "mt5" else DEFAULT_BINGX_CONFIG),
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)

    try:
        config_dict = json.loads(cfg.config_json or "{}")
    except Exception:
        config_dict = {}

    return BotConfigOut(
        bot_type=bot_type,
        config=config_dict,
        api_key=cfg.api_key,
        mt5_account=cfg.mt5_account,
        mt5_server=cfg.mt5_server,
        updated_at=cfg.updated_at,
    )


@router.put("/{bot_type}", response_model=BotConfigOut, summary="Guardar configuración del bot")
def update_config(
    bot_type: str,
    data: BotConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if bot_type not in BOT_TYPES:
        raise HTTPException(400, f"bot_type debe ser uno de: {BOT_TYPES}")

    cfg = (
        db.query(models.BotConfig)
        .filter(models.BotConfig.user_id == current_user.id, models.BotConfig.bot_type == bot_type)
        .first()
    )
    if not cfg:
        cfg = models.BotConfig(user_id=current_user.id, bot_type=bot_type)
        db.add(cfg)

    if data.config is not None:
        cfg.config_json = json.dumps(data.config)
    if data.api_key is not None:
        cfg.api_key = data.api_key
    if data.api_secret is not None:
        cfg.api_secret = data.api_secret
    if data.mt5_account is not None:
        cfg.mt5_account = data.mt5_account
    if data.mt5_password is not None:
        cfg.mt5_password = data.mt5_password
    if data.mt5_server is not None:
        cfg.mt5_server = data.mt5_server

    cfg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cfg)

    return BotConfigOut(
        bot_type=bot_type,
        config=json.loads(cfg.config_json or "{}"),
        api_key=cfg.api_key,
        mt5_account=cfg.mt5_account,
        mt5_server=cfg.mt5_server,
        updated_at=cfg.updated_at,
    )


@router.get("/admin/{user_id}/{bot_type}", response_model=BotConfigOut, summary="Config de usuario (Admin)")
def admin_get_config(
    user_id: int,
    bot_type: str,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    if bot_type not in BOT_TYPES:
        raise HTTPException(400, "bot_type inválido")
    cfg = (
        db.query(models.BotConfig)
        .filter(models.BotConfig.user_id == user_id, models.BotConfig.bot_type == bot_type)
        .first()
    )
    if not cfg:
        raise HTTPException(404, "Configuración no encontrada")
    return BotConfigOut(
        bot_type=bot_type,
        config=json.loads(cfg.config_json or "{}"),
        api_key=cfg.api_key,
        mt5_account=cfg.mt5_account,
        mt5_server=cfg.mt5_server,
        updated_at=cfg.updated_at,
    )
