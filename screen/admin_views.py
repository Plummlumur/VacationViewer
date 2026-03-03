"""Admin views for configuration management.

Provides login and dashboard views to edit runtime configuration.
Credentials are stored in config/admin.json.
"""

import json
import logging
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from screen.cache import invalidate_cache
from screen.config_manager import AppConfig, load_config, save_config

logger: logging.Logger = logging.getLogger(__name__)

WEEKDAY_LABELS: list[str] = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]


def _load_credentials() -> dict[str, str]:
    """Load admin credentials from JSON file.

    Returns:
        Dict with 'username' and 'password' keys.
    """
    cred_path: Path = Path(
        getattr(settings, "ADMIN_CREDENTIALS_PATH", "config/admin.json")
    )
    if not cred_path.exists():
        logger.warning("Admin credentials file not found: %s", cred_path)
        return {}
    try:
        with open(cred_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load admin credentials: %s", e)
        return {}


def _check_credentials(username: str, password: str) -> bool:
    """Verify username and password against stored credentials.

    Args:
        username: Submitted username.
        password: Submitted password.

    Returns:
        True if credentials match.
    """
    creds: dict[str, str] = _load_credentials()
    if not creds:
        return False
        
    stored_username = creds.get("username")
    stored_password = creds.get("password")
    
    if not stored_username or stored_username != username or not stored_password:
        return False
        
    if stored_password.startswith("pbkdf2_"):
        return check_password(password, stored_password)
        
    return stored_password == password


def login_required(
    view_func: Callable[..., HttpResponse],
) -> Callable[..., HttpResponse]:
    """Decorator to require admin login via session.

    Args:
        view_func: The view function to protect.

    Returns:
        Wrapped view function.
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.session.get("admin_authenticated"):
            return HttpResponseRedirect("/admin/login/")
        return view_func(request, *args, **kwargs)

    return wrapper


def admin_login(request: HttpRequest) -> HttpResponse:
    """Admin login view.

    GET: Render login form.
    POST: Validate credentials, set session, redirect to dashboard.

    Args:
        request: The HTTP request.

    Returns:
        Login form or redirect to dashboard.
    """
    error: str | None = None

    if request.method == "POST":
        username: str = request.POST.get("username", "")
        password: str = request.POST.get("password", "")

        if _check_credentials(username, password):
            request.session["admin_authenticated"] = True
            return HttpResponseRedirect("/admin/dashboard/")
        error = "Benutzername oder Passwort ist falsch."

    return render(request, "screen/admin_login.html", {"error": error})


def admin_logout(request: HttpRequest) -> HttpResponse:
    """Admin logout view. Clears session and redirects to login.

    Args:
        request: The HTTP request.

    Returns:
        Redirect to login page.
    """
    request.session.flush()
    return HttpResponseRedirect("/admin/login/")


@login_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    """Admin dashboard for editing configuration.

    GET: Show current config in form.
    POST: Save updated config and redirect back.

    Args:
        request: The HTTP request.

    Returns:
        Dashboard form or redirect after save.
    """
    config: AppConfig = load_config()
    success: bool = False

    if request.method == "POST":
        try:
            # Parse weekday limits from form
            new_limits: dict[int, int] = {}
            for i in range(7):
                val: str = request.POST.get(f"limit_{i}", "5")
                new_limits[i] = max(0, int(val))

            config.vacation_limits = new_limits
            config.xlsx_path = request.POST.get("xlsx_path", config.xlsx_path)
            config.rotation_seconds = max(
                1, int(request.POST.get("rotation_seconds", "10"))
            )
            config.refresh_minutes = max(
                1, int(request.POST.get("refresh_minutes", "5"))
            )

            save_config(config)
            invalidate_cache()
            success = True
            logger.info("Admin updated configuration")
        except (ValueError, TypeError) as e:
            logger.error("Invalid config input: %s", e)

    context: dict = {
        "config": config,
        "weekday_labels": WEEKDAY_LABELS,
        "weekday_limits": [
            {
                "index": i,
                "label": WEEKDAY_LABELS[i],
                "limit": config.vacation_limits.get(i, 5),
            }
            for i in range(7)
        ],
        "success": success,
    }

    return render(request, "screen/admin_dashboard.html", context)
