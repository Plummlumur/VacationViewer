"""
Django settings for VacationViewer project.

TV-Info-Screen-Webapp for displaying vacation slot availability.

Production usage: set SECRET_KEY, DEBUG, ALLOWED_HOSTS via environment
variables or an EnvironmentFile (see deployment/vacationviewer_setup.sh).
"""

import os
import sys
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security-Critical Settings (S-01, S-03, S-04)
# Fail fast in production: no silent fallbacks for critical values.
# ---------------------------------------------------------------------------

_secret_key: str = os.environ.get("SECRET_KEY", "")
if not _secret_key:
    # Allow insecure dev key only when DEBUG is explicitly True
    _debug_env: str = os.environ.get("DEBUG", "")
    if _debug_env.lower() != "true":
        sys.exit(
            "FATAL: SECRET_KEY environment variable is not set. "
            "Generate one with: python -c \"from django.core.management.utils "
            "import get_random_secret_key; print(get_random_secret_key())\""
        )
    _secret_key = "django-insecure-vacationviewer-dev-key-DO-NOT-USE-IN-PRODUCTION"

SECRET_KEY: str = _secret_key

# DEBUG must be explicitly set — no implicit default.
# In dev: set DEBUG=True. In production: set DEBUG=False.
_debug_raw: str = os.environ.get("DEBUG", "")
if not _debug_raw:
    # Convenience: if no env set at all, assume dev mode but warn loudly.
    import warnings
    warnings.warn(
        "DEBUG environment variable is not set. Defaulting to True (dev mode). "
        "Set DEBUG=False for production.",
        stacklevel=1,
    )
    _debug_raw = "True"

DEBUG: bool = _debug_raw.lower() == "true"

# ALLOWED_HOSTS: never use '*' in production (S-04).
# Default to localhost-only for safety.
ALLOWED_HOSTS: list[str] = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

# ---------------------------------------------------------------------------
# Application Definition
# ---------------------------------------------------------------------------

INSTALLED_APPS: list[str] = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "screen",
]

MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF: str = "vacationviewer.urls"

TEMPLATES: list[dict] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION: str = "vacationviewer.wsgi.application"

DATABASES: dict = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.environ.get("DB_PATH", BASE_DIR / "db.sqlite3")),
    }
}

LANGUAGE_CODE: str = "de"
TIME_ZONE: str = "Europe/Berlin"
USE_I18N: bool = True
USE_TZ: bool = True

STATIC_URL: str = "static/"
STATICFILES_DIRS: list[Path] = []
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Session Security (S-11)
# Admin sessions expire after 1 hour of inactivity.
# ---------------------------------------------------------------------------

SESSION_COOKIE_AGE: int = 3600          # 1 hour in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE: bool = True
SESSION_COOKIE_HTTPONLY: bool = True
SESSION_COOKIE_SAMESITE: str = "Strict"
# SESSION_COOKIE_SECURE = True  # Enable when HTTPS is active

# ---------------------------------------------------------------------------
# Security Headers (S-12)
# ---------------------------------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF: bool = True
X_FRAME_OPTIONS: str = "DENY"

# HTTPS-only settings — enable when TLS termination is configured:
# SECURE_SSL_REDIRECT = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# VacationViewer Application Configuration (Defaults)
# ---------------------------------------------------------------------------

_data_dir: Path = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))

# Path to the XLSX vacation data file
XLSX_PATH: Path = _data_dir / "urlaub.xlsx"

# Max concurrent vacationers per weekday (0=Monday, 6=Sunday)
VACATION_LIMITS: dict[int, int] = {
    0: 5,  # Monday
    1: 5,  # Tuesday
    2: 5,  # Wednesday
    3: 5,  # Thursday
    4: 5,  # Friday
    5: 2,  # Saturday
    6: 2,  # Sunday
}

# Auto-rotation interval between months (seconds)
ROTATION_SECONDS: int = 10

# Data refresh interval (minutes)
REFRESH_MINUTES: int = 5

_config_dir: Path = Path(os.environ.get("CONFIG_DIR", BASE_DIR / "config"))

# Path to admin credentials file
ADMIN_CREDENTIALS_PATH: Path = _config_dir / "admin.json"

# Path to runtime config overrides (written by admin UI)
CONFIG_OVERRIDE_PATH: Path = _config_dir / "settings_override.json"
