"""Management command to securely set the admin password.

Usage:
    python manage.py hash_admin_password

Prompts for a new password, hashes it with PBKDF2, and writes the
result into config/admin.json. The file is created if it doesn't exist.
"""

import getpass
import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Set or reset the admin password stored in config/admin.json."""

    help = "Interactively set the admin password (hashed with PBKDF2-SHA256)"

    def handle(self, *args: object, **options: object) -> None:
        cred_path: Path = Path(
            getattr(settings, "ADMIN_CREDENTIALS_PATH", "config/admin.json")
        )

        # Load existing data if present
        existing: dict[str, str] = {}
        if cred_path.exists():
            try:
                with open(cred_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.stdout.write(self.style.WARNING("Could not read existing credentials, starting fresh."))

        # Determine username
        current_username: str = existing.get("username", "admin")
        self.stdout.write(f"Current username: {current_username}")
        new_username: str = input(f"Username [{current_username}]: ").strip() or current_username

        # Prompt for password (twice for confirmation)
        while True:
            password: str = getpass.getpass("New password: ")
            if len(password) < 12:
                self.stdout.write(self.style.WARNING("Password must be at least 12 characters long. Try again."))
                continue
            password_confirm: str = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                self.stdout.write(self.style.WARNING("Passwords do not match. Try again."))
                continue
            break

        hashed: str = make_password(password)
        data: dict[str, str] = {"username": new_username, "password": hashed}

        cred_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cred_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Restrict file permissions (owner-read-only)
        cred_path.chmod(0o600)

        self.stdout.write(self.style.SUCCESS(f"Admin password updated successfully. Stored in: {cred_path}"))
