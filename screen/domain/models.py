"""Domain models for vacation slot computation."""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class DayStatus(Enum):
    """Status of a single day regarding vacation slot availability."""

    FREE = "free"
    OCCUPIED = "occupied"
    LIMIT_REACHED = "limit_reached"


@dataclass(frozen=True)
class DayData:
    """Computed data for a single day.

    Attributes:
        day: The calendar date.
        weekday: Day of week (0=Monday, 6=Sunday).
        vacation_count: Number of people on vacation this day.
        limit: Maximum allowed vacationers for this weekday.
        status: Computed availability status.
        free_slots: Number of remaining available slots.
    """

    day: date
    weekday: int
    vacation_count: int
    limit: int
    status: DayStatus
    free_slots: int


@dataclass(frozen=True)
class MonthData:
    """Aggregated vacation data for a single month.

    Attributes:
        year: Calendar year.
        month: Calendar month (1-12).
        days: List of DayData for all days in this month.
    """

    year: int
    month: int
    days: list[DayData]

    @property
    def label(self) -> str:
        """Human-readable month label in German."""
        month_names: dict[int, str] = {
            1: "Januar",
            2: "Februar",
            3: "März",
            4: "April",
            5: "Mai",
            6: "Juni",
            7: "Juli",
            8: "August",
            9: "September",
            10: "Oktober",
            11: "November",
            12: "Dezember",
        }
        return f"{month_names[self.month]} {self.year}"
