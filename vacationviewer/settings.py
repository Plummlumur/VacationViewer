"""
Django settings for VacationViewer project.

TV-Info-Screen-Webapp for displaying vacation slot availability.
"""

import os
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Security: Load from env in production
SECRET_KEY: str = os.environ.get("SECRET_KEY", "django-insecure-vacationviewer-dev-key-change-in-production")
DEBUG: bool = os.environ.get("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS: list[str] = os.environ.get("ALLOWED_HOSTS", "*").split(",")

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
        "NAME": BASE_DIR / "db.sqlite3",
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

# --- VacationViewer Configuration (Defaults) ---

# Path to the XLSX vacation data file
XLSX_PATH: Path = BASE_DIR / "data" / "urlaub.xlsx"

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

# Path to admin credentials file
ADMIN_CREDENTIALS_PATH: Path = BASE_DIR / "config" / "admin.json"

# Path to runtime config overrides (written by admin UI)
CONFIG_OVERRIDE_PATH: Path = BASE_DIR / "config" / "settings_override.json"
