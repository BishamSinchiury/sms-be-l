from django.db import models
from django.utils.translation import gettext_lazy as _
from organization.models import Organization
from core.models import TimestampModel
from .levels import SchoolLevel


class Grade(TimestampModel):
    class GradeChoices(models.TextChoices):
        PRESCHOOL = "preschool", _("Preschool")
        NURSERY = "nursery", _("Nursery")
        LKG = "lkg", _("LKG")
        UKG = "ukg", _("UKG")
        ONE = "1", _("Grade 1")
        TWO = "2", _("Grade 2")
        THREE = "3", _("Grade 3")
        FOUR = "4", _("Grade 4")
        FIVE = "5", _("Grade 5")
        SIX = "6", _("Grade 6")
        SEVEN = "7", _("Grade 7")
        EIGHT = "8", _("Grade 8")
        NINE = "9", _("Grade 9")
        TEN = "10", _("Grade 10")
        ELEVEN = "11", _("Grade 11")
        TWELVE = "12", _("Grade 12")

    name = models.CharField(
        max_length=20,
        choices=GradeChoices.choices,
    )

    short = models.CharField(
        max_length=10,
    )

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="grades",
    )

    level = models.ForeignKey(
        SchoolLevel,
        on_delete=models.PROTECT,
        related_name="grades",
    )

    duration = models.PositiveIntegerField(
        default=12,
        help_text=_("Duration in months"),
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
            "Grades cannot be deleted."
        )