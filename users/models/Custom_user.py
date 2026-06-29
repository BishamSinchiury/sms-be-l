import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import PersonalDetail, ContactDetail, AddressDetail, DocumentDetail
from organization.models import Organization


class CustomUserManager(BaseUserManager):
    """Email is the unique identifier instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Users must have an email address."))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_sysadmin", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_sysadmin", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("status", "approved")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_sysadmin") is not True:
            raise ValueError(_("Superuser must have is_sysadmin=True."))

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Status(models.TextChoices):
        PENDING   = "pending",   _("Pending")
        APPROVED  = "approved",  _("Approved")
        UNCLAIMED = "unclaimed", _("Unclaimed")

    class RoleChoices(models.TextChoices):
        STUDENT  = "student",  _("Student")
        TEACHER  = "teacher",  _("Teacher")
        STAFF    = "staff",    _("Staff")
        OWNER    = "owner",    _("Owner")
        GUARDIAN = "guardian", _("Guardian")
        VENDOR   = "vendor",   _("Vendor")

    email      = models.EmailField(unique=True)
    username   = models.CharField(max_length=50, blank=True)

    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        blank=True,
        help_text=_(
            "Top-level role. Granular positions for Staff users are "
            "assigned separately via UserRole -> Role."
        ),
    )

    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_sysadmin = models.BooleanField(default=False)
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.UNCLAIMED)
    uuid        = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    org         = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        null=True, blank=True, related_name="users",
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    user     = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    personal = models.OneToOneField(PersonalDetail, on_delete=models.SET_NULL, null=True, blank=True)
    contact  = models.OneToOneField(ContactDetail,  on_delete=models.SET_NULL, null=True, blank=True)
    address  = models.OneToOneField(AddressDetail,  on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.email