"""Vacation slot computation logic.

Computes day-level availability status based on vacation counts
and weekday-specific limits. Groups results by month for display.
"""

import calendar
from datetime import date
from itertools import groupby

from screen.domain.models import DayData, DayStatus, MonthData


def compute_day_status(vacation_count: int, limit: int) -> DayStatus:
    """Determine the availability status for a single day.

    Args:
        vacation_count: Number of people on vacation.
        limit: Maximum allowed vacationers for this weekday.

    Returns:
        DayStatus indicating availability.
    """
    if vacation_count >= limit:
        return DayStatus.LIMIT_REACHED
    if vacation_count > 0:
        return DayStatus.OCCUPIED
    return DayStatus.FREE


def get_visible_days(
    day_counts: dict[date, int],
    limits: dict[int, int],
    today: date,
    day_exceptions: dict[str, int] | None = None,
) -> list[DayData]:
    """Compute DayData for all visible days (today onwards).

    Generates data for the remaining days of the current month
    and all future months that have vacation data.

    Args:
        day_counts: Mapping of date to number of vacationers.
        limits: Mapping of weekday (0=Mon) to max allowed vacationers.
        today: Current date (days before this are excluded).
        day_exceptions: Mapping of ISO date string to specific limit override.

    Returns:
        List of DayData sorted by date.
    """
    if not day_counts:
        return []

    # Determine date range: from start of current month to end of last month with data
    max_date: date = max(day_counts.keys())

    # Start from today, include rest of current month + future months
    # We need full months for calendar grid, so start from 1st of current month
    current_month_start: date = today.replace(day=1)

    # End at last day of the month containing max_date (or at least current month)
    if max_date < today:
        # All data in the past, show at least current month
        last_day_of_month: int = calendar.monthrange(today.year, today.month)[1]
        end_date: date = today.replace(day=last_day_of_month)
    else:
        last_day_of_month = calendar.monthrange(max_date.year, max_date.month)[1]
        end_date = max_date.replace(day=last_day_of_month)

    days: list[DayData] = []
    current: date = current_month_start

    while current <= end_date:
        weekday: int = current.weekday()
        limit: int = limits.get(weekday, 5)
        
        # Apply day-specific exception if it exists
        if day_exceptions and current.isoformat() in day_exceptions:
            limit = day_exceptions[current.isoformat()]
            
        vacation_count: int = day_counts.get(current, 0)
        status: DayStatus = compute_day_status(vacation_count, limit)
        free_slots: int = max(0, limit - vacation_count)

        days.append(
            DayData(
                day=current,
                weekday=weekday,
                vacation_count=vacation_count,
                limit=limit,
                status=status,
                free_slots=free_slots,
            )
        )
        # Next day
        current = date.fromordinal(current.toordinal() + 1)

    return days


def group_by_month(days: list[DayData]) -> list[MonthData]:
    """Group a list of DayData into MonthData objects.

    Args:
        days: List of DayData, must be sorted by date.

    Returns:
        List of MonthData, one per month.
    """
    months: list[MonthData] = []

    for (year, month), group in groupby(days, key=lambda d: (d.day.year, d.day.month)):
        month_days: list[DayData] = list(group)
        months.append(MonthData(year=year, month=month, days=month_days))

    return months
