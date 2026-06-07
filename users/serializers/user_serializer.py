from rest_framework import serializers
from users.models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('uuid', 'email', 'username', 'is_verified', 'is_staff', 'is_sysadmin')
        read_only_fields = fields