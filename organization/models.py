from django.db import models
from django.core.exceptions import ValidationError
from users.models import CustomUser


class Organization(models.Model):
    name = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(upload_to="organizations/logos/")
    address = models.CharField(max_length=255)
    motto = models.CharField(max_length=255)

    primary_color = models.CharField(max_length=7)
    secondary_color = models.CharField(max_length=7)

    cover_picture = models.ImageField(upload_to="organizations/covers/")
    domain_name = models.URLField(max_length=200)
    admin = models.ManyToManyField(CustomUser, related_name="organizations")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.clean()

    def __str__(self):
        return self.name