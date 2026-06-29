from rest_framework import serializers

from core.models import PersonalDetail, ContactDetail, AddressDetail
from organization.models import Organization
from users.models import CustomUser

from .models import (
    Enrollment,
    EnrollmentSubjectSelection,
    GuardianProfile,
    Student,
    StudentProfile,
)


# ── Nested detail serializers ─────────────────────────────────────────────────

class PersonalDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PersonalDetail
        fields = ["first_name", "last_name", "gender", "date_of_birth", "tax_id", "profile_photo"]


class ContactDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ContactDetail
        fields = ["phone_number", "phone_number2", "email"]


class AddressDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AddressDetail
        fields = ["country", "province", "district", "city", "latitude", "longitude"]


# ── Student create ────────────────────────────────────────────────────────────

class StudentCreateSerializer(serializers.Serializer):
    """
    Doesn't map 1:1 to a single model — plain Serializer not ModelSerializer.
    Field names match Student.objects.create_student() kwargs exactly so
    validated_data can be passed straight through with **.
    """

    org = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())

    student_email    = serializers.EmailField()
    student_personal = PersonalDetailSerializer()
    student_contact  = ContactDetailSerializer(required=False, allow_null=True)
    student_address  = AddressDetailSerializer(required=False, allow_null=True)

    guardian_email    = serializers.EmailField()
    guardian_personal = PersonalDetailSerializer()
    guardian_relation = serializers.ChoiceField(choices=GuardianProfile.Relation.choices)
    guardian_contact  = ContactDetailSerializer(required=False, allow_null=True)
    guardian_address  = AddressDetailSerializer(required=False, allow_null=True)

    admission_number = serializers.CharField(max_length=30)

    def validate_student_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_guardian_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_admission_number(self, value):
        if StudentProfile.objects.filter(admission_number=value).exists():
            raise serializers.ValidationError("This admission number is already in use.")
        return value

    def validate(self, attrs):
        if attrs.get("student_email") and attrs.get("guardian_email"):
            if attrs["student_email"] == attrs["guardian_email"]:
                raise serializers.ValidationError(
                    {"guardian_email": "Guardian email must differ from student email."}
                )
        return attrs

    def create(self, validated_data):
        # Null-out optional nested dicts that came in as None
        for key in ("student_contact", "student_address", "guardian_contact", "guardian_address"):
            if validated_data.get(key) is None:
                validated_data.pop(key, None)
        return Student.objects.create_student(**validated_data)


# ── Student read ──────────────────────────────────────────────────────────────

class StudentReadSerializer(serializers.ModelSerializer):
    email            = serializers.EmailField(source="user.email", read_only=True)
    guardian_email   = serializers.EmailField(source="guardian.email", read_only=True)
    admission_number = serializers.SerializerMethodField()
    first_name       = serializers.SerializerMethodField()
    last_name        = serializers.SerializerMethodField()

    class Meta:
        model  = Student
        fields = [
            "id", "uuid", "org",
            "email", "first_name", "last_name",
            "guardian_email",
            "admission_number",
            "status", "is_active",
            "created_at",
        ]

    def get_admission_number(self, obj):
        try:
            return obj.user.profile.student_profile.admission_number
        except Exception:
            return None

    def get_first_name(self, obj):
        try:
            return obj.user.profile.personal.first_name
        except Exception:
            return None

    def get_last_name(self, obj):
        try:
            return obj.user.profile.personal.last_name
        except Exception:
            return None


# ── Enrollment ────────────────────────────────────────────────────────────────

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Enrollment
        fields = [
            "id", "student",
            "program", "sem",
            "grade", "class_config", "stream",
            "status", "enrolled_on",
        ]

    def validate(self, attrs):
        # ModelSerializer doesn't call Model.clean() — do it explicitly
        existing = self.instance.__dict__ if self.instance else {}
        instance = Enrollment(**{**existing, **attrs})
        instance.clean()
        return attrs


# ── EnrollmentSubjectSelection ────────────────────────────────────────────────

class EnrollmentSubjectSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EnrollmentSubjectSelection
        fields = ["id", "enrollment", "optional_group", "subject"]

    def validate(self, attrs):
        existing = self.instance.__dict__ if self.instance else {}
        instance = EnrollmentSubjectSelection(**{**existing, **attrs})
        instance.clean()
        return attrs
