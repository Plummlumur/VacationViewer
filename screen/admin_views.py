"""Admin views for configuration management.

Provides login and dashboard views to edit runtime configuration.
Credentials are stored in config/admin.json (excluded from VCS via .gitignore).
Passwords must be PBKDF2-hashed — use `python manage.py hash_admin_password`.
"""

import json
import logging
import time
from collections import defaultdict
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

# ---------------------------------------------------------------------------
# Rate-Limiting (S-05): brute-force protection for admin login
# ---------------------------------------------------------------------------

_failed_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS: int = 5
_LOCKOUT_WINDOW_SECONDS: float = 300.0  # 5-minute sliding window


def _get_client_ip(request: HttpRequest) -> str:
    """Extract client IP, respecting X-Forwarded-For when behind a proxy."""
    forwarded_for: str | None = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        # Take the first (leftmost) IP — that's the original client
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _is_rate_limited(ip: str) -> bool:
    """Return True if the IP has exceeded the failed-login threshold."""
    now: float = time.monotonic()
    recent: list[float] = [
        t for t in _failed_attempts[ip] if now - t < _LOCKOUT_WINDOW_SECONDS
    ]
    _failed_attempts[ip] = recent
    return len(recent) >= _MAX_ATTEMPTS


def _record_failed_attempt(ip: str) -> None:
    """Record a failed login attempt for the given IP."""
    _failed_attempts[ip].append(time.monotonic())
    logger.warning("Failed login attempt from %s (total: %d)", ip, len(_failed_attempts[ip]))


# ---------------------------------------------------------------------------
# Credentials Loading & Verification (S-06)
# ---------------------------------------------------------------------------


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

    Only accepts PBKDF2-hashed passwords (S-06).
    Plaintext passwords are explicitly rejected with a log warning.

    Args:
        username: Submitted username.
        password: Submitted password.

    Returns:
        True if credentials match.
    """
    creds: dict[str, str] = _load_credentials()
    if not creds:
        return False

    stored_username: str | None = creds.get("username")
    stored_password: str | None = creds.get("password", "")

    if not stored_username or stored_username != username:
        return False

    if not stored_password:
        logger.error("Admin password field is empty in credentials file.")
        return False

    # Enforce hashed passwords only — no plaintext fallback (S-06)
    if not stored_password.startswith("pbkdf2_"):
        logger.error(
            "Admin password is stored in plaintext. "
            "Run: python manage.py hash_admin_password"
        )
        return False

    return check_password(password, stored_password)


# ---------------------------------------------------------------------------
# Login-Required Decorator
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def admin_login(request: HttpRequest) -> HttpResponse:
    """Admin login view with brute-force protection.

    GET: Render login form.
    POST: Validate credentials (rate-limited), set session, redirect to dashboard.

    Args:
        request: The HTTP request.

    Returns:
        Login form or redirect to dashboard.
    """
    # Already authenticated → go directly to dashboard
    if request.session.get("admin_authenticated"):
        return HttpResponseRedirect("/admin/dashboard/")

    error: str | None = None

    if request.method == "POST":
        client_ip: str = _get_client_ip(request)

        if _is_rate_limited(client_ip):
            logger.warning("Login blocked (rate limit) for IP: %s", client_ip)
            error = "Zu viele fehlgeschlagene Versuche. Bitte warte 5 Minuten."
        else:
            username: str = request.POST.get("username", "")
            password: str = request.POST.get("password", "")

            if _check_credentials(username, password):
                request.session.cycle_key()  # Prevent session fixation
                request.session["admin_authenticated"] = True
                logger.info("Successful admin login from %s", client_ip)
                return HttpResponseRedirect("/admin/dashboard/")

            _record_failed_attempt(client_ip)
            error = "Benutzername oder Passwort ist falsch."

    return render(request, "screen/admin_login.html", {"error": error})


def admin_logout(request: HttpRequest) -> HttpResponse:
    """Admin logout view. Accepts POST only (CSRF protection).

    GET requests are redirected to the login page without logging out.
    This prevents cross-site request forgery from silently ending sessions.

    Args:
        request: The HTTP request.

    Returns:
        Redirect to login page.
    """
    if request.method == "POST":
        client_ip: str = _get_client_ip(request)
        logger.info("Admin logout from %s", client_ip)
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
            def safe_int(val: str | None, default: int) -> int:
                if not val:
                    return default
                val = val.strip()
                return int(val) if val.isdigit() else default

            new_limits: dict[int, int] = {}
            for i in range(7):
                new_limits[i] = max(0, safe_int(request.POST.get(f"limit_{i}"), 5))

            exception_dates = request.POST.getlist("exception_dates[]")
            exception_limits = request.POST.getlist("exception_limits[]")

            new_exceptions: dict[str, int] = {}
            for edate, elimit in zip(exception_dates, exception_limits):
                edate = edate.strip()
                if edate and elimit.strip().isdigit():
                    new_exceptions[edate] = max(0, int(elimit.strip()))

            config.vacation_limits = new_limits
            config.day_exceptions = new_exceptions

            # S-08: restrict xlsx_path to the data directory
            raw_path: str = request.POST.get("xlsx_path", config.xlsx_path)
            config.xlsx_path = _validate_xlsx_path(raw_path, config.xlsx_path)

            config.rotation_seconds = max(
                1, safe_int(request.POST.get("rotation_seconds"), 10)
            )
            config.refresh_minutes = max(
                1, safe_int(request.POST.get("refresh_minutes"), 5)
            )

            save_config(config)
            invalidate_cache()
            success = True
            logger.info("Admin updated configuration")
        except Exception as e:
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
        "day_exceptions": config.day_exceptions.items(),
        "success": success,
    }

    return render(request, "screen/admin_dashboard.html", context)


# ---------------------------------------------------------------------------
# Path Validation Helper (S-08)
# ---------------------------------------------------------------------------


def _validate_xlsx_path(raw_path: str, current_path: str) -> str:
    """Restrict xlsx_path to the configured data directory.

    Prevents path traversal by ensuring the resolved path stays within
    BASE_DIR/data/. Falls back to current_path on violation.

    Args:
        raw_path: User-supplied path string from the form.
        current_path: Current valid path to fall back to on error.

    Returns:
        Sanitized, absolute path string.
    """
    allowed_dir: Path = Path(settings.BASE_DIR) / "data"
    try:
        # Only use the filename component to prevent directory traversal
        filename: str = Path(raw_path).name
        if not filename:
            raise ValueError("Empty filename")
        resolved: Path = (allowed_dir / filename).resolve()
        # Double-check the resolved path is still inside allowed_dir
        resolved.relative_to(allowed_dir.resolve())
        return str(resolved)
    except (ValueError, RuntimeError) as e:
        logger.warning(
            "Path traversal attempt blocked: %r → %s. Keeping current path.", raw_path, e
        )
        return current_path
