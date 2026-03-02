#!/bin/bash
# vacationviewer_setup.sh
# Installation script for VacationViewer on a Raspberry Pi running Raspberry Pi OS (Debian based).
# This script installs required dependencies, sets up the Python environment, runs migrations,
# and configures systemd to run the application as a service.

set -e

APP_DIR="/var/www/vacationviewer"
VENV_DIR="$APP_DIR/.venv"
USER="pi" # Default Raspberry Pi user

echo "[1/6] Updating system and installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git xdotool unclutter chromium-browser

echo "[2/6] Setting up application directory..."
# Assuming the repository is cloned. If not, this script will be in the repo itself.
if [ ! -d "$APP_DIR" ]; then
    echo "Creating directory $APP_DIR. Make sure to copy the codebase here."
    sudo mkdir -p "$APP_DIR"
    sudo chown -R $USER:$USER "$APP_DIR"
fi

echo "[3/6] Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Continuing without package installation."
fi

echo "[4/6] Running Django migrations..."
python manage.py makemigrations
python manage.py migrate

echo "[5/6] Creating systemd service for Django..."
SERVICE_FILE="/etc/systemd/system/vacationviewer.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=VacationViewer Django Daemon
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/python manage.py runserver 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vacationviewer.service
sudo systemctl start vacationviewer.service
echo "Django service configured and started."

echo "[6/6] Configuring autostart for Kiosk mode..."
AUTOSTART_DIR="/home/$USER/.config/lxsession/LXDE-pi"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/autostart" <<EOF
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash

# Disabled screen sleep
@xset s off
@xset -dpms
@xset s noblank

# Hide mouse cursor
@unclutter -idle 0.5 -root &

# Start Chromium in kiosk mode pointing to the app
@chromium-browser --kiosk --incognito --disable-infobars --start-maximized http://127.0.0.1:8000
EOF

echo "Setup is complete!"
echo "Please restart the Raspberry Pi with 'sudo reboot' to test the Kiosk mode."
