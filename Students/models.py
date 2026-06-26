
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimestampModel
from organization.models import Organization
from users.models import CustomUser, UserProfile

from Academics.models import ( 
    ClassSubjectConfig,
    Grade,
    OptionalSubjectGroup,
    Program,
    Sem,
    Stream,
    Subject,
)

from .managers import StudentManager


# ─────────────────────────────────────────────────────────────────────────────
# Profiles
# ─────────────────────────────────────────────────────────────────────────────

class StudentProfile(models.Model):
    """Student-specific extension of UserProfile."""

    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    admission_number = models.CharField(max_length=30, unique=True)
    roll_number = models.CharField(max_length=20, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    previous_school = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.user_profile.user.email} ({self.admission_number})"


class GuardianProfile(models.Model):
    """Guardian-specific extension of UserProfile."""

    class Relation(models.TextChoices):
        FATHER = "father", _("Father")
        MOTHER = "mother", _("Mother")
        GUARDIAN = "guardian", _("Guardian")
        OTHER = "other", _("Other")

    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="guardian_profile",
    )
    relation_to_student = models.CharField(max_length=10, choices=Relation.choices)
    occupation = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user_profile.user.email} ({self.get_relation_to_student_display()})"


# ─────────────────────────────────────────────────────────────────────────────
# Student
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Enrollment
# ─────────────────────────────────────────────────────────────────────────────

class Enrollment(TimestampModel):
    """
    Ties a Student to an academic period — either:
      - university path: program + sem
      - school path:      grade + class_config (+ optional stream)
    Exactly one path must be set, never both, never neither (same XOR shape
    as OptionalSubjectGroup.sem / .config).
    """

    class EnrollmentStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        COMPLETED = "completed", _("Completed")
        WITHDRAWN = "withdrawn", _("Withdrawn")

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    # university path
    program = models.ForeignKey(
        Program, on_delete=models.PROTECT, null=True, blank=True, related_name="enrollments",
    )
    sem = models.ForeignKey(
        Sem, on_delete=models.PROTECT, null=True, blank=True, related_name="enrollments",
    )

    # school path
    grade = models.ForeignKey(
        Grade, on_delete=models.PROTECT, null=True, blank=True, related_name="enrollments",
    )
    class_config = models.ForeignKey(
        ClassSubjectConfig, on_delete=models.PROTECT, null=True, blank=True, related_name="enrollments",
    )
    stream = models.ForeignKey(
        Stream, on_delete=models.PROTECT, null=True, blank=True, related_name="enrollments",
    )

    status = models.CharField(
        max_length=15, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE,
    )
    enrolled_on = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-enrolled_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "sem"],
                condition=models.Q(sem__isnull=False),
                name="unique_enrollment_per_student_sem",
            ),
            models.UniqueConstraint(
                fields=["student", "grade", "class_config"],
                condition=models.Q(grade__isnull=False, class_config__isnull=False),
                name="unique_enrollment_per_student_grade_config",
            ),
        ]

    def __str__(self):
        return f"{self.student} -> {self.parent}"

    @property
    def parent(self):
        """Returns the Sem or ClassSubjectConfig this enrollment is scoped to."""
        return self.sem or self.class_config

    def clean(self):
        super().clean()

        has_university = bool(self.program_id or self.sem_id)
        has_school = bool(self.grade_id or self.class_config_id)

        if has_university and has_school:
            raise ValidationError(
                _("An enrollment is either university-path (program+sem) or "
                  "school-path (grade+class_config), not both.")
            )
        if not has_university and not has_school:
            raise ValidationError(
                _("An enrollment must specify either program+sem or grade+class_config.")
            )

        if has_university:
            if not (self.program_id and self.sem_id):
                raise ValidationError(_("Both program and sem are required for a university-path enrollment."))
            if self.sem.program_id != self.program_id:
                raise ValidationError({"sem": _("Selected sem does not belong to the selected program.")})

        if has_school:
            if not (self.grade_id and self.class_config_id):
                raise ValidationError(_("Both grade and class_config are required for a school-path enrollment."))
            if self.class_config.grade_id != self.grade_id:
                raise ValidationError({"class_config": _("Selected config does not belong to the selected grade.")})
            if self.stream_id and self.class_config.streams.exists():
                if not self.class_config.streams.filter(pk=self.stream_id).exists():
                    raise ValidationError({"stream": _("Selected stream is not part of this class config.")})

        if self.student_id:
            student_org_id = self.student.org_id
            if has_university and self.program_id and self.program.org_id != student_org_id:
                raise ValidationError(_("Program does not belong to the student's organization."))
            if has_school and self.grade_id and self.grade.org_id != student_org_id:
                raise ValidationError(_("Grade does not belong to the student's organization."))


class EnrollmentSubjectSelection(TimestampModel):
    """
    Which subject the student picked for a given OptionalSubjectGroup, within
    one Enrollment. One selection per group per enrollment.
    """

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="subject_selections",
    )
    optional_group = models.ForeignKey(
        OptionalSubjectGroup,
        on_delete=models.PROTECT,
        related_name="subject_selections",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="subject_selections",
    )

    class Meta:
        ordering = ["optional_group__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "optional_group"],
                name="unique_selection_per_group_per_enrollment",
            ),
        ]

    def __str__(self):
        return f"{self.enrollment} / {self.optional_group.name} -> {self.subject}"

    def clean(self):
        super().clean()
        if not (self.enrollment_id and self.optional_group_id):
            return

        if self.optional_group.parent != self.enrollment.parent:
            raise ValidationError({
                "optional_group": _(
                    "This optional group does not belong to the enrollment's sem/class_config."
                )
            })

        if self.subject_id and not self.optional_group.subjects.filter(pk=self.subject_id).exists():
            raise ValidationError({"subject": _("Selected subject is not part of this optional group.")})