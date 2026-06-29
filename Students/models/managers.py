import logging

from django.db import models, transaction

from core.models import AddressDetail, ContactDetail, PersonalDetail
from users.models import CustomUser, UserProfile

from .utils import generate_random_password, send_credentials_email

logger = logging.getLogger(__name__)


class StudentManager(models.Manager):
    """
    Student.objects.create_student(...) is the ONLY supported way to create a
    Student. Plain Student.objects.create() will fail because `user` and
    `guardian` are required FKs to CustomUsers that don't exist yet — this
    method provisions both accounts (with random passwords + credential
    emails) and the Student row in a single transaction.
    """

    @transaction.atomic
    def create_student(
        self,
        *,
        org,
        student_email,
        student_personal,
        guardian_email,
        guardian_personal,
        guardian_relation,
        admission_number,
        student_contact=None,
        student_address=None,
        guardian_contact=None,
        guardian_address=None,
        **student_extra_fields,
    ):
        # local import avoids circular import with Students/models.py
        from .models import GuardianProfile, StudentProfile

        student_password  = generate_random_password()
        guardian_password = generate_random_password()

        student_user = CustomUser.objects.create_user(
            email=student_email,
            password=student_password,
            role=CustomUser.RoleChoices.STUDENT,
            org=org,
        )
        guardian_user = CustomUser.objects.create_user(
            email=guardian_email,
            password=guardian_password,
            role=CustomUser.RoleChoices.GUARDIAN,
            org=org,
        )

        student_personal_detail  = PersonalDetail.objects.create(**student_personal)
        guardian_personal_detail = PersonalDetail.objects.create(**guardian_personal)

        student_contact_detail  = ContactDetail.objects.create(**student_contact)  if student_contact  else None
        guardian_contact_detail = ContactDetail.objects.create(**guardian_contact) if guardian_contact else None

        student_address_detail  = AddressDetail.objects.create(**student_address)  if student_address  else None
        guardian_address_detail = AddressDetail.objects.create(**guardian_address) if guardian_address else None

        student_profile = UserProfile.objects.create(
            user=student_user,
            personal=student_personal_detail,
            contact=student_contact_detail,
            address=student_address_detail,
        )
        guardian_profile = UserProfile.objects.create(
            user=guardian_user,
            personal=guardian_personal_detail,
            contact=guardian_contact_detail,
            address=guardian_address_detail,
        )

        StudentProfile.objects.create(
            user_profile=student_profile,
            admission_number=admission_number,
        )
        GuardianProfile.objects.create(
            user_profile=guardian_profile,
            relation_to_student=guardian_relation,
        )

        student = self.create(
            org=org,
            user=student_user,
            guardian=guardian_user,
            **student_extra_fields,
        )

        for user, password, label in (
            (student_user,  student_password,  "Student"),
            (guardian_user, guardian_password, "Guardian"),
        ):
            try:
                send_credentials_email(user, password, label)
            except Exception:
                logger.exception("Failed to send credentials email to %s", user.email)

        return student
