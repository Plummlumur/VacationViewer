"""Services for vacation data management."""

import logging
from pathlib import Path
from typing import Tuple

from screen.ingest.models import VacationRange
from screen.ingest.parser import load_xlsx
from screen.models import Employee, Vacation

logger: logging.Logger = logging.getLogger(__name__)


def import_vacations_from_excel(path: Path) -> Tuple[int, int]:
    """Import vacations from an Excel file into the database.

    Args:
        path: Path to the Excel file.

    Returns:
        A tuple of (records_created, records_skipped).
    """
    ranges = load_xlsx(path)
    created_count = 0
    skipped_count = 0

    for vr in ranges:
        # Get or create employee
        employee, _ = Employee.objects.get_or_create(name=vr.person_id)

        # Check for duplicate vacation range
        exists = Vacation.objects.filter(
            employee=employee,
            start_date=vr.start,
            end_date=vr.end
        ).exists()

        if not exists:
            Vacation.objects.create(
                employee=employee,
                start_date=vr.start,
                end_date=vr.end
            )
            created_count += 1
        else:
            skipped_count += 1
            logger.info(
                "Skipping duplicate vacation: %s (%s - %s)",
                employee.name, vr.start, vr.end
            )

    return created_count, skipped_count
