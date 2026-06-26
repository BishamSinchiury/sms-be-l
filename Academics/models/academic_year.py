from django.db import models
import uuid
from organization.models import Organization
from core.models import TimestampModel
from django.db.models import UniqueConstraint, Q

class AcademicYear(TimestampModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, unique=True)

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
    )

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name