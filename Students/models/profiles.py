from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import UserProfile

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
