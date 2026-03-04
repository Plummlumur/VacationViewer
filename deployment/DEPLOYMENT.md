# VacationViewer – Deployment Guide

**Zielplattform:** Raspberry Pi OS (Bookworm/Bullseye) · Debian 12/11  
**Produktionsstack:** Python 3.11+ · Gunicorn · Systemd · Chromium (Kiosk)

---

## Voraussetzungen

- Raspberry Pi (Modell 3B+, 4 oder 5 empfohlen) mit Raspberry Pi OS Desktop **oder** Debian-Server
- Internetzugang während der Installation (für Pakete und Repo-Clone)
- SSH-Zugriff oder direktes Terminal
- Ein angeschlossenes Display (für Kiosk-Modus)

---

## 1. System vorbereiten

```bash
sudo apt-get update && sudo apt-get upgrade -y

sudo apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl
```

Für den Kiosk-Modus (Raspberry Pi mit Desktop) zusätzlich:

```bash
sudo apt-get install -y \
    xdotool \
    unclutter \
    chromium-browser
```

---

## 2. Codebase deployen

```bash
# Anwendungsverzeichnis anlegen
sudo mkdir -p /var/www/vacationviewer
sudo chown -R pi:pi /var/www/vacationviewer   # 'pi' ggf. durch deinen User ersetzen
```

**Option A – Git Clone (empfohlen):**

```bash
cd /var/www
git clone <repository-url> vacationviewer
cd vacationviewer
git checkout hardening/production-ready      # Den gehärteten Branch verwenden
```

**Option B – Manueller Upload via SCP:**

```bash
# Auf dem Entwicklungsrechner ausführen:
scp -r /path/to/VacationViewer/* pi@<pi-ip>:/var/www/vacationviewer/
```

---

## 3. Python-Umgebung einrichten

```bash
cd /var/www/vacationviewer

# Virtual Environment erstellen
python3 -m venv .venv

# Aktivieren
source .venv/bin/activate

# Pip updaten und Produktions-Abhängigkeiten installieren
pip install --upgrade pip
pip install -r requirements.txt    # Installiert: django, openpyxl, defusedxml, gunicorn, whitenoise
```

> **Hinweis:** `requirements-dev.txt` (pytest, ruff) wird in Produktion **nicht** installiert.

---

## 4. Secrets und Umgebungsvariablen konfigurieren

Alle sicherheitsrelevanten Werte werden über eine EnvironmentFile verwaltet – niemals im Source-Code oder in Git.

```bash
# Verzeichnis für Secrets anlegen (nur root lesbar)
sudo mkdir -p /etc/vacationviewer

# Neuen geheimen Schlüssel generieren
SECRET=$(source .venv/bin/activate && python -c \
  "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# EnvironmentFile schreiben
sudo bash -c "cat > /etc/vacationviewer/env" << EOF
# VacationViewer – Produktionskonfiguration
# ACHTUNG: Datei sicher halten. Nur root darf lesen.
SECRET_KEY=${SECRET}
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,$(hostname)
EOF

# Berechtigungen sichern
sudo chmod 600 /etc/vacationviewer/env
sudo chown root:root /etc/vacationviewer/env
```

> `$(hostname)` trägt automatisch den Hostnamen des Pi ein. Bei Bedarf weitere Hostnamen kommasepariert ergänzen, z.B. `ALLOWED_HOSTS=127.0.0.1,localhost,vacationviewer.local`.

---

## 5. Datenbank und Admin-Passwort einrichten

```bash
cd /var/www/vacationviewer
source .venv/bin/activate

# Umgebungsvariablen laden
export $(sudo cat /etc/vacationviewer/env | grep -v '^#' | xargs)

# Datenbankmigrationen ausführen
python manage.py migrate

# Static Files einsammeln (für Gunicorn/WhiteNoise)
python manage.py collectstatic --no-input

# Admin-Passwort setzen (interaktiv, mind. 12 Zeichen)
python manage.py hash_admin_password
```

Das Passwort wird PBKDF2-SHA256 gehasht in `config/admin.json` gespeichert.

---

## 6. Urlaubsdaten bereitstellen

Die App erwartet eine Excel-Datei im Format `Person-ID | Urlaubsstart | Urlaubsende`:

```bash
# Verzeichnis prüfen
ls /var/www/vacationviewer/data/

# Excel-Datei platzieren (Name muss mit configured xlsx_path übereinstimmen)
cp /path/to/urlaub.xlsx /var/www/vacationviewer/data/urlaub.xlsx
```

Der Standardpfad ist `data/urlaub.xlsx` relativ zum App-Verzeichnis. Er kann im Admin-Dashboard angepasst werden.

---

## 7. Systemd Service einrichten (Gunicorn)

```bash
# Log-Verzeichnis anlegen
sudo mkdir -p /var/log/vacationviewer
sudo chown pi:www-data /var/log/vacationviewer
sudo chmod 750 /var/log/vacationviewer

# Service-Datei erstellen
sudo bash -c "cat > /etc/systemd/system/vacationviewer.service" << 'EOF'
[Unit]
Description=VacationViewer – Gunicorn WSGI
After=network.target

[Service]
User=pi
Group=www-data
WorkingDirectory=/var/www/vacationviewer
EnvironmentFile=/etc/vacationviewer/env
ExecStart=/var/www/vacationviewer/.venv/bin/gunicorn \
    --workers 2 \
    --timeout 30 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/vacationviewer/access.log \
    --error-logfile /var/log/vacationviewer/error.log \
    vacationviewer.wsgi:application
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Service aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable vacationviewer.service
sudo systemctl start vacationviewer.service

# Status prüfen
sudo systemctl status vacationviewer.service
```

**Erwartete Ausgabe:** `Active: active (running)`

---

## 8. Funktionstest

```bash
# Antwort der App prüfen (sollte HTTP 200 zurückgeben)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health/

# Logs beobachten
sudo journalctl -u vacationviewer.service -f
```

---

## 9. Kiosk-Modus einrichten (Raspberry Pi mit Desktop)

Dieser Schritt öffnet Chromium beim Systemstart automatisch im Vollbild und zeigt die App an.

```bash
# Autostart-Verzeichnis sicherstellen
mkdir -p /home/pi/.config/lxsession/LXDE-pi

# Autostart-Datei schreiben
cat > /home/pi/.config/lxsession/LXDE-pi/autostart << 'EOF'
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash

# Bildschirm-Schlafmodus deaktivieren
@xset s off
@xset -dpms
@xset s noblank

# Mauszeiger ausblenden
@unclutter -idle 0.5 -root &

# Chromium im Kiosk-Modus starten
@chromium-browser --kiosk --incognito --disable-infobars --start-maximized http://127.0.0.1:8000
EOF
```

> **Hinweis:** `--incognito` verhindert, dass Chromium beim nächsten Start einen Wiederherstellungsdialog zeigt.

---

## 10. System neu starten

```bash
sudo reboot
```

Nach dem Neustart sollte:
1. Der `vacationviewer.service` automatisch gestartet sein
2. Der Desktop die App vollständig in Chromium anzeigen

---

## Urlaubsdaten aktualisieren

Die App prüft die Excel-Datei in regelmäßigen Abständen (Standard: alle 5 Minuten) auf Änderungen.

**Datei per SCP hochladen:**

```bash
# Vom Entwicklungsrechner:
scp urlaub_2026.xlsx pi@<pi-ip>:/var/www/vacationviewer/data/urlaub.xlsx
```

Der VacationViewer übernimmt die neue Datei beim nächsten Cache-Refresh automatisch. Ein Neustart ist nicht nötig.

---

## Admin-Interface

Das Admin-Dashboard ist erreichbar unter:

```
http://<pi-ip>:8000/admin/
```

Dort können folgende Einstellungen zur Laufzeit geändert werden:
- **Urlaubslimits** pro Wochentag
- **Tagesausnahmen** (z.B. Feiertage mit abweichendem Limit)
- **Excel-Dateiname** (muss im `data/`-Verzeichnis liegen)
- **Rotationsintervall** und **Aktualisierungsintervall**

---

## Troubleshooting

### Service startet nicht

```bash
# Detaillierte Fehlermeldung anzeigen
sudo journalctl -u vacationviewer.service -n 50 --no-pager

# Häufige Ursachen:
# - EnvironmentFile /etc/vacationviewer/env fehlt oder hat falschen Pfad
# - .venv nicht erstellt (pip install -r requirements.txt fehlt)
# - collectstatic wurde nicht ausgeführt
```

### Seite lädt nicht / HTTP 500

```bash
# Gunicorn-Fehlerlog prüfen
tail -50 /var/log/vacationviewer/error.log

# Häufige Ursachen:
# - XLSX-Datei fehlt unter data/urlaub.xlsx
# - config/admin.json fehlt (hash_admin_password nicht ausgeführt)
```

### Font wird nicht geladen / Layout kaputt

```bash
# Prüfen ob collectstatic die Font-Dateien kopiert hat
ls /var/www/vacationviewer/staticfiles/screen/fonts/

# Falls leer: collectstatic erneut ausführen
source .venv/bin/activate
export $(sudo cat /etc/vacationviewer/env | grep -v '^#' | xargs)
python manage.py collectstatic --no-input
```

### Admin-Passwort zurücksetzen

```bash
cd /var/www/vacationviewer
source .venv/bin/activate
export $(sudo cat /etc/vacationviewer/env | grep -v '^#' | xargs)
python manage.py hash_admin_password
```

### Service nach Code-Update neu starten

```bash
cd /var/www/vacationviewer
git pull                                      # Code aktualisieren
source .venv/bin/activate
pip install -r requirements.txt               # Abhängigkeiten prüfen
python manage.py collectstatic --no-input     # Static Files neu einsammeln
sudo systemctl restart vacationviewer.service
```

---

## Schnell-Referenz: Wichtige Befehle

| Aktion | Befehl |
|--------|--------|
| Service-Status | `sudo systemctl status vacationviewer.service` |
| Service neu starten | `sudo systemctl restart vacationviewer.service` |
| Logs live verfolgen | `sudo journalctl -u vacationviewer.service -f` |
| App-Logs (Zugriff) | `tail -f /var/log/vacationviewer/access.log` |
| App-Logs (Fehler) | `tail -f /var/log/vacationviewer/error.log` |
| Passwort ändern | `python manage.py hash_admin_password` |
| Cache leeren | `sudo systemctl restart vacationviewer.service` |
| Kiosk-Browser neu starten | `sudo reboot` |

---

*VacationViewer · Branch: `hardening/production-ready` · Stand: 2026-03-03*
