from rest_framework import serializers
from rbac.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    user_email     = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    target_type    = serializers.SerializerMethodField()

    class Meta:
        model  = ActivityLog
        fields = [
            'uuid', 'user_email', 'action', 'action_display',
            'target_type', 'object_uuid', 'metadata', 'ip_address', 'created_at',
        ]

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None

    def get_target_type(self, obj):
        return obj.content_type.model if obj.content_type else None