import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimestampModel
from organization.models import Organization
from users.models import CustomUser

from .managers import StudentManager

class Student(TimestampModel):
    """
    Create exclusively via Student.objects.create_student(...) — see
    students/managers.py. That method provisions the student's and
    guardian's CustomUser accounts (random password + credentials email
    each) atomically alongside this row.
    """

    class StudentStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        GRADUATED = "graduated", _("Graduated")
        WITHDRAWN = "withdrawn", _("Withdrawn")
        TRANSFERRED = "transferred", _("Transferred")

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="students",
    )

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="student",
        limit_choices_to={"role": CustomUser.RoleChoices.STUDENT},
    )

    guardian = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="students",
        limit_choices_to={"role": CustomUser.RoleChoices.GUARDIAN},
        help_text=_(
            "Primary guardian. FK rather than 1-1 so siblings could share a "
            "guardian account in future without a schema change."
        ),
    )

    status = models.CharField(
        max_length=15,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
    )

    is_active = models.BooleanField(default=True)

    objects = StudentManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.user.email

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != CustomUser.RoleChoices.STUDENT:
            raise ValidationError({"user": _("Linked user must have role=Student.")})
        if self.guardian_id and self.guardian.role != CustomUser.RoleChoices.GUARDIAN:
            raise ValidationError({"guardian": _("Linked guardian must have role=Guardian.")})
        if self.user_id and self.guardian_id and self.user.org_id != self.guardian.org_id:
            raise ValidationError(_("Student and guardian must belong to the same organization."))
