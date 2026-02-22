"""
main.py — TradingBot Pro Server
FastAPI server para gestión de usuarios, licencias y configuraciones.

Uso:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Variables de entorno:
  DATABASE_URL     - URL de la base de datos (default: SQLite local)
  JWT_SECRET_KEY   - Clave secreta para JWT (¡CAMBIAR EN PRODUCCIÓN!)
  ADMIN_EMAIL      - Email del admin inicial (default: admin@tradingbot.com)
  ADMIN_PASSWORD   - Contraseña del admin inicial (default: admin123)
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import engine, SessionLocal
import models
from auth import hash_password
from routers import auth_router, users_router, licenses_router, configs_router, system_router


def _seed_initial_data():
    """Crea admin por defecto y configuraciones iniciales del sistema."""
    db: Session = SessionLocal()
    try:
        # ── Admin por defecto ────────────────────────────────────────────────
        if not db.query(models.User).filter(models.User.is_admin == True).first():
            admin_email    = os.environ.get("ADMIN_EMAIL", "admin@tradingbot.com")
            admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
            admin = models.User(
                first_name="Admin",
                last_name="Sistema",
                email=admin_email,
                password_hash=hash_password(admin_password),
                is_admin=True,
                is_active=True,
            )
            db.add(admin)
            db.flush()
            db.add(models.License(user_id=admin.id, license_type="lifetime", is_active=True))
            db.commit()
            print(f"✅ Admin creado: {admin_email} / {admin_password}")
            print("   ⚠️  CAMBIA LA CONTRASEÑA INMEDIATAMENTE en producción!")

        # ── Configuraciones del sistema ──────────────────────────────────────
        defaults = {
            "maintenance_enabled":  "false",
            "maintenance_message":  "Sistema en mantenimiento. Regresamos pronto.",
            "allow_registration":   "true",
            "server_version":       "1.0.0",
            "commercial_message_1": "🤖 Señales de IA para MT5 y BingX",
            "commercial_message_2": "📊 Aprende de cada operación automáticamente",
            "commercial_message_3": "🔒 Tus configuraciones seguras en la nube",
            "commercial_message_4": "⚡ Licencias flexibles: mensual, anual o de por vida",
        }
        for key, value in defaults.items():
            if not db.query(models.SystemSettings).filter(models.SystemSettings.key == key).first():
                db.add(models.SystemSettings(key=key, value=value))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    _seed_initial_data()
    print("🚀 TradingBot Pro Server iniciado")
    yield
    print("🛑 TradingBot Pro Server detenido")


app = FastAPI(
    title="TradingBot Pro Server",
    description="Servidor para gestión de usuarios, licencias y configuraciones del bot de trading",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router.router,     prefix="/auth",     tags=["🔐 Autenticación"])
app.include_router(users_router.router,    prefix="/users",    tags=["👥 Usuarios"])
app.include_router(licenses_router.router, prefix="/licenses", tags=["🎫 Licencias"])
app.include_router(configs_router.router,  prefix="/config",   tags=["⚙️ Configuración del Bot"])
app.include_router(system_router.router,   prefix="/system",   tags=["🖥️ Sistema"])


# ── Admin panel (static HTML) ─────────────────────────────────────────────────
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/admin", tags=["🏠 Info"], include_in_schema=False)
def admin_panel():
    """Panel de administración web."""
    return FileResponse(str(_STATIC_DIR / "admin.html"))


@app.get("/", tags=["🏠 Info"])
def root():
    return {
        "service":     "TradingBot Pro Server",
        "version":     "1.0.0",
        "status":      "running",
        "docs":        "/docs",
        "admin_panel": "/admin",
    }


@app.get("/health", tags=["🏠 Info"])
def health():
    return {"status": "healthy"}
