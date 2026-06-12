
from rbac.models import Permission, Role, RolePermission, UserPermissionOverride
from rest_framework import serializers

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Permission
        fields = ['uuid', 'codename', 'name']

    def validate_codename(self, value):
        org = self.context['org']
        qs = Permission.objects.filter(org=org, codename=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A permission with this codename already exists.")
        return value

    def create(self, validated_data):
        return Permission.objects.create(org=self.context['org'], **validated_data)


class RoleSerializer(serializers.ModelSerializer):
    """
    permissions   → read-only nested list of full Permission objects
    permission_uuids → write-only list used to set the role's permission set
                       (replaces existing assignments entirely on each write)
    """
    permissions      = PermissionSerializer(many=True, read_only=True)
    permission_uuids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model  = Role
        fields = [
            'uuid', 'name', 'description',
            'permissions', 'permission_uuids', 'user_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        return obj.user_roles.count()

    def validate_name(self, value):
        org = self.context['org']
        qs = Role.objects.filter(org=org, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A role with this name already exists.")
        return value

    def validate_permission_uuids(self, value):
        org = self.context['org']
        found = Permission.objects.filter(org=org, uuid__in=value).count()
        if found != len(set(value)):
            raise serializers.ValidationError("One or more permissions not found in this organization.")
        return value

    def create(self, validated_data):
        perm_uuids = validated_data.pop('permission_uuids', [])
        org = self.context['org']
        role = Role.objects.create(org=org, **validated_data)
        if perm_uuids:
            perms = Permission.objects.filter(org=org, uuid__in=perm_uuids)
            RolePermission.objects.bulk_create([
                RolePermission(role=role, permission=p) for p in perms
            ])
        return role

    def update(self, instance, validated_data):
        perm_uuids = validated_data.pop('permission_uuids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if perm_uuids is not None:
            org = self.context['org']
            RolePermission.objects.filter(role=instance).delete()
            perms = Permission.objects.filter(org=org, uuid__in=perm_uuids)
            RolePermission.objects.bulk_create([
                RolePermission(role=instance, permission=p) for p in perms
            ])

        return instance