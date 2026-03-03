# VacationViewer – Production Hardening Guide

> **Status**: Prototype / Development → Production
> **Zielplattform**: Raspberry Pi (Debian/Raspberry Pi OS) + Gunicorn + Nginx

---

## Security Audit – Key Findings

### Tabellarische Übersicht

| # | Severity | Kategorie | Befund | Datei(en) |
|---|----------|-----------|--------|-----------|
| **S-01** | 🔴 CRITICAL | Secrets | `SECRET_KEY` hat einen hartcodierten Fallback-Wert im Source-Code. Bei leerem `SECRET_KEY`-Env startet die App mit einem bekannten, vorhersehbaren Key (Session-Hijacking, CSRF-Bypass möglich). | `settings.py:14` |
| **S-02** | 🔴 CRITICAL | Deployment | Das Setup-Script startet die App mit `manage.py runserver` als Systemd-Service. Djangos Dev-Server ist **ausdrücklich nicht für Produktion geeignet**: Single-Threaded, kein Request-Timeout, kein TLS, gibt Debug-Informationen preis. | `vacationviewer_setup.sh:51` |
| **S-03** | 🔴 CRITICAL | Config | `DEBUG=True` ist der Default-Wert via Env-Fallback. In Produktion ohne explizit gesetztes Env würde die App mit aktiviertem Debug-Mode laufen (vollständiger Stacktrace inkl. Env-Vars im Browser bei Fehlern). | `settings.py:16` |
| **S-04** | 🟠 HIGH | Config | `ALLOWED_HOSTS = "*"` ist der Default. Ohne Env-Variable akzeptiert die App HTTP-Requests von beliebigen Hostheadern → HTTP Host Header Injection. | `settings.py:17` |
| **S-05** | 🟠 HIGH | Auth | Kein Brute-Force-Schutz auf dem Login-Endpunkt (`/admin/login/`). Unbegrenzte POST-Versuche möglich. Kein Rate-Limit, kein Account-Lockout, kein CAPTCHA. | `admin_views.py:101-124` |
| **S-06** | 🟠 HIGH | Auth | Fallback-Pfad bei `stored_password` ohne PBKDF2-Präfix führt zu **Klartext-Passwort-Vergleich** (`stored_password == password`). Falls `admin.json` je ohne gehashtes Passwort angelegt wird, ist der Vergleich timing-unsicher (kein `hmac.compare_digest`). | `admin_views.py:77` |
| **S-07** | 🟠 HIGH | Secrets | `config/admin.json` ist in `.gitignore` **auskommentiert** (`# config/admin.json`). Das Credentials-File wird damit ins Repository committed, inklusive PBKDF2-Hash. | `.gitignore:17` |
| **S-08** | 🟡 MEDIUM | Path Traversal | `config.xlsx_path` wird aus dem Admin-Dashboard vom User gesetzt und direkt als Dateisystempfad verwendet, ohne Validierung oder Pfad-Normalisierung. Ein Angreifer mit Adminzugang kann beliebige Dateipfade setzten (z.B. `/etc/passwd`). Das Parsing via openpyxl würde fehlschlagen, aber der Pfad wird im Error-Log geloggt. | `admin_views.py:179`, `views.py:34` |
| **S-09** | 🟡 MEDIUM | Info Disclosure | Im Fehlerfall (XLSX nicht gefunden) wird die vollständige Exception-Message inkl. Dateipfad an das Template (`error`-Variable) übergeben und im Browser angezeigt. | `views.py:42` |
| **S-10** | 🟡 MEDIUM | External Deps | Google Fonts werden via externem CDN eingebunden (`fonts.googleapis.com`). Auf einem Kiosk-System ggf. ohne Internetzugang funktioniert das Layout nicht. Datenschutz-relevant (IP-Logging bei Google). Kein SRI-Hash (Subresource Integrity). | `admin_login.html:9-10`, `admin_dashboard.html:9-10`, `month_screen.html:11-12` |
| **S-11** | 🟡 MEDIUM | Session | Session-Daten liegen standardmäßig in der SQLite-DB (Django Default). Kein Session-Expiry konfiguriert. Eine Admin-Session läuft theoretisch unbegrenzt. | `settings.py` (fehlt) |
| **S-12** | 🟡 MEDIUM | Headers | Django `SecurityMiddleware` ist zwar aktiv, aber keine HSTS-Settings (`SECURE_HSTS_SECONDS` etc.) konfiguriert. `SECURE_BROWSER_XSS_FILTER` und `SECURE_CONTENT_TYPE_NOSNIFF` fehlen. | `settings.py` (fehlt) |
| **S-13** | 🟡 MEDIUM | Deployment | Das Setup-Skript läuft als `User=pi` ohne `EnvironmentFile`. Secrets (SECRET_KEY etc.) müssten in das Skript hardcodiert oder separat verwaltet werden – kein klarer Mechanismus vorhanden. | `vacationviewer_setup.sh:51` |
| **S-14** | 🟢 LOW | Cache | `CachedData` ist kein Thread-Safe-Singleton (kein Lock). Bei einem Multi-Worker-Setup (Gunicorn mit `--workers > 1`) kann es zu Race Conditions beim Cache-Refresh kommen. Im Raspberry-Pi-Kontext (1 Worker) unkritisch. | `cache.py:16-68` |
| **S-15** | 🟢 LOW | Logout | Logout via `GET /admin/logout/`. Ein einfacher Link reicht – kein CSRF-Token nötig bei GET. Aber: Bei CSRF-Angriffen könnte ein User ungewollt ausloggt werden. Empfehlung: POST + CSRF. | `admin_views.py:127`, `admin_dashboard.html:243` |
| **S-16** | 🟢 LOW | Dependencies | `pytest` und `ruff` in `requirements.txt` – Dev-Dependencies in Production-Deps. Unnötiger Angriff auf die Installierte Oberfläche (Attack Surface). | `requirements.txt:4-6` |
| **S-17** | 🟢 LOW | Versions | `defusedxml 0.7.1` ist die aktuellste stabile Version (kein Update nötig). `openpyxl 3.1.5` ist aktuell. Django `>=5.1` ist aktuell und supported. Keine deprecated Libraries gefunden. | `requirements.txt` |

---

## Detailbeschreibung & Fixes

### S-01 – Hardcodierter SECRET_KEY Fallback

**Problem**: `os.environ.get("SECRET_KEY", "django-insecure-...")` verwendet einen bekannten Fallback.

**Fix**:
```python
# settings.py
import sys

_secret = os.environ.get("SECRET_KEY", "")
if not _secret:
    sys.exit("FATAL: SECRET_KEY environment variable is not set.")
SECRET_KEY: str = _secret
```

---

### S-02 – Dev-Server in Produktion (KRITISCH)

**Problem**: `manage.py runserver 0.0.0.0:8000` im Systemd-Service.

**Fix**: Gunicorn + Nginx als Reverse-Proxy. Siehe Schritt-für-Schritt unten.

---

### S-03 – DEBUG Default True

**Problem**: Ohne Env-Variable läuft die App im Debug-Modus.

**Fix**:
```python
# settings.py – Fail fast statt Fallback
_debug_env = os.environ.get("DEBUG", "")
if not _debug_env:
    sys.exit("FATAL: DEBUG environment variable must be explicitly set (True/False).")
DEBUG: bool = _debug_env.lower() == "true"
```

---

### S-04 – ALLOWED_HOSTS Wildcard

**Fix**:
```python
ALLOWED_HOSTS: list[str] = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
```
In Produktion: `ALLOWED_HOSTS=127.0.0.1,<pi-hostname>` in der EnvironmentFile.

---

### S-05 – Kein Brute-Force-Schutz

**Option A (einfach)**: Rate-Limiting via Nginx (`limit_req_zone`).

**Option B (in Django)**: Eigenes Login-Throttling implementieren:
```python
# admin_views.py
import time
from collections import defaultdict

_failed_attempts: dict[str, list[float]] = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 Minuten

def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _failed_attempts[ip] if now - t < WINDOW_SECONDS]
    _failed_attempts[ip] = attempts
    return len(attempts) >= MAX_ATTEMPTS

def _record_failed_attempt(ip: str) -> None:
    _failed_attempts[ip].append(time.time())
```

---

### S-06 – Klartext-Passwort-Fallback

**Fix**: Klartext-Fallback entfernen. Nur PBKDF2 erlauben:
```python
def _check_credentials(username: str, password: str) -> bool:
    creds = _load_credentials()
    if not creds:
        return False
    stored_username = creds.get("username")
    stored_password = creds.get("password", "")
    if not stored_username or stored_username != username:
        return False
    if not stored_password.startswith("pbkdf2_"):
        logger.error("Admin password is not hashed. Run: python manage.py hash_admin_password")
        return False
    return check_password(password, stored_password)
```

---

### S-07 – admin.json im Git

**Fix**: `.gitignore` korrigieren:
```gitignore
# Config (sensitive) – KEIN Auskommentieren!
config/admin.json
config/settings_override.json
```
Dann aus dem Git-History entfernen:
```bash
git rm --cached config/admin.json
git commit -m "security: remove admin.json from tracking"
```

---

### S-08 – Path Traversal bei xlsx_path

**Fix**:
```python
# admin_views.py – Pfad auf erlaubtes Verzeichnis beschränken
from pathlib import Path

def _validate_xlsx_path(raw_path: str) -> str:
    """Ensure path stays within the data directory."""
    allowed_dir = Path(settings.BASE_DIR) / "data"
    resolved = (allowed_dir / Path(raw_path).name).resolve()
    if not str(resolved).startswith(str(allowed_dir.resolve())):
        raise ValueError(f"Path traversal attempt: {raw_path}")
    return str(resolved)
```

---

### S-09 – Exception-Pfade im Browser

**Fix**: In `views.py` nur eine generische Fehlermeldung zurückgeben:
```python
return render(
    request,
    "screen/month_screen.html",
    {"error": "Urlaubsdaten konnten nicht geladen werden.", "months": [], "config_json": "{}"},
    status=500,
)
```

---

### S-10 – Google Fonts (Extern + kein SRI)

**Fix**: Fonts lokal hosten — Inter-Font herunterladen und als Static File einbinden:
```html
<!-- Statt Google Fonts CDN: -->
<link rel="stylesheet" href="{% static 'screen/css/fonts.css' %}">
```

---

### S-11 – Session Expiry

**Fix** in `settings.py`:
```python
SESSION_COOKIE_AGE = 3600          # 1 Stunde
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
# SESSION_COOKIE_SECURE = True     # Nur wenn HTTPS aktiv
```

---

### S-12 – Security-Headers

**Fix** in `settings.py`:
```python
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True   # Legacy, aber schadet nicht
X_FRAME_OPTIONS = "DENY"
```
Mit HTTPS (empfohlen):
```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

---

### S-16 – Dev-Deps in requirements.txt

**Fix**: Aufteilen in zwei Files:
- `requirements.txt` → nur `django`, `openpyxl`, `defusedxml`, `gunicorn`, `whitenoise`
- `requirements-dev.txt` → `pytest`, `pytest-django`, `ruff`

---

## Production Deployment – Schritt-für-Schritt

### Architektur

```
Browser (Chromium Kiosk)
        │
        ▼
   Nginx :80
  (Reverse Proxy + Static Files)
        │
        ▼
  Gunicorn :8000
  (WSGI App Server, 2 Workers)
        │
        ▼
  Django App (VacationViewer)
        │
        ▼
   SQLite DB + XLSX-Datei
```

### 1. Abhängigkeiten installieren

```bash
pip install gunicorn whitenoise
```

**`requirements.txt` (Produktion)**:
```text
django>=5.1,<6.0
openpyxl>=3.1,<4.0
defusedxml>=0.7.1
gunicorn>=21.0,<23.0
whitenoise>=6.6,<7.0
```

**`requirements-dev.txt`**:
```text
-r requirements.txt
pytest>=8.0
pytest-django>=4.8
ruff>=0.9
```

### 2. Settings für Produktion

`settings.py` muss per Umgebungsvariablen gesteuert werden. Erstelle die Datei `/etc/vacationviewer/env`:

```bash
# /etc/vacationviewer/env  (chmod 600, owner: root)
SECRET_KEY=<generieren mit: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")>
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,<hostname-des-pi>
```

### 3. WhiteNoise für Static Files

Da kein separater Static-File-Server vorhanden, WhiteNoise verwenden:

```python
# settings.py
MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # direkt nach Security
    ...
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
```

Static Files einsammeln:
```bash
python manage.py collectstatic --no-input
```

### 4. Gunicorn Systemd Service

Ersetze den bisherigen Service-Eintrag im Setup-Skript:

```ini
# /etc/systemd/system/vacationviewer.service
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

[Install]
WantedBy=multi-user.target
```

Log-Verzeichnis anlegen:
```bash
sudo mkdir -p /var/log/vacationviewer
sudo chown pi:www-data /var/log/vacationviewer
```

### 5. Nginx als Reverse Proxy (optional, aber empfohlen)

Da es sich um ein internes Kiosk-System handelt und der Chromium-Browser nur auf `127.0.0.1:8000` zugreift, ist Nginx optional. Für externe Erreichbarkeit (Admin-Zugriff) empfohlen:

```nginx
# /etc/nginx/sites-available/vacationviewer
server {
    listen 80;
    server_name <pi-hostname>.local;

    location /static/ {
        alias /var/www/vacationviewer/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 30;
    }

    # Rate-Limiting für Login
    location /admin/login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

Rate-Limit-Zone in `nginx.conf`:
```nginx
http {
    limit_req_zone $binary_remote_addr zone=login:10m rate=3r/m;
    ...
}
```

### 6. admin.json aus Git entfernen

```bash
git rm --cached config/admin.json
echo "config/admin.json" >> .gitignore
git add .gitignore
git commit -m "security: exclude admin credentials from version control"
```

### 7. Passwort für Produktion neu setzen

```bash
# Sicheres Passwort hashen und in admin.json schreiben
python -c "
from django.contrib.auth.hashers import make_password
import json, getpass
pw = getpass.getpass('New admin password: ')
data = {'username': 'admin', 'password': make_password(pw)}
with open('config/admin.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Done. Hash stored.')
"
```

### 8. Deployment Checklist

Vor dem Go-Live diese Punkte abhaken:

```
[ ] SECRET_KEY in EnvironmentFile gesetzt (neu generiert, nicht aus Dev)
[ ] DEBUG=False gesetzt
[ ] ALLOWED_HOSTS enthält nur erlaubte Hostnamen (kein *)
[ ] admin.json aus Git-Tracking entfernt
[ ] Passwort neu gesetzt (starkes Passwort, min. 16 Zeichen)
[ ] gunicorn läuft (kein manage.py runserver)
[ ] collectstatic ausgeführt
[ ] python manage.py check --deploy bestanden (keine Warnungen)
[ ] Session-Expiry konfiguriert
[ ] Security-Header konfiguriert (NOSNIFF, X-FRAME)
[ ] Google Fonts lokal gehostet (optional, aber empfohlen)
[ ] requirements.txt aufgeteilt (dev-deps entfernt)
[ ] config/admin.json chmod 600 (nur App-User lesbar)
[ ] Log-Rotation für journald/gunicorn konfiguriert
```

### 9. Django Deployment Check

```bash
DJANGO_SETTINGS_MODULE=vacationviewer.settings \
SECRET_KEY=<key> DEBUG=False ALLOWED_HOSTS=localhost \
python manage.py check --deploy
```

Dieser Befehl zeigt verbleibende Sicherheitsprobleme.

---

## Bibliotheken – Versionsstatus

| Library | Aktuelle Version | Produktionsstatus | Anmerkung |
|---------|-----------------|-------------------|-----------|
| `django` | `5.1.x` | ✅ Supported (LTS bis 2028 bei 4.2, 5.2 LTS ab Apr 2025) | `5.1` ist kein LTS-Release; auf `5.2 LTS` upgraden sobald verfügbar |
| `openpyxl` | `3.1.5` | ✅ Aktuell | Keine bekannten CVEs |
| `defusedxml` | `0.7.1` | ✅ Aktuell | Schützt gegen XML-Injection, korrekt eingesetzt |
| `pytest` | `8.x` | ⚠️ Dev-Only | Nicht in Produktion installieren |
| `ruff` | `0.9.x` | ⚠️ Dev-Only | Nicht in Produktion installieren |
| `gunicorn` | – | ➕ Hinzufügen | WSGI Production Server |
| `whitenoise` | – | ➕ Hinzufügen | Static File Serving ohne Nginx |

---

*Erstellt: 2026-03-03 | VacationViewer v0.9a*
