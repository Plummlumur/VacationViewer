from django.db import models


class Employee(models.Model):
    """Employee model to store team members."""
    name = models.CharField(max_length=255, unique=True, verbose_name="Name")
    group = models.CharField(max_length=255, blank=True, null=True, verbose_name="Gruppe/Abteilung")

    class Meta:
        verbose_name = "Mitarbeiter"
        verbose_name_plural = "Mitarbeiter"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Vacation(models.Model):
    """Vacation model to store vacation periods for employees."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="vacations", verbose_name="Mitarbeiter")
    start_date = models.DateField(verbose_name="Von")
    end_date = models.DateField(verbose_name="Bis")

    class Meta:
        verbose_name = "Urlaub"
        verbose_name_plural = "Urlaube"
        ordering = ["start_date", "employee__name"]

    def __str__(self) -> str:
        return f"{self.employee.name}: {self.start_date} bis {self.end_date}"
