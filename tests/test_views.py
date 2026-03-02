"""Integration tests for views."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from django.test import RequestFactory

from screen.views import health, month_screen


@pytest.fixture
def rf() -> RequestFactory:
    """Django request factory."""
    return RequestFactory()


class TestHealthView:
    """Tests for the health check endpoint."""

    def test_returns_ok(self, rf: RequestFactory) -> None:
        """Health endpoint returns 200 with status ok."""
        # Arrange
        request = rf.get("/health/")

        # Act
        response = health(request)

        # Assert
        assert response.status_code == 200
        assert json.loads(response.content) == {"status": "ok"}


class TestMonthScreenView:
    """Tests for the month screen view."""

    @pytest.mark.django_db
    def test_renders_with_data(self, rf: RequestFactory, sample_xlsx: Path) -> None:
        """Month screen renders successfully with test data."""
        # Arrange
        request = rf.get("/")

        # Act
        with patch("screen.views.load_config") as mock_config:
            mock_config.return_value.xlsx_path = str(sample_xlsx)
            mock_config.return_value.refresh_minutes = 5
            mock_config.return_value.rotation_seconds = 10
            mock_config.return_value.vacation_limits = {i: 5 for i in range(7)}
            response = month_screen(request)

        # Assert
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Urlaubsübersicht" in content
        assert "März 2026" in content

    @pytest.mark.django_db
    def test_handles_missing_xlsx(self, rf: RequestFactory) -> None:
        """Month screen shows error when XLSX is missing."""
        # Arrange
        request = rf.get("/")

        # Act
        with patch("screen.views.load_config") as mock_config:
            mock_config.return_value.xlsx_path = "/nonexistent/file.xlsx"
            mock_config.return_value.refresh_minutes = 5
            mock_config.return_value.rotation_seconds = 10
            mock_config.return_value.vacation_limits = {i: 5 for i in range(7)}
            response = month_screen(request)

        # Assert
        assert response.status_code == 200  # empty state, no crash
