"""Tests for admin views and config manager."""

import json
import pytest
from pathlib import Path

from django.test import RequestFactory

from screen.admin_views import admin_login, _check_credentials
from screen.config_manager import AppConfig, load_config, save_config


@pytest.fixture
def rf() -> RequestFactory:
    """Django request factory."""
    return RequestFactory()


@pytest.fixture
def admin_credentials(tmp_path: Path, settings) -> Path:
    """Create temporary admin credentials file."""
    cred_path = tmp_path / "admin.json"
    cred_path.write_text(json.dumps({"username": "testadmin", "password": "testpass"}))
    settings.ADMIN_CREDENTIALS_PATH = cred_path
    return cred_path


@pytest.fixture
def config_override_path(tmp_path: Path, settings) -> Path:
    """Set up temporary config override path."""
    override_path = tmp_path / "settings_override.json"
    settings.CONFIG_OVERRIDE_PATH = override_path
    return override_path


class TestCheckCredentials:
    """Tests for credential verification."""

    @pytest.mark.django_db
    def test_valid_credentials(self, admin_credentials: Path) -> None:
        """Correct credentials return True."""
        assert _check_credentials("testadmin", "testpass") is True

    @pytest.mark.django_db
    def test_wrong_password(self, admin_credentials: Path) -> None:
        """Wrong password returns False."""
        assert _check_credentials("testadmin", "wrong") is False

    @pytest.mark.django_db
    def test_wrong_username(self, admin_credentials: Path) -> None:
        """Wrong username returns False."""
        assert _check_credentials("wrong", "testpass") is False


class TestAdminLogin:
    """Tests for admin login view."""

    @pytest.mark.django_db
    def test_get_renders_form(self, rf: RequestFactory) -> None:
        """GET request renders login form."""
        request = rf.get("/admin/login/")
        response = admin_login(request)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Benutzername" in content

    @pytest.mark.django_db
    def test_post_with_valid_credentials_redirects(
        self, rf: RequestFactory, admin_credentials: Path
    ) -> None:
        """POST with correct credentials redirects to dashboard."""
        from django.contrib.sessions.backends.db import SessionStore

        request = rf.post(
            "/admin/login/", {"username": "testadmin", "password": "testpass"}
        )
        request.session = SessionStore()
        response = admin_login(request)
        assert response.status_code == 302
        assert "/admin/dashboard/" in response.url

    @pytest.mark.django_db
    def test_post_with_invalid_credentials_shows_error(
        self, rf: RequestFactory, admin_credentials: Path
    ) -> None:
        """POST with wrong credentials shows error message."""
        request = rf.post("/admin/login/", {"username": "wrong", "password": "wrong"})
        request.session = {}
        response = admin_login(request)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "falsch" in content


class TestConfigManager:
    """Tests for config load/save."""

    @pytest.mark.django_db
    def test_load_defaults(self, config_override_path: Path) -> None:
        """Without override file, defaults from settings are used."""
        config = load_config()
        assert isinstance(config, AppConfig)
        assert isinstance(config.vacation_limits, dict)

    @pytest.mark.django_db
    def test_save_and_load(self, config_override_path: Path) -> None:
        """Saved config can be loaded back."""
        # Arrange
        config = AppConfig(
            vacation_limits={0: 3, 1: 3, 2: 4, 3: 4, 4: 5, 5: 1, 6: 1},
            xlsx_path="/data/test.xlsx",
            rotation_seconds=15,
            refresh_minutes=3,
        )

        # Act
        save_config(config)
        loaded = load_config()

        # Assert
        assert loaded.vacation_limits == config.vacation_limits
        assert loaded.rotation_seconds == 15
        assert loaded.refresh_minutes == 3
