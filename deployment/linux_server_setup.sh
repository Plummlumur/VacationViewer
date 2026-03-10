#!/bin/bash
# linux_server_setup.sh
# Deployment wizard for VacationViewer on a standard Debian/Ubuntu Linux server.
# This script configures Gunicorn, Nginx, and systemd for a production environment.

set -e

echo "======================================================"
echo " VacationViewer - Linux Server Deployment Wizard"
echo "======================================================"

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root (e.g., sudo ./deployment/linux_server_setup.sh)"
  exit 1
fi

APP_DIR="/var/www/vacationviewer"
VENV_DIR="$APP_DIR/.venv"
LOG_DIR="/var/log/vacationviewer"
ENV_FILE="/etc/vacationviewer/env"

read -p "Enter the system user that should run the application (e.g., www-data, or your username) [www-data]: " APP_USER
APP_USER=${APP_USER:-www-data}

read -p "Enter the domain or IP address for the server (e.g., vacation.local or 192.168.1.100) [localhost]: " APP_HOST
APP_HOST=${APP_HOST:-localhost}

read -p "Do you want to configure HTTPS using Let's Encrypt / Certbot? (y/N) [N]: " USE_CERTBOT
USE_CERTBOT=${USE_CERTBOT:-N}

if [[ "$USE_CERTBOT" =~ ^[Yy]$ ]]; then
    read -p "Enter an email address for Let's Encrypt (required for expiration notices): " CERTBOT_EMAIL
fi

echo ""
echo "[1/7] Updating system and installing dependencies (Python, Nginx, etc.)..."
apt-get update
apt-get install -y python3 python3-venv python3-pip git nginx rsync

if [[ "$USE_CERTBOT" =~ ^[Yy]$ ]]; then
    echo "  Installing certbot and nginx plugin..."
    apt-get install -y certbot python3-certbot-nginx
fi

echo "[2/7] Setting up application directory..."
mkdir -p "$APP_DIR"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "[3/7] Setting up Python virtual environment and copying files..."
sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "  Syncing project files to $APP_DIR..."
    rsync -a --exclude='.venv' --exclude='.git' --exclude='__pycache__' . "$APP_DIR/"
    chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
    
    echo "  Installing Python dependencies..."
    sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
    sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install gunicorn
else
    echo "Error: requirements.txt not found. Please run this script from the project root."
    exit 1
fi

echo "[4/7] Configuration and Database Migrations..."
mkdir -p /etc/vacationviewer
if [ ! -f "$ENV_FILE" ]; then
    GENERATED_KEY=$(sudo -u "$APP_USER" "$VENV_DIR/bin/python" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    cat > "$ENV_FILE" <<EOF
# VacationViewer Production Environment File
SECRET_KEY=$GENERATED_KEY
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,$APP_HOST
EOF
    chmod 600 "$ENV_FILE"
    chown "$APP_USER":"$APP_USER" "$ENV_FILE"
    echo "  Created new environment file at $ENV_FILE"
else
    echo "  Environment file already exists at $ENV_FILE"
fi

cd "$APP_DIR"
echo "  Applying migrations..."
sudo -u "$APP_USER" bash -c "set -a; source $ENV_FILE; set +a; $VENV_DIR/bin/python manage.py makemigrations"
sudo -u "$APP_USER" bash -c "set -a; source $ENV_FILE; set +a; $VENV_DIR/bin/python manage.py migrate"
echo "  Collecting static files..."
sudo -u "$APP_USER" bash -c "set -a; source $ENV_FILE; set +a; $VENV_DIR/bin/python manage.py collectstatic --no-input"

echo "[5/7] Setting up Gunicorn systemd service..."
mkdir -p "$LOG_DIR"
chown -R "$APP_USER":"$APP_USER" "$LOG_DIR"

SERVICE_FILE="/etc/systemd/system/vacationviewer.service"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=VacationViewer Gunicorn Daemon
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/gunicorn \\
    --workers 3 \\
    --bind unix:$APP_DIR/vacationviewer.sock \\
    --access-logfile $LOG_DIR/access.log \\
    --error-logfile $LOG_DIR/error.log \\
    vacationviewer.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vacationviewer.service
systemctl restart vacationviewer.service

echo "[6/7] Setting up Nginx to serve the app..."
NGINX_CONF="/etc/nginx/sites-available/vacationviewer"
cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $APP_HOST;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root $APP_DIR;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/vacationviewer.sock;
    }
}
EOF

ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
# Remove default nginx config to avoid conflicts if present
rm -f /etc/nginx/sites-enabled/default

systemctl restart nginx

if [[ "$USE_CERTBOT" =~ ^[Yy]$ ]]; then
    echo "[7/7] Configuring HTTPS with Let's Encrypt..."
    if [ -n "$CERTBOT_EMAIL" ]; then
        certbot --nginx -d "$APP_HOST" --non-interactive --agree-tos -m "$CERTBOT_EMAIL" --redirect
    else
        echo "  Notice: Registering without email address."
        certbot --nginx -d "$APP_HOST" --non-interactive --agree-tos --register-unsafely-without-email --redirect
    fi
    echo "  HTTPS configured successfully!"
else
    echo "[7/7] Skipping HTTPS configuration..."
fi

echo "======================================================"
echo " Setup complete! VacationViewer is now deployed."
if [[ "$USE_CERTBOT" =~ ^[Yy]$ ]]; then
    echo " Domain / IP   : https://$APP_HOST"
else
    echo " Domain / IP   : http://$APP_HOST"
fi
echo " Directory     : $APP_DIR"
echo " Log files     : $LOG_DIR"
echo "======================================================"
echo " To set an admin password, run:"
echo "   sudo -u $APP_USER $VENV_DIR/bin/python $APP_DIR/manage.py hash_admin_password"
echo "======================================================"
