"""Tests for the XLSX ingest parser."""

import pytest
from datetime import date
from pathlib import Path

from screen.ingest.models import VacationRange
from screen.ingest.parser import expand_ranges, load_xlsx


class TestLoadXlsx:
    """Tests for load_xlsx function."""

    def test_loads_valid_xlsx(self, sample_xlsx: Path) -> None:
        """Valid XLSX is parsed into VacationRange objects."""
        # Arrange / Act
        ranges = load_xlsx(sample_xlsx)

        # Assert
        assert len(ranges) == 3
        assert all(isinstance(r, VacationRange) for r in ranges)
        assert ranges[0].person_id == "P001"
        assert ranges[0].start == date(2026, 3, 5)
        assert ranges[0].end == date(2026, 3, 10)

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        """FileNotFoundError for nonexistent file."""
        # Arrange
        path = tmp_path / "nonexistent.xlsx"

        # Act / Assert
        with pytest.raises(FileNotFoundError):
            load_xlsx(path)

    def test_raises_on_invalid_schema(self, invalid_schema_xlsx: Path) -> None:
        """ValueError when required columns are missing."""
        # Act / Assert
        with pytest.raises(ValueError, match="Schema validation failed"):
            load_xlsx(invalid_schema_xlsx)

    def test_skips_invalid_rows(self, bad_dates_xlsx: Path) -> None:
        """Rows with bad dates or empty Person-ID are skipped."""
        # Act
        ranges = load_xlsx(bad_dates_xlsx)

        # Assert – only the first valid row should be loaded
        assert len(ranges) == 1
        assert ranges[0].person_id == "P001"


class TestExpandRanges:
    """Tests for expand_ranges function."""

    def test_expands_single_range(self) -> None:
        """A single 3-day range produces 3 day entries."""
        # Arrange
        ranges = [VacationRange("P001", date(2026, 3, 5), date(2026, 3, 7))]

        # Act
        result = expand_ranges(ranges)

        # Assert
        assert result == {
            date(2026, 3, 5): 1,
            date(2026, 3, 6): 1,
            date(2026, 3, 7): 1,
        }

    def test_overlapping_ranges_sum_up(self) -> None:
        """Overlapping ranges from different people are summed."""
        # Arrange
        ranges = [
            VacationRange("P001", date(2026, 3, 5), date(2026, 3, 7)),
            VacationRange("P002", date(2026, 3, 6), date(2026, 3, 8)),
        ]

        # Act
        result = expand_ranges(ranges)

        # Assert
        assert result[date(2026, 3, 5)] == 1
        assert result[date(2026, 3, 6)] == 2  # overlap
        assert result[date(2026, 3, 7)] == 2  # overlap
        assert result[date(2026, 3, 8)] == 1

    def test_empty_ranges(self) -> None:
        """Empty input returns empty dict."""
        assert expand_ranges([]) == {}

    def test_single_day_range(self) -> None:
        """A range where start == end produces exactly one entry."""
        # Arrange
        ranges = [VacationRange("P001", date(2026, 3, 5), date(2026, 3, 5))]

        # Act
        result = expand_ranges(ranges)

        # Assert
        assert result == {date(2026, 3, 5): 1}
