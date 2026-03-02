"""Django app configuration for the screen app."""

from django.apps import AppConfig


class ScreenConfig(AppConfig):
    """Configuration for the vacation screen app."""

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "screen"
    verbose_name: str = "Vacation Screen"
