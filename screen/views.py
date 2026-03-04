"""Views for the vacation screen app."""

import json
import logging
from datetime import date
from pathlib import Path

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from screen.cache import get_vacation_data
from screen.config_manager import load_config
from screen.domain.slots import get_visible_days, group_by_month

logger: logging.Logger = logging.getLogger(__name__)


def month_screen(request: HttpRequest) -> HttpResponse:
    """Render the TV-optimized month screen view.

    Loads vacation data, computes slot status per day, groups by month,
    and renders the calendar grid template.

    Args:
        request: The HTTP request.

    Returns:
        Rendered month screen template.
    """
    config = load_config()

    try:
        day_counts: dict[date, int] = get_vacation_data(
            ttl_minutes=config.refresh_minutes,
        )
    except Exception as e:
        logger.error("Failed to load vacation data: %s", e)
        return render(
            request,
            "screen/month_screen.html",
            {
                # S-09: Do NOT expose internal paths or exception details to the browser.
                # Full error is logged server-side via logger.error above.
                "error": "Urlaubsdaten konnten nicht geladen werden.",
                "months": [],
                "config_json": "{}",
            },
            status=500,
        )

    today: date = date.today()
    days = get_visible_days(
        day_counts,
        config.vacation_limits,
        today,
        config.day_exceptions,
    )
    months = group_by_month(days)

    # Prepare weekday headers
    weekday_names: list[str] = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

    # Config for JS (rotation, refresh)
    config_json: str = json.dumps(
        {
            "rotation_seconds": config.rotation_seconds,
            "refresh_minutes": config.refresh_minutes,
        }
    )

    context: dict = {
        "months": months,
        "today": today,
        "weekday_names": weekday_names,
        "config_json": config_json,
        "error": None,
    }

    return render(request, "screen/month_screen.html", context)


def health(request: HttpRequest) -> JsonResponse:
    """Health check endpoint.

    Args:
        request: The HTTP request.

    Returns:
        JSON response with status.
    """
    return JsonResponse({"status": "ok"})
