from django.db import models
from django.core.exceptions import ValidationError
from core.models import ContactDetail, AddressDetail, DocumentDetail
import uuid as uuid_lib

class Organization(models.Model):
    name = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(upload_to="organizations/logos/")
    address = models.CharField(max_length=255)
    motto = models.CharField(max_length=255)

    primary_color = models.CharField(max_length=7)
    secondary_color = models.CharField(max_length=7)

    cover_picture = models.ImageField(upload_to="organizations/covers/")
    domain_name = models.CharField(max_length=253, unique=True)

    contact  = models.OneToOneField(
        ContactDetail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organization'
    )
    address_detail = models.OneToOneField(
        AddressDetail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organization'
    )
    document = models.OneToOneField(
        DocumentDetail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organization'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class SubOrganization(models.Model):
    uuid        = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)  
    name        = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    org         = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='suborgs'
    )
    contact = models.OneToOneField(
        ContactDetail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suborg'
    )
    address_detail = models.OneToOneField(
        AddressDetail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suborg'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'org')

    def __str__(self):
        return f"{self.org.name} — {self.name}"