from rest_framework import serializers
from django.contrib.auth import authenticate

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])

        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        # Must be either admin or sysadmin to use this endpoint
        if not user.is_staff and not user.is_sysadmin:
            raise serializers.ValidationError("Admin access required.")

        data['user'] = user
        return data


class AdminOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)