#!/bin/bash
# setup_vps_api.sh
# Instala y configura el servidor API del Bot MT5 en el VPS Ubuntu
# Ejecutar como root o con sudo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR/trading_ai"
SERVICE_NAME="tradingbot-api"
VENV_DIR="$BOT_DIR/.venv_api"

echo "========================================"
echo "  Setup API Server - Bot MT5"
echo "  VPS: 217.154.100.195"
echo "========================================"

# 1. Verificar Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python3 no encontrado"
    exit 1
fi
echo "[OK] Python3: $(python3 --version)"

# 2. Crear entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    echo "[...] Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
fi

# 3. Instalar dependencias
echo "[...] Instalando dependencias API..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements_api.txt" -q
echo "[OK] Dependencias instaladas"

# 4. Crear archivo de configuracion del servicio
echo "[...] Configurando servicio systemd..."

# Preguntar API key si no esta configurada
if [ -z "$BOT_API_KEY" ]; then
    read -rsp "Ingresa la API KEY para la app (min 8 caracteres): " BOT_API_KEY
    echo
fi

if [ ${#BOT_API_KEY} -lt 8 ]; then
    echo "ERROR: API key muy corta"
    exit 1
fi

cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Trading Bot MT5 - API Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$BOT_DIR
ExecStart=$VENV_DIR/bin/python $BOT_DIR/api_server.py
Restart=always
RestartSec=5
Environment=BOT_API_KEY=$BOT_API_KEY
Environment=API_PORT=8080
Environment=API_HOST=0.0.0.0
Environment=MT5_FILES_BASE=$BOT_DIR/mt5_exchange

[Install]
WantedBy=multi-user.target
EOF

# 5. Abrir puerto en firewall (si ufw esta activo)
if command -v ufw &>/dev/null && ufw status | grep -q "active"; then
    echo "[...] Abriendo puerto 8080 en firewall..."
    ufw allow 8080/tcp
    echo "[OK] Puerto 8080 abierto"
fi

# 6. Habilitar y arrancar el servicio
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "========================================"
    echo "[OK] API Server corriendo!"
    echo ""
    echo "  URL:      http://217.154.100.195:8080"
    echo "  Docs:     http://217.154.100.195:8080/docs"
    echo "  API Key:  $BOT_API_KEY"
    echo ""
    echo "  Comandos utiles:"
    echo "  sudo systemctl status $SERVICE_NAME"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
    echo "  sudo systemctl restart $SERVICE_NAME"
    echo "========================================"
else
    echo ""
    echo "ERROR: El servicio no arranco. Ver logs:"
    journalctl -u "$SERVICE_NAME" -n 30 --no-pager
    exit 1
fi
