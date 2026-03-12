#!/bin/bash
# vacationviewer_setup.sh
# Installation script for VacationViewer on a Raspberry Pi running Raspberry Pi OS (Debian based).
# This script installs required dependencies, sets up the Python environment, runs migrations,
# and configures systemd with Gunicorn (production WSGI server) as a service.
#
# Security hardening applied:
#   - Uses Gunicorn instead of manage.py runserver (S-02)
#   - Reads secrets from an EnvironmentFile (S-13)
#   - Runs with restricted filesystem permissions

set -e

APP_DIR="/var/www/vacationviewer"
VENV_DIR="$APP_DIR/.venv"
USER="pi"  # Default Raspberry Pi user
ENV_FILE="/etc/vacationviewer/env"
LOG_DIR="/var/log/vacationviewer"

echo "[1/7] Updating system and installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git xdotool unclutter chromium-browser

echo "[2/7] Setting up application directory..."
if [ ! -d "$APP_DIR" ]; then
    echo "Creating directory $APP_DIR. Make sure to copy the codebase here."
    sudo mkdir -p "$APP_DIR"
    sudo chown -R $USER:$USER "$APP_DIR"
fi

echo "[3/7] Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
if [ -f "requirements.txt" ]; then
    # Install production deps only (no pytest/ruff in production)
    "$VENV_DIR/bin/pip" install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Continuing without package installation."
fi

echo "[4/7] Creating EnvironmentFile for secrets..."
# Create secrets directory with restricted permissions (S-13)
sudo mkdir -p /etc/vacationviewer
if [ ! -f "$ENV_FILE" ]; then
    # Generate a fresh SECRET_KEY
    GENERATED_KEY=$("$VENV_DIR/bin/python" -c \
        "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    sudo bash -c "cat > $ENV_FILE" <<EOF
# VacationViewer – Production Environment
# KEEP THIS FILE SECRET: chmod 600, owner $USER
SECRET_KEY=$GENERATED_KEY
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,$(hostname)
EOF
    sudo chmod 600 "$ENV_FILE"
    sudo chown "$USER":"$USER" "$ENV_FILE"
    echo "  EnvironmentFile created at $ENV_FILE"
    echo "  !! Review $ENV_FILE and set ALLOWED_HOSTS to your Pi's hostname !!"
else
    echo "  EnvironmentFile already exists at $ENV_FILE – skipping generation."
fi

echo "[5/7] Running Django migrations and collecting static files..."
sudo -u "$USER" bash -c "set -a; source $ENV_FILE; set +a; $VENV_DIR/bin/python manage.py makemigrations"
sudo -u "$USER" bash -c "set -a; source $ENV_FILE; set +a; $VENV_DIR/bin/python manage.py migrate"
sudo -u "$USER" bash -c "set -a; source $ENV_FILE; set +a; DJANGO_SETTINGS_MODULE=vacationviewer.settings $VENV_DIR/bin/python manage.py collectstatic --no-input || true"

echo "[6/7] Creating systemd service for Gunicorn (production WSGI server)..."
# Create log directory (S-02: replaces dev server)
sudo mkdir -p "$LOG_DIR"
sudo chown "$USER":www-data "$LOG_DIR"
sudo chmod 750 "$LOG_DIR"

SERVICE_FILE="/etc/systemd/system/vacationviewer.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=VacationViewer – Gunicorn WSGI
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/gunicorn \\
    --workers 2 \\
    --timeout 30 \\
    --bind 127.0.0.1:8000 \\
    --access-logfile $LOG_DIR/access.log \\
    --error-logfile $LOG_DIR/error.log \\
    vacationviewer.wsgi:application
Restart=on-failure
RestartSec=5
# Harden the service process
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vacationviewer.service
sudo systemctl start vacationviewer.service
echo "  Gunicorn service configured and started."

echo "[7/7] Configuring autostart for Kiosk mode..."
AUTOSTART_DIR="/home/$USER/.config/lxsession/LXDE-pi"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/autostart" <<EOF
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash

# Disable screen sleep
@xset s off
@xset -dpms
@xset s noblank

# Hide mouse cursor
@unclutter -idle 0.5 -root &

# Start Chromium in kiosk mode pointing to the app
@chromium-browser --kiosk --incognito --disable-infobars --start-maximized http://127.0.0.1:8000
EOF

echo ""
echo "======================================================"
echo " Setup complete!"
echo "======================================================"
echo ""
echo " IMPORTANT next steps:"
echo "  1. Review $ENV_FILE and verify ALLOWED_HOSTS"
echo "  2. Set admin password:"
echo "     $VENV_DIR/bin/python manage.py hash_admin_password"
echo "  3. Restart: sudo reboot"
echo ""
