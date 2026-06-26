from rest_framework import serializers
from Academics.models import Program
from Academics.models import UniversityLevel


class ProgramSerializer(serializers.ModelSerializer):
    level_name = serializers.SerializerMethodField()
    level_id   = serializers.IntegerField(source="level.id")

    def get_level_name(self, obj):
        return obj.level.get_name_display() if obj.level else None

    class Meta:
        model = Program
        fields = [
            "id",
            "name",
            "short",
            "org",
            "level_id",
            "level_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "org"]

    def validate_short(self, value):
        return value.strip().upper()

    def validate_name(self, value):
        return value.strip()

    def validate(self, attrs):
        # level_id arrives as {"level": {"id": <n>}} due to source="level.id"
        level_data = attrs.pop("level", None)
        level_id   = level_data.get("id") if isinstance(level_data, dict) else None

        if level_id is not None:
            try:
                attrs["level"] = UniversityLevel.objects.get(id=level_id)
            except UniversityLevel.DoesNotExist:
                raise serializers.ValidationError({"level_id": "Level not found."})

        level = attrs.get("level") or getattr(self.instance, "level", None)
        org   = attrs.get("org")   or getattr(self.instance, "org",   None)

        if level and org and level.org_id != org.id:
            raise serializers.ValidationError(
                {"level": "Selected level does not belong to the same organization."}
            )

        return attrs