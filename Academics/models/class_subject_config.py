from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import TimestampModel
from .programs import Program
from .grades import Grade
from .stream import Stream
from .subject import Subject
from .sem import Sem



# ─────────────────────────────────────────────────────────────────────────────
# ClassSubjectConfig
# ─────────────────────────────────────────────────────────────────────────────

class ClassSubjectConfig(TimestampModel):
    """
    Subject blueprint for a school grade, optionally scoped to specific streams.

    A student's valid selection = all compulsory_subjects
                                + exactly one subject per OptionalSubjectGroup
    """

    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="subject_configs",
    )

    streams = models.ManyToManyField(
        Stream,
        blank=True,
        related_name="subject_configs",
        help_text=_("Which streams this config applies to. Leave blank if the grade has no streams."),
    )

    compulsory_subjects = models.ManyToManyField(
        Subject,
        blank=True,
        related_name="compulsory_configs",
        help_text=_("Subjects every student in this config must take."),
    )

    total_compulsory_subjects = models.PositiveIntegerField(
        default=0,
        help_text=_("Maximum compulsory subjects allowed. 0 = no limit defined."),
    )

    total_optional_groups = models.PositiveIntegerField(
        default=0,
        help_text=_("Maximum optional groups allowed. 0 = no limit defined."),
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["grade__order"]

    def __str__(self):
        stream_names = ", ".join(self.streams.values_list("name", flat=True)) or "all streams"
        return f"{self.grade} — {stream_names}"

    @property
    def compulsory_count(self):
        return self.compulsory_subjects.count() if self.pk else 0

    @property
    def optional_group_count(self):
        return self.optional_groups.count() if self.pk else 0

    def clean(self):
        super().clean()
        if not self.pk:
            return

        if self.total_compulsory_subjects > 0:
            count = self.compulsory_subjects.count()
            if count > self.total_compulsory_subjects:
                raise ValidationError({
                    "compulsory_subjects": _(
                        f"This config allows at most {self.total_compulsory_subjects} "
                        f"compulsory subject(s), but {count} are assigned."
                    )
                })

        if self.total_optional_groups > 0:
            count = self.optional_groups.count()
            if count > self.total_optional_groups:
                raise ValidationError({
                    "total_optional_groups": _(
                        f"This config allows at most {self.total_optional_groups} "
                        f"optional group(s), but {count} exist."
                    )
                })

        optional_subject_ids = set(
            self.optional_groups.values_list("subjects__id", flat=True)
        )
        compulsory_ids = set(self.compulsory_subjects.values_list("id", flat=True))
        overlap = compulsory_ids & optional_subject_ids
        if overlap:
            names = list(Subject.objects.filter(id__in=overlap).values_list("name", flat=True))
            raise ValidationError({
                "compulsory_subjects": _(
                    f"Subject(s) {names} appear in both compulsory and optional groups."
                )
            })


# ─────────────────────────────────────────────────────────────────────────────
# OptionalSubjectGroup  —  shared by both Sem and ClassSubjectConfig
# ─────────────────────────────────────────────────────────────────────────────

class OptionalSubjectGroup(TimestampModel):
    """
    A mutually exclusive group of elective subjects.
    Belongs to EITHER a Sem OR a ClassSubjectConfig — never both, never neither.

    A student picks exactly one subject from this group.

    Example:
      Group "Mathematics Group" → [Mathematics, Social Studies]
      Group "CS Group"          → [Computer Science, Travel & Tourism]
    """

    # exactly one of these two FKs must be set
    sem = models.ForeignKey(
        Sem,
        on_delete=models.CASCADE,
        related_name="optional_groups",
        null=True,
        blank=True,
    )

    config = models.ForeignKey(
        ClassSubjectConfig,
        on_delete=models.CASCADE,
        related_name="optional_groups",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100,
        help_text=_("Human label, e.g. 'Mathematics Group', 'Group A'."),
    )

    subjects = models.ManyToManyField(
        Subject,
        related_name="optional_groups",
        help_text=_("Subjects in this group. Student picks exactly one."),
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            # name unique within a sem
            models.UniqueConstraint(
                fields=["sem", "name"],
                condition=models.Q(sem__isnull=False),
                name="unique_optional_group_name_per_sem",
            ),
            # name unique within a config
            models.UniqueConstraint(
                fields=["config", "name"],
                condition=models.Q(config__isnull=False),
                name="unique_optional_group_name_per_config",
            ),
        ]

    def __str__(self):
        parent = self.sem or self.config
        return f"{parent} / {self.name}"

    @property
    def parent(self):
        """Returns the owning Sem or ClassSubjectConfig instance."""
        return self.sem or self.config

    @property
    def org_id(self):
        if self.sem_id:
            return self.sem.program.org_id
        if self.config_id:
            return self.config.grade.org_id
        return None

    def clean(self):
        super().clean()

        # exactly one parent must be set
        has_sem    = bool(self.sem_id or self.sem)
        has_config = bool(self.config_id or self.config)

        if has_sem and has_config:
            raise ValidationError(
                _("An optional group can belong to a semester OR a class config, not both.")
            )
        if not has_sem and not has_config:
            raise ValidationError(
                _("An optional group must belong to either a semester or a class config.")
            )

        if not self.pk:
            return

        # at least 2 subjects
        if self.subjects.count() < 2:
            raise ValidationError(
                {"subjects": _("An optional group must contain at least 2 subjects.")}
            )

        # subjects must not be compulsory in the parent
        if has_sem and self.sem_id:
            compulsory_ids = set(self.sem.compulsory_subjects.values_list("id", flat=True))
        elif has_config and self.config_id:
            compulsory_ids = set(self.config.compulsory_subjects.values_list("id", flat=True))
        else:
            compulsory_ids = set()

        group_ids = set(self.subjects.values_list("id", flat=True))
        overlap   = compulsory_ids & group_ids
        if overlap:
            names = list(Subject.objects.filter(id__in=overlap).values_list("name", flat=True))
            raise ValidationError({
                "subjects": _(f"Subject(s) {names} are already compulsory in the parent.")
            })