from django.db import models
from organization.models import Organization
from core.models import TimestampModel
from .levels import SchoolLevel


class Stream(TimestampModel):
    name = models.CharField(
        max_length=100,
    )

    short = models.CharField(
        max_length=20,
    )

    level = models.ForeignKey(
        SchoolLevel,
        on_delete=models.PROTECT,
        related_name="streams",
    )


    is_active = models.BooleanField(
        default=True,
    )


    def __str__(self):
        return self.name