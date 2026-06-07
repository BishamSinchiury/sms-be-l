from rest_framework import serializers
from organization.models import Organization

class OrganizationPublicSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    cover_picture = serializers.SerializerMethodField()
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

    def get_logo(self, obj):
        request = self.context.get("request")
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None

    def get_cover_picture(self, obj):
        request = self.context.get("request")
        if obj.cover_picture and request:
            return request.build_absolute_uri(obj.cover_picture.url)
        return None