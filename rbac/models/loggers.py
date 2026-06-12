# rbac/models.py — add this at the bottom
import uuid
from django.db import models
from core.models import TimestampModel

# rbac/models.py
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class ActivityLog(TimestampModel):
    class Action(models.TextChoices):
        LOGIN               = 'LOGIN',              'Logged in'
        LOGOUT              = 'LOGOUT',             'Logged out'
        LOGIN_FAILED        = 'LOGIN_FAILED',       'Failed login attempt'
        USER_CREATED        = 'USER_CREATED',       'Created user'
        USER_UPDATED        = 'USER_UPDATED',       'Updated user'
        USER_DELETED        = 'USER_DELETED',       'Deleted user'
        USER_ACTIVATED      = 'USER_ACTIVATED',     'Activated user'
        USER_DEACTIVATED    = 'USER_DEACTIVATED',   'Deactivated user'
        ROLE_CREATED        = 'ROLE_CREATED',       'Created role'
        ROLE_UPDATED        = 'ROLE_UPDATED',       'Updated role'
        ROLE_DELETED        = 'ROLE_DELETED',       'Deleted role'
        ROLE_ASSIGNED       = 'ROLE_ASSIGNED',      'Assigned role to user'
        PERMISSION_GRANTED  = 'PERMISSION_GRANTED', 'Granted permission'
        PERMISSION_REVOKED  = 'PERMISSION_REVOKED', 'Revoked permission'
        ORG_UPDATED         = 'ORG_UPDATED',        'Updated organization'
        SUBORG_CREATED      = 'SUBORG_CREATED',     'Created sub-organization'
        SUBORG_UPDATED      = 'SUBORG_UPDATED',     'Updated sub-organization'
        SUBORG_DELETED      = 'SUBORG_DELETED',     'Deleted sub-organization'

    uuid       = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user       = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs'
    )
    action     = models.CharField(max_length=50, choices=Action.choices)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_uuid  = models.UUIDField(null=True, blank=True)

    target       = GenericForeignKey('content_type', 'object_uuid')

    metadata     = models.JSONField(default=dict, blank=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.action} — {self.created_at}"