from rest_framework import serializers
from Academics.models import AcademicYear


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = [
            "uuid",
            "name",
            "org",
            "start_date",
            "end_date",
            "is_active",
        ]
        read_only_fields = ["uuid", "org"]


    def _deactivate_others(self, instance):
        if instance.is_active:
            AcademicYear.objects.filter(
                org=instance.org,
                is_active=True,
            ).exclude(
                pk=instance.pk
            ).update(
                is_active=False
            )
    
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._deactivate_others(instance)
        return instance

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._deactivate_others(instance)
        return instance

    

    def validate(self, data):
        start_date = data.get(
            "start_date",
            getattr(self.instance, "start_date", None)
        )
        end_date = data.get(
            "end_date",
            getattr(self.instance, "end_date", None)
        )

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError(
                    "Start date cannot be after end date."
                )

            if (end_date - start_date).days < 365:
                raise serializers.ValidationError(
                    "Academic year must be at least 1 year long."
                )

        return data