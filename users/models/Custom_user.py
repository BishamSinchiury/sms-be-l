import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from organization.models import Organization
from core.models import PersonalDetail, ContactDetail, AddressDetail, DocumentDetail

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        UNCLAIMED = "unclaimed", "Unclaimed"
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_sysadmin = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNCLAIMED)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    personal = models.OneToOneField(PersonalDetail, on_delete=models.SET_NULL, null=True, blank=True)
    contact = models.OneToOneField(ContactDetail, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.OneToOneField(AddressDetail, on_delete=models.SET_NULL, null=True, blank=True)