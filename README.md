# VacationViewer

TV-Info-Screen-Webapp zur Anzeige freier Urlaubsslots für ein Museumsteam (~40 Personen).  
Zeigt eine Monatsansicht als Kalender-Grid mit farbcodierten Status-Indikatoren.  
Datenquelle ist eine SQLite-Datenbank. Urlaubsdaten können manuell im Dashboard gepflegt oder via Excel (XLSX) importiert werden.

## Features

- **Monatsansicht** – Kalender-Grid (Mo–So) mit allen Tagen des Monats
- **Status pro Tag** – Frei (✓ grün), Belegt (● gelb), Limit erreicht (✗ rot)
- **Wochentag-Limits** – Unterschiedliche Max-Urlauber pro Wochentag
- **Auto-Rotation** – Wechselt automatisch zwischen Monaten (konfigurierbar)
- **Auto-Refresh** – Lädt Daten regelmäßig neu (aus DB-Cache)
- **Admin-Interface** – Login-geschütztes Dashboard zum Editieren aller Einstellungen
- **Barrierefreiheit** – Symbole + Text + Farbe, hoher Kontrast (WCAG AA), große Schrift

## Tech-Stack

| Komponente | Technologie |
|------------|-------------|
| Backend | Python 3.12, Django 5+ |
| Datenquelle | Excel (XLSX) via openpyxl |
| Frontend | Django Templates, Vanilla CSS/JS |
| Tests | pytest, pytest-django |
| Linting | ruff |

## Setup

```bash
# Repository klonen
git clone <repo-url>
cd VacationViewer

# Virtual Environment erstellen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Datenbank initialisieren (SQLite für Persistenz)
python manage.py makemigrations screen
python manage.py migrate

# Beispiel-XLSX als Arbeitsdatei kopieren
cp data/urlaub_example.xlsx data/urlaub.xlsx

# Server starten
python manage.py runserver
```

## URLs

| URL | Beschreibung |
|-----|-------------|
| `http://127.0.0.1:8000/` | Monatsansicht (TV-Screen) |
| `http://127.0.0.1:8000/admin/` | Admin-Login |
| `http://127.0.0.1:8000/admin/dashboard/` | Konfiguration editieren |
| `http://127.0.0.1:8000/health/` | Health-Check (`{"status": "ok"}`) |

## Konfiguration

### Default-Werte (`vacationviewer/settings.py`)

| Einstellung | Default | Beschreibung |
|-------------|---------|-------------|
| `XLSX_PATH` | `data/urlaub.xlsx` | Pfad zur Excel-Datei |
| `VACATION_LIMITS` | Mo–Fr: 5, Sa–So: 2 | Max. Urlauber pro Wochentag |
| `ROTATION_SECONDS` | 10 | Auto-Rotation zwischen Monaten |
| `REFRESH_MINUTES` | 5 | Daten-Refresh-Intervall |

Alle Werte sind über das **Admin-Dashboard** zur Laufzeit änderbar.  
Änderungen werden in `config/settings_override.json` gespeichert.

### Admin-Zugangsdaten

Standard-Credentials stehen in `config/admin.json`:

```json
{"username": "admin", "password": "admin"}
```

> ⚠️ Für den Produktivbetrieb unbedingt ändern! Die Datei ist per `.gitignore` vom Repo ausgeschlossen.

## XLSX-Schema

Die Excel-Datei muss folgende Spalten enthalten:

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `Person-ID` | Text | Anonyme Kennung (z.B. P001) |
| `Urlaubsstart` | Datum | Erster Urlaubstag (inklusiv) |
| `Urlaubsende` | Datum | Letzter Urlaubstag (inklusiv) |

Mehrere Zeilen pro Person sind möglich (mehrere Urlaubszeiträume).

## Tests

```bash
source .venv/bin/activate

# Alle Tests
pytest -v

# Linting
ruff check .
ruff format --check .

# Django System-Check
python manage.py check
```

## Deployment

### Variante A: Server + Smart-TV-Browser

1. Django auf internem Server starten (z.B. via `gunicorn`)
2. Smart-TV-Browser öffnet `http://<server>:8000/` im Vollbild
3. Auto-Rotation und Auto-Refresh laufen automatisch

### Variante B: Raspberry Pi + Kiosk-Modus

1. Raspberry Pi mit Chromium im Kiosk-Modus
2. Django lokal auf dem Pi starten
3. Chromium öffnet `http://127.0.0.1:8000/` im Vollbild

```bash
# Beispiel: Chromium Kiosk-Modus
chromium-browser --kiosk --noerrdialogs http://127.0.0.1:8000/
```

## Projektstruktur

```
VacationViewer/
├── manage.py                    # Django CLI
├── requirements.txt             # Dependencies
├── pytest.ini                   # Test-Konfiguration
├── config/
│   ├── admin.json               # Admin-Credentials
│   └── settings_override.json   # Runtime-Config (vom Admin-UI)
├── data/
│   ├── urlaub.xlsx              # Aktive Urlaubsdaten
│   └── urlaub_example.xlsx      # Beispiel-Datei
├── vacationviewer/              # Django-Projekt
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── screen/                      # Haupt-App
│   ├── views.py                 # TV-Screen View
│   ├── admin_views.py           # Admin Login + Dashboard
│   ├── config_manager.py        # Config Load/Save
│   ├── cache.py                 # In-Memory TTL-Cache (DB-basiert)
│   ├── services.py              # Excel-Import & Business-Logik
│   ├── models.py                # Employee & Vacation Modelle
│   ├── urls.py
│   ├── ingest/                  # XLSX-Parser
│   │   ├── parser.py
│   │   └── models.py
│   ├── domain/                  # Business-Logik
│   │   ├── slots.py
│   │   └── models.py
│   ├── templates/screen/
│   │   ├── month_screen.html
│   │   ├── admin_login.html
│   │   └── admin_dashboard.html
│   └── static/screen/
│       ├── css/style.css
│       └── js/rotation.js
└── tests/
    ├── conftest.py
    ├── test_parser.py
    ├── test_slots.py
    ├── test_views.py
    └── test_admin.py
```

## Datenupdate

1. Excel-Datei aktualisieren (Pfad siehe Admin-Dashboard oder `settings.py`)
2. Warten bis Auto-Refresh greift (Standard: 5 min) – oder Server neustarten
3. Alternativ: Im Admin-Dashboard „Speichern" klicken → Cache wird sofort invalidiert
