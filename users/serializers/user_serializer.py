from rest_framework import serializers
from users.models import CustomUser
from users.models import CustomUser
from core.models import PersonalDetail
from django.contrib.auth.password_validation import validate_password
from rbac.models import Role, UserRole

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('uuid', 'email', 'username', 'is_verified', 'status', 'is_staff', 'is_sysadmin')
        read_only_fields = fields


class RoleMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['uuid', 'name']


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the Users Management table."""
    role      = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = CustomUser
        fields = [
            'uuid', 'email', 'username', 'full_name',
            'is_active', 'is_verified', 'status', 'is_staff', 'is_sysadmin',
            'role', 'created_at',
        ]

    def get_role(self, obj):
        user_role = getattr(obj, 'user_role', None)
        return user_role.role.name if user_role else None

    def get_full_name(self, obj):
        if obj.personal and (obj.personal.first_name or obj.personal.last_name):
            return f"{obj.personal.first_name} {obj.personal.last_name}".strip()
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    """Full detail view — used for the user detail panel."""
    role          = serializers.SerializerMethodField()
    role_uuid     = serializers.SerializerMethodField()
    first_name    = serializers.SerializerMethodField()
    last_name     = serializers.SerializerMethodField()
    gender        = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    phone_number  = serializers.SerializerMethodField()
    phone_number2 = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()
    country       = serializers.SerializerMethodField()
    province      = serializers.SerializerMethodField()
    district      = serializers.SerializerMethodField()
    city          = serializers.SerializerMethodField()

    class Meta:
        model  = CustomUser
        fields = [
            'uuid', 'email', 'username',
            'is_active', 'is_verified', 'status', 'is_staff', 'is_sysadmin',
            'role', 'role_uuid',
            'first_name', 'last_name', 'gender', 'date_of_birth',
            'phone_number', 'phone_number2', 'contact_email',
            'country', 'province', 'district', 'city',
            'created_at', 'updated_at',
        ]

    def get_role(self, obj):
        user_role = getattr(obj, 'user_role', None)
        return user_role.role.name if user_role else None

    def get_role_uuid(self, obj):
        user_role = getattr(obj, 'user_role', None)
        return user_role.role.uuid if user_role else None

    def get_first_name(self, obj):
        return obj.personal.first_name if obj.personal else None

    def get_last_name(self, obj):
        return obj.personal.last_name if obj.personal else None

    def get_gender(self, obj):
        return obj.personal.gender if obj.personal else None

    def get_date_of_birth(self, obj):
        return obj.personal.date_of_birth if obj.personal else None

    def get_phone_number(self, obj):
        return obj.contact.phone_number if obj.contact else None

    def get_phone_number2(self, obj):
        return obj.contact.phone_number2 if obj.contact else None

    def get_contact_email(self, obj):
        return obj.contact.email if obj.contact else None

    def get_country(self, obj):
        return obj.address.country if obj.address else None

    def get_province(self, obj):
        return obj.address.province if obj.address else None

    def get_district(self, obj):
        return obj.address.district if obj.address else None

    def get_city(self, obj):
        return obj.address.city if obj.address else None


class UserCreateSerializer(serializers.Serializer):
    email      = serializers.EmailField()
    username   = serializers.CharField(max_length=50, required=False, allow_blank=True)
    password   = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name  = serializers.CharField(max_length=100, required=False, allow_blank=True)
    is_staff   = serializers.BooleanField(required=False, default=False)
    role_uuid  = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_role_uuid(self, value):
        if value is None:
            return value
        org = self.context['org']
        if not Role.objects.filter(uuid=value, org=org).exists():
            raise serializers.ValidationError("Role not found in this organization.")
        return value

    def create(self, validated_data):
        org = self.context['org']
        role_uuid  = validated_data.pop('role_uuid', None)
        first_name = validated_data.pop('first_name', '')
        last_name  = validated_data.pop('last_name', '')
        password   = validated_data.pop('password')

        personal = None
        if first_name or last_name:
            personal = PersonalDetail.objects.create(first_name=first_name, last_name=last_name)

        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=password,
            username=validated_data.get('username', ''),
            is_staff=validated_data.get('is_staff', False),
            org=org,
            personal=personal,
        )

        if role_uuid:
            role = Role.objects.get(uuid=role_uuid, org=org)
            UserRole.objects.create(user=user, role=role)

        return user


class UserUpdateSerializer(serializers.Serializer):
    """Partial update — active state, staff flag, role, basic personal info."""
    username   = serializers.CharField(max_length=50, required=False, allow_blank=True)
    is_active  = serializers.BooleanField(required=False)
    is_verified= serializers.BooleanField(required=False)
    status     = serializers.CharField(max_length=10, required=False)
    is_staff   = serializers.BooleanField(required=False)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name  = serializers.CharField(max_length=100, required=False, allow_blank=True)
    role_uuid  = serializers.UUIDField(required=False, allow_null=True)

    def validate_role_uuid(self, value):
        if value is None:
            return value
        org = self.context['org']
        if not Role.objects.filter(uuid=value, org=org).exists():
            raise serializers.ValidationError("Role not found in this organization.")
        return value

    def update(self, instance, validated_data):
        org = self.context['org']
        role_uuid  = validated_data.pop('role_uuid', serializers.empty)
        first_name = validated_data.pop('first_name', None)
        last_name  = validated_data.pop('last_name', None)

        for attr in ['username', 'is_active', 'is_staff', 'is_verified', 'status']:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])

        if first_name is not None or last_name is not None:
            if instance.personal:
                if first_name is not None:
                    instance.personal.first_name = first_name
                if last_name is not None:
                    instance.personal.last_name = last_name
                instance.personal.save()
            else:
                instance.personal = PersonalDetail.objects.create(
                    first_name=first_name or '', last_name=last_name or ''
                )

        instance.save()

        if role_uuid is not serializers.empty:
            UserRole.objects.filter(user=instance).delete()
            if role_uuid:
                role = Role.objects.get(uuid=role_uuid, org=org)
                UserRole.objects.create(user=instance, role=role)

        return instance
    




class ResetPasswordSerializer(serializers.Serializer):
    email       = serializers.EmailField()
    reset_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        # Runs Django's full password validator chain (length, common passwords, etc.)
        validate_password(value)
        return value