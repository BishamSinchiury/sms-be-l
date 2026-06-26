from rest_framework import serializers
from Academics.models import Subject


class SubjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subject
        fields = [
            "id",
            "name",
            "code",
            "book_publication",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        return value.strip()

    def validate_code(self, value):
        return value.strip().upper()

    def validate_book_publication(self, value):
        return value.strip() if value else value

    def validate(self, attrs):
        org  = getattr(self.instance, "org", None) or attrs.get("org")
        name = attrs.get("name") or getattr(self.instance, "name", None)
        code = attrs.get("code") or getattr(self.instance, "code", None)

        if org and name:
            qs = Subject.objects.filter(org=org, name=name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "A subject with this name already exists for this organization."}
                )

        if org and code:
            qs = Subject.objects.filter(org=org, code=code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"code": "A subject with this code already exists for this organization."}
                )

        return attrs
