from rest_framework import serializers
from Academics.models import UniversityLevel, SchoolLevel


class _BaseLevelSerializer(serializers.ModelSerializer):
    """
    Shared behaviour for UniversityLevel / SchoolLevel.

    These are seed-data models: rows are created once (via management
    command) and can never be deleted (`Model.delete()` raises
    NotImplementedError). From the API, only `order` and `is_active`
    are mutable — `name` and `org` are fixed at creation time.
    """

    name_display = serializers.SerializerMethodField()

    def get_name_display(self, obj):
        return obj.get_name_display()

    def get_fields(self):
        fields = super().get_fields()
        for locked_field in ("name", "org"):
            if locked_field in fields:
                fields[locked_field].read_only = True
        return fields

    def validate_order(self, value):
        if value < 1:
            raise serializers.ValidationError("Order must be a positive integer.")
        return value

    def validate(self, attrs):
        order = attrs.get("order")
        if order is not None:
            org = getattr(self.instance, "org", None) or attrs.get("org")
            qs = self.Meta.model.objects.filter(org=org, order=order)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"order": "A level with this order already exists for this organization."}
                )
        return attrs


class UniversityLevelSerializer(_BaseLevelSerializer):
    class Meta:
        model = UniversityLevel
        fields = [
            "id",
            "name",
            "name_display",
            "org",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "name", "org", "created_at", "updated_at"]


class SchoolLevelSerializer(_BaseLevelSerializer):
    class Meta:
        model = SchoolLevel
        fields = [
            "id",
            "name",
            "name_display",
            "org",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "name", "org", "created_at", "updated_at"]