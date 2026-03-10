#!/bin/bash
# linux_server_update.sh
# Update script for a Linux server deployment of VacationViewer.
# This script pulls the latest changes from Git, updates dependencies,
# runs migrations, collects static files, and restarts the service.

set -e

echo "======================================================"
echo " VacationViewer - Update Script"
echo "======================================================"

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root (e.g., sudo ./deployment/linux_server_update.sh)"
  exit 1
fi

APP_DIR="/var/www/vacationviewer"
VENV_DIR="$APP_DIR/.venv"
ENV_FILE="/etc/vacationviewer/env"

# Try to determine the app user from the systemd service file or default to www-data
if [ -f "/etc/systemd/system/vacationviewer.service" ]; then
    APP_USER=$(grep -oP '(?<=^User=).*' /etc/systemd/system/vacationviewer.service || echo "www-data")
else
    APP_USER="www-data"
fi

if [ ! -d "$APP_DIR" ]; then
    echo "Error: Application directory $APP_DIR not found. Is VacationViewer installed?"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file $ENV_FILE not found."
    exit 1
fi

echo "[1/5] Pulling latest repository changes..."
# We assume this script is run from within the git repository that was used for installation.
# Pull the latest changes to the current location, then sync them over cleanly to the APP_DIR.

# First pull into the current directory
sudo -u "$SUDO_USER" git pull origin master || git pull

echo "  Syncing project files to $APP_DIR..."
# Sync the newly pulled files to the application directory, excluding runtime/local files.
rsync -a --exclude='.venv' --exclude='.git' --exclude='__pycache__' --exclude='storage' --exclude='data' --exclude='config' --exclude='db.sqlite3' . "$APP_DIR/"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "[2/5] Updating Python dependencies..."
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "[3/5] Applying Database Migrations..."
cd "$APP_DIR"
sudo -u "$APP_USER" bash -c "set -a; source $ENV_FILE; set +a; $VENV_DIR/bin/python manage.py migrate"

echo "[4/5] Collecting static files..."
sudo -u "$APP_USER" bash -c "set -a; source $ENV_FILE; set +a; $VENV_DIR/bin/python manage.py collectstatic --no-input"

echo "[5/5] Restarting VacationViewer service..."
systemctl restart vacationviewer.service

echo "======================================================"
echo " Update complete! The application has been restarted."
echo "======================================================"
