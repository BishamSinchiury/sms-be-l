from rest_framework import serializers
from Academics.models import Stream
from Academics.models.levels import SchoolLevel


class StreamSerializer(serializers.ModelSerializer):
    level_name = serializers.SerializerMethodField()
    level_id = serializers.IntegerField(source="level.id")

    def get_level_name(self, obj):
        return obj.level.get_name_display() if obj.level else None

    class Meta:
        model = Stream
        fields = [
            "id",
            "name",
            "short",
            "level_id",
            "level_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        return value.strip()

    def validate_short(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        level_data = attrs.pop("level", None)
        level_id = level_data.get("id") if isinstance(level_data, dict) else None

        if level_id is not None:
            try:
                attrs["level"] = SchoolLevel.objects.get(id=level_id)
            except SchoolLevel.DoesNotExist:
                raise serializers.ValidationError(
                    {"level_id": "Level not found."}
                )

        if not self.instance and attrs.get("level") is None:
            raise serializers.ValidationError(
                {"level_id": "This field is required."}
            )

        name = attrs.get("name", getattr(self.instance, "name", None))
        level = attrs.get("level", getattr(self.instance, "level", None))

        if name and level:
            qs = Stream.objects.filter(
                name__iexact=name,
                level=level,
            )

            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "name": (
                            f'A stream named "{name}" already exists '
                            f'for this level.'
                        )
                    }
                )

        return attrs