"""Data models for the XLSX ingest module."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class VacationRange:
    """A single vacation period for one person.

    Attributes:
        person_id: Anonymized identifier for the person.
        start: First day of the vacation period (inclusive).
        end: Last day of the vacation period (inclusive).
    """

    person_id: str
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"Vacation end ({self.end}) is before start ({self.start}) "
                f"for person {self.person_id}"
            )
