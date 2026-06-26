from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import TimestampModel
from .programs import Program
from .subject import Subject

class Sem(TimestampModel):
    """
    A semester/academic period belonging to a university-level program.

    Subject structure mirrors ClassSubjectConfig:
      - compulsory_subjects   : every student must take these
      - optional groups       : see OptionalSubjectGroup (reverse FK via sem=)
      - total_compulsory_subjects / total_optional_groups : capacity caps

    A student's valid selection = all compulsory_subjects
                                + exactly one subject per OptionalSubjectGroup
    """

    name = models.CharField(max_length=100)

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="semesters",
    )

    duration = models.PositiveIntegerField(
        default=6,
        help_text=_("Duration in months"),
    )

    order = models.PositiveIntegerField()

    # ── subject capacity ──────────────────────────────────────────────────────

    total_compulsory_subjects = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "Maximum compulsory subjects allowed. "
            "compulsory_subjects.count() must not exceed this. 0 = no limit defined."
        ),
    )

    total_optional_groups = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "Maximum optional groups allowed. "
            "OptionalSubjectGroup count must not exceed this. 0 = no limit defined."
        ),
    )

    compulsory_subjects = models.ManyToManyField(
        Subject,
        blank=True,
        related_name="compulsory_sems",
        help_text=_("Subjects every student in this semester must take."),
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["program", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "name"],
                name="unique_sem_name_per_program",
            ),
            models.UniqueConstraint(
                fields=["program", "order"],
                name="unique_sem_order_per_program",
            ),
        ]

    def __str__(self):
        return f"{self.program.short} - {self.name}"

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

        # compulsory capacity
        if self.total_compulsory_subjects > 0:
            count = self.compulsory_subjects.count()
            if count > self.total_compulsory_subjects:
                raise ValidationError({
                    "compulsory_subjects": _(
                        f"This semester allows at most {self.total_compulsory_subjects} "
                        f"compulsory subject(s), but {count} are assigned."
                    )
                })

        # optional group capacity
        if self.total_optional_groups > 0:
            count = self.optional_groups.count()
            if count > self.total_optional_groups:
                raise ValidationError({
                    "total_optional_groups": _(
                        f"This semester allows at most {self.total_optional_groups} "
                        f"optional group(s), but {count} exist."
                    )
                })

        # compulsory must not overlap with any optional group's subjects
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

        # all subjects must belong to the same org as the program
        sem_org_id = self.program.org_id
        all_subject_ids = compulsory_ids | optional_subject_ids
        wrong = Subject.objects.filter(id__in=all_subject_ids).exclude(org_id=sem_org_id)
        if wrong.exists():
            names = list(wrong.values_list("name", flat=True))
            raise ValidationError(_(
                f"Subject(s) {names} do not belong to the same organization as this semester."
            ))

