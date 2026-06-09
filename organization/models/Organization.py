from django.db import models
from django.core.exceptions import ValidationError

class Organization(models.Model):
    name = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(upload_to="organizations/logos/")
    address = models.CharField(max_length=255)
    motto = models.CharField(max_length=255)

    primary_color = models.CharField(max_length=7)
    secondary_color = models.CharField(max_length=7)

    cover_picture = models.ImageField(upload_to="organizations/covers/")
    domain_name = models.CharField(max_length=253, unique=True)

    def __str__(self):
        return self.name