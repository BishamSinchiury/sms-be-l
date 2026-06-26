from django.db import models
from django.utils.translation import gettext_lazy as _
from organization.models import Organization
from core.models import TimestampModel


class UniversityLevel(TimestampModel):
    class LevelChoices(models.TextChoices):
        BACHELORS = "bachelors", _("Bachelors")
        MASTERS = "masters", _("Masters")
        DIPLOMA = "diploma", _("Diploma")
        PHD = "phd", _("PhD")

    name = models.CharField(
        max_length=50,
        choices=LevelChoices.choices,
    )

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="university_levels",
    )

    order = models.PositiveIntegerField()

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["order"]
        unique_together = [
            ("org", "name"),
            ("org", "order"),
        ]

    def __str__(self):
        return self.get_name_display()

    def delete(self, *args, **kwargs):
        raise NotImplementedError(
            "University levels cannot be deleted."
        )

class SchoolLevel(TimestampModel):
    class LevelChoices(models.TextChoices):
        PRE_SCHOOL = "pre_school", _("Pre School")
        PRE_PRIMARY = "pre_primary", _("Pre Primary")
        PRIMARY = "primary", _("Primary")
        LOWER_SECONDARY = "lower_secondary", _("Lower Secondary")
        SECONDARY = "secondary", _("Secondary")
        HIGHER_SECONDARY = "higher_secondary", _("Higher Secondary")

    name = models.CharField(
        max_length=50,
        choices=LevelChoices.choices,
    )

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="school_levels",
    )

    order = models.PositiveIntegerField()

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        unique_together = [
            ("org", "name"),
            ("org", "order"),
        ]

    def __str__(self):
        return self.get_name_display()

    def delete(self, *args, **kwargs):
        raise NotImplementedError(
            "School levels cannot be deleted."
        )