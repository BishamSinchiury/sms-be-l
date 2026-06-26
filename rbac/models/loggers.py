# rbac/models.py
import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.models import TimestampModel


class ActivityLog(TimestampModel):
    class Verb(models.TextChoices):
        # Generic CRUD — covers ~90% of actions across every model,
        # no per-model enum member needed.
        CREATED      = 'CREATED',      'Created'
        UPDATED      = 'UPDATED',      'Updated'
        DELETED      = 'DELETED',      'Deleted'
        ACTIVATED    = 'ACTIVATED',    'Activated'
        DEACTIVATED  = 'DEACTIVATED',  'Deactivated'
        ASSIGNED     = 'ASSIGNED',     'Assigned'
        REVOKED      = 'REVOKED',      'Revoked'

        # Non-CRUD / auth events — these aren't tied to a model instance
        # in the usual sense, so they stay as their own verbs.
        LOGIN        = 'LOGIN',        'Logged in'
        LOGOUT       = 'LOGOUT',       'Logged out'
        LOGIN_FAILED = 'LOGIN_FAILED', 'Failed login attempt'

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs',
    )

    verb = models.CharField(max_length=20, choices=Verb.choices)

    # What kind of thing was acted on (Program, SubOrganization, Role, ...).
    # Nullable for verbs like LOGIN/LOGOUT that have no target model.
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    object_uuid = models.UUIDField(null=True, blank=True)
    target = GenericForeignKey('content_type', 'object_uuid')

    # Free-text label for the target at the time of the action, captured
    # so deleted objects (target=None after delete) still read well —
    # e.g. "Acme Branch" instead of just "SubOrganization #deleted".
    target_repr = models.CharField(max_length=255, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.describe()} — {self.created_at}"

    def describe(self):
        """Human-readable line, generated instead of hand-written per action."""
        verb_label = self.get_verb_display()
        if self.content_type:
            entity = self.content_type.model_class()._meta.verbose_name
            target_label = self.target_repr or str(self.target or "")
            return f"{verb_label} {entity}" + (f" \u2014 {target_label}" if target_label else "")
        return verb_label