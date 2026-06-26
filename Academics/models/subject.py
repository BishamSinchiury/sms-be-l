from django.db import models
from django.utils.translation import gettext_lazy as _

from organization.models import Organization
from core.models import TimestampModel


class Subject(TimestampModel):
    """
    Canonical subject definition for an org.
    Code is unique per org (e.g. two orgs can both have "ENG-101").
    """

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="subjects",
    )

    name = models.CharField(max_length=200)

    code = models.CharField(
        max_length=20,
        help_text=_("Short identifier, unique within the org (e.g. ENG-101)."),
    )

    book_publication = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Publisher or book title. Optional."),
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["org", "code"],
                name="unique_subject_code_per_org",
            ),
            models.UniqueConstraint(
                fields=["org", "name"],
                name="unique_subject_name_per_org",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"
