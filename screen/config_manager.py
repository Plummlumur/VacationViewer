"""Configuration manager for runtime config overrides.

Reads defaults from Django settings, overlays with values from
config/settings_override.json (written by the admin UI).
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from django.conf import settings

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Runtime-configurable application settings.

    Attributes:
        vacation_limits: Max vacationers per weekday (0=Mon, 6=Sun).
        rotation_seconds: Auto-rotation interval in seconds.
        refresh_minutes: Data refresh interval in minutes.
    """

    vacation_limits: dict[int, int] = field(default_factory=dict)
    day_exceptions: dict[str, int] = field(default_factory=dict)
    rotation_seconds: int = 10
    refresh_minutes: int = 5


def load_config() -> AppConfig:
    """Load configuration with overrides from JSON file.

    Priority: settings_override.json > Django settings.py defaults.

    Returns:
        Merged AppConfig with all runtime values.
    """
    # Start with Django settings defaults
    config = AppConfig(
        vacation_limits=dict(getattr(settings, "VACATION_LIMITS", {})),
        rotation_seconds=int(getattr(settings, "ROTATION_SECONDS", 10)),
        refresh_minutes=int(getattr(settings, "REFRESH_MINUTES", 5)),
    )

    # Overlay with JSON overrides if file exists
    override_path: Path = Path(getattr(settings, "CONFIG_OVERRIDE_PATH", ""))
    if override_path.exists():
        try:
            with open(override_path, "r", encoding="utf-8") as f:
                overrides: dict = json.load(f)

            if "vacation_limits" in overrides:
                # JSON keys are strings, convert to int
                config.vacation_limits = {
                    int(k): int(v) for k, v in overrides["vacation_limits"].items()
                }
            if "day_exceptions" in overrides:
                config.day_exceptions = {
                    str(k): int(v) for k, v in overrides["day_exceptions"].items()
                }

            if "rotation_seconds" in overrides:
                config.rotation_seconds = int(overrides["rotation_seconds"])
            if "refresh_minutes" in overrides:
                config.refresh_minutes = int(overrides["refresh_minutes"])

            logger.info("Loaded config overrides from %s", override_path)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to load config overrides: %s", e)

    return config


def save_config(config: AppConfig) -> None:
    """Save configuration overrides to JSON file.

    Args:
        config: The AppConfig to persist.
    """
    override_path: Path = Path(getattr(settings, "CONFIG_OVERRIDE_PATH", ""))

    # Ensure directory exists
    override_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert int keys to strings for JSON serialization
    data: dict = asdict(config)
    data["vacation_limits"] = {str(k): v for k, v in config.vacation_limits.items()}
    # day_exceptions keys are already strings, but ensuring serialization safety
    data["day_exceptions"] = {str(k): int(v) for k, v in config.day_exceptions.items()}

    with open(override_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Saved config overrides to %s", override_path)
