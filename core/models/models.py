# core/models.py
from django.db import models
import uuid


class TimestampModel(models.Model):
    """
    Abstract base model that adds created_at and updated_at
    to any model that inherits it.
    
    auto_now_add → set once when object is created, never changes
    auto_now     → updated every time the object is saved
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True



class PersonalDetail(models.Model):
    """
    Stores personal information for any person in the system.
    Linked via OneToOne from User, Vendor, etc.
    Inherits TimestampModel for created_at and updated_at.
    """

    class Gender(models.TextChoices):
        MALE        = 'M', 'Male'
        FEMALE      = 'F', 'Female'
        OTHER       = 'O', 'Other'

    uuid          = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    first_name    = models.CharField(max_length=100)
    last_name     = models.CharField(max_length=100)
    gender        = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    tax_id        = models.CharField(max_length=50, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    

class ContactDetail(models.Model):
    """
    Stores contact information.
    Linked via OneToOne from User, Organization, SubOrg etc.
    """
    uuid          = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    phone_number  = models.CharField(max_length=20)
    phone_number2 = models.CharField(max_length=20, blank=True)
    email         = models.EmailField(blank=True)

    def __str__(self):
        return self.phone_number
    
class AddressDetail(models.Model):
    """
    Stores address information.
    Linked via OneToOne from User, Organization, SubOrg, Vendor etc.
    
    latitude and longitude are optional — only needed when
    physical location mapping is required (e.g. org branch on a map)
    """
    country   = models.CharField(max_length=100)
    province  = models.CharField(max_length=100)
    district  = models.CharField(max_length=100)
    city      = models.CharField(max_length=100)
    latitude  = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.city}, {self.district}, {self.province}"

class DocumentDetail(models.Model):
    """
    Stores registration document information.
    Linked via OneToOne from User, Organization, Vendor etc.
    
    We store registration numbers as CharFields — not the actual
    documents. Actual document files would be a separate model
    with a ForeignKey to whoever owns them.
    """
    uuid                          = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    id_registration               = models.CharField(max_length=100, blank=True)
    tax_registration              = models.CharField(max_length=100, blank=True)
    birth_certificate_registration = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.id_registration or self.tax_registration or "No registration"