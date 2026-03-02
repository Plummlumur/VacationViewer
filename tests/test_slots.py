"""Tests for the domain slot computation logic."""

from datetime import date

from screen.domain.models import DayStatus, MonthData
from screen.domain.slots import compute_day_status, get_visible_days, group_by_month


class TestComputeDayStatus:
    """Tests for compute_day_status function."""

    def test_free_when_no_vacationers(self) -> None:
        """Status is FREE when nobody is on vacation."""
        assert compute_day_status(0, 5) == DayStatus.FREE

    def test_occupied_when_some_slots_used(self) -> None:
        """Status is OCCUPIED when some but not all slots are taken."""
        assert compute_day_status(3, 5) == DayStatus.OCCUPIED

    def test_limit_reached_at_exact_limit(self) -> None:
        """Status is LIMIT_REACHED when count equals limit."""
        assert compute_day_status(5, 5) == DayStatus.LIMIT_REACHED

    def test_limit_reached_above_limit(self) -> None:
        """Status is LIMIT_REACHED when count exceeds limit."""
        assert compute_day_status(7, 5) == DayStatus.LIMIT_REACHED

    def test_limit_zero(self) -> None:
        """With limit 0, any vacation count is LIMIT_REACHED, zero is FREE."""
        assert compute_day_status(0, 0) == DayStatus.LIMIT_REACHED
        assert compute_day_status(1, 0) == DayStatus.LIMIT_REACHED


class TestGetVisibleDays:
    """Tests for get_visible_days function."""

    def test_filters_past_days_from_start_of_month(
        self, default_limits: dict[int, int]
    ) -> None:
        """Days start from 1st of current month."""
        # Arrange
        day_counts = {date(2026, 3, 15): 2}
        today = date(2026, 3, 10)

        # Act
        days = get_visible_days(day_counts, default_limits, today)

        # Assert – should include all days of March (from 1st)
        assert days[0].day == date(2026, 3, 1)
        assert days[-1].day == date(2026, 3, 31)

    def test_uses_weekday_specific_limits(self) -> None:
        """Different weekdays get different limits."""
        # Arrange
        limits = {0: 5, 1: 5, 2: 5, 3: 5, 4: 5, 5: 2, 6: 2}
        day_counts = {
            date(2026, 3, 7): 3,  # Saturday
            date(2026, 3, 9): 3,  # Monday
        }
        today = date(2026, 3, 1)

        # Act
        days = get_visible_days(day_counts, limits, today)

        # Assert
        saturday = next(d for d in days if d.day == date(2026, 3, 7))
        monday = next(d for d in days if d.day == date(2026, 3, 9))

        assert saturday.limit == 2
        assert saturday.status == DayStatus.LIMIT_REACHED
        assert monday.limit == 5
        assert monday.status == DayStatus.OCCUPIED

    def test_empty_data_returns_empty_list(
        self, default_limits: dict[int, int]
    ) -> None:
        """No vacation data returns empty list."""
        assert get_visible_days({}, default_limits, date(2026, 3, 10)) == []

    def test_includes_future_months(
        self, default_limits: dict[int, int]
    ) -> None:
        """Days from future months with data are included."""
        # Arrange
        day_counts = {
            date(2026, 3, 15): 1,
            date(2026, 4, 10): 2,
        }
        today = date(2026, 3, 10)

        # Act
        days = get_visible_days(day_counts, default_limits, today)

        # Assert – should include through end of April
        assert any(d.day.month == 4 for d in days)
        assert days[-1].day == date(2026, 4, 30)

    def test_free_slots_calculated_correctly(
        self, default_limits: dict[int, int]
    ) -> None:
        """free_slots = max(0, limit - vacation_count)."""
        # Arrange
        day_counts = {date(2026, 3, 2): 3}  # Monday, limit=5
        today = date(2026, 3, 1)

        # Act
        days = get_visible_days(day_counts, default_limits, today)

        # Assert
        monday = next(d for d in days if d.day == date(2026, 3, 2))
        assert monday.free_slots == 2
        assert monday.vacation_count == 3


class TestGroupByMonth:
    """Tests for group_by_month function."""

    def test_groups_days_into_months(
        self, default_limits: dict[int, int]
    ) -> None:
        """Days spanning two months produce two MonthData objects."""
        # Arrange
        day_counts = {
            date(2026, 3, 15): 1,
            date(2026, 4, 10): 2,
        }
        days = get_visible_days(day_counts, default_limits, date(2026, 3, 1))

        # Act
        months = group_by_month(days)

        # Assert
        assert len(months) == 2
        assert months[0].month == 3
        assert months[0].year == 2026
        assert months[1].month == 4

    def test_single_month_data(
        self, default_limits: dict[int, int]
    ) -> None:
        """Single month of data produces one MonthData."""
        # Arrange
        day_counts = {date(2026, 3, 15): 1}
        days = get_visible_days(day_counts, default_limits, date(2026, 3, 1))

        # Act
        months = group_by_month(days)

        # Assert
        assert len(months) == 1
        assert isinstance(months[0], MonthData)
        assert months[0].label == "März 2026"
