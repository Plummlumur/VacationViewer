"""Management command to set the admin password."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = "Sets the admin password securely in the configuration file."

    def add_arguments(self, parser):
        parser.add_argument("password", type=str, help="The new plain text password")

    def handle(self, *args, **options):
        password = options["password"]
        hashed_password = make_password(password)
        
        cred_path = Path(getattr(settings, "ADMIN_CREDENTIALS_PATH", "config/admin.json"))
        cred_path.parent.mkdir(parents=True, exist_ok=True)
        
        creds = {}
        if cred_path.exists():
            with open(cred_path, "r", encoding="utf-8") as f:
                try:
                    creds = json.load(f)
                except json.JSONDecodeError:
                    pass
        
        creds["username"] = creds.get("username", "admin")
        creds["password"] = hashed_password
        
        with open(cred_path, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)
            
        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated admin credentials in {cred_path}")
        )
