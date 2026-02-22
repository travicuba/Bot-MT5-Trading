#!/bin/bash
# ════════════════════════════════════════════════════════════════
#  TradingBot Pro Server — Script de instalación (Ubuntu/Debian)
# ════════════════════════════════════════════════════════════════
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="tradingbot-server"
SERVICE_USER="${USER:-root}"
PORT="${SERVER_PORT:-8000}"

echo "═══════════════════════════════════════════════"
echo "  TradingBot Pro Server — Instalación"
echo "═══════════════════════════════════════════════"

# Solicitar credenciales
read -p "Email del administrador [admin@tradingbot.com]: " ADMIN_EMAIL
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@tradingbot.com}"

read -s -p "Contraseña del administrador: " ADMIN_PASSWORD
echo
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "❌ La contraseña no puede estar vacía"
    exit 1
fi

read -s -p "Clave secreta JWT (dejar en blanco para generar automáticamente): " JWT_SECRET
echo
if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "🔑 JWT Secret generado automáticamente"
fi

read -p "Puerto del servidor [8000]: " INPUT_PORT
PORT="${INPUT_PORT:-8000}"

# Crear entorno virtual
echo ""
echo "📦 Creando entorno virtual Python..."
cd "$SCRIPT_DIR"
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt --quiet

# Crear archivo de entorno
cat > "$SCRIPT_DIR/.env" <<EOF
DATABASE_URL=sqlite:///$(pwd)/tradingbot_server.db
JWT_SECRET_KEY=$JWT_SECRET
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD=$ADMIN_PASSWORD
EOF
echo "✅ Archivo .env creado"

# Crear servicio systemd
echo "🔧 Creando servicio systemd..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=TradingBot Pro Server
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${SCRIPT_DIR}
Environment=PATH=${SCRIPT_DIR}/venv/bin
EnvironmentFile=${SCRIPT_DIR}/.env
ExecStart=${SCRIPT_DIR}/venv/bin/uvicorn main:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

sleep 2
if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  ✅ TradingBot Pro Server iniciado correctamente"
    echo "  🌐 URL: http://$(hostname -I | awk '{print $1}'):${PORT}"
    echo "  📖 Documentación: http://$(hostname -I | awk '{print $1}'):${PORT}/docs"
    echo "  👤 Admin: ${ADMIN_EMAIL}"
    echo "═══════════════════════════════════════════════"
else
    echo "❌ Error al iniciar el servicio"
    sudo journalctl -u ${SERVICE_NAME} --no-pager -n 20
    exit 1
fi
