from rest_framework import serializers
from organization.models import Organization

class OrganizationPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "logo",
            "address",
            "motto",
            "primary_color",
            "secondary_color",
            "cover_picture",
        )
        read_only_fields = fields