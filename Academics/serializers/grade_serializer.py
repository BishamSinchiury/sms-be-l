from rest_framework import serializers
from Academics.models import Grade


class GradeSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source="get_name_display", read_only=True)
    level_name = serializers.CharField(source="level.get_name_display", read_only=True)

    class Meta:
        model = Grade
        fields = [
            "id",
            "name",
            "name_display",
            "short",
            "org",
            "level",
            "level_name",
            "duration",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_short(self, value):
        return value.strip().upper()

    def validate_duration(self, value):
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 month.")
        return value

    def validate_order(self, value):
        if value < 1:
            raise serializers.ValidationError("Order must be a positive integer.")
        return value

    def validate(self, attrs):
        level = attrs.get("level") or getattr(self.instance, "level", None)
        org = attrs.get("org") or getattr(self.instance, "org", None)
        name = attrs.get("name") or getattr(self.instance, "name", None)
        order = attrs.get("order") or getattr(self.instance, "order", None)

        if level is not None and org is not None and level.org_id != org.id:
            raise serializers.ValidationError(
                {"level": "Selected level does not belong to the same organization as this grade."}
            )

        if org is not None and name is not None:
            qs = Grade.objects.filter(org=org, name=name)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "A grade with this name already exists for this organization."}
                )

        if org is not None and order is not None:
            qs = Grade.objects.filter(org=org, order=order)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"order": "A grade with this order already exists for this organization."}
                )

        return attrs