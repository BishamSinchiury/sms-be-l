from django.db import models
from organization.models import Organization
from core.models import TimestampModel
from .levels import UniversityLevel


class Program(TimestampModel):
    name = models.CharField(
        max_length=100,
    )

    short = models.CharField(
        max_length=10,
    )

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="programs",
    )

    level = models.ForeignKey(
        UniversityLevel,
        on_delete=models.PROTECT,
        related_name="programs",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["level__order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["org", "name"],
                name="unique_program_name_per_org",
            ),
        ]

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        raise NotImplementedError(
            "Programs cannot be deleted."
        )