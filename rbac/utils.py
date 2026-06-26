# rbac/utils.py
import logging
from django.contrib.contenttypes.models import ContentType
from rbac.models import ActivityLog

logger = logging.getLogger(__name__)


def log_activity(user, verb, request=None, target=None, target_repr=None, metadata=None):
    """
    Logs any user action against any model in the system.

    `verb` is an ActivityLog.Verb value (CREATED, UPDATED, DELETED, ...).
    The "what kind of thing" (Program, SubOrganization, ...) is derived
    automatically from `target`'s model — no per-model enum entry needed.

    Usage:
        log_activity(
            user=request.user,
            verb=ActivityLog.Verb.DEACTIVATED,
            request=request,
            target=some_user,        # any model instance
            metadata={'reason': '..'}
        )

    For verbs with no target model (LOGIN, LOGOUT, LOGIN_FAILED), omit `target`.

    For logging after a delete, pass `target_repr` explicitly (e.g.
    `str(instance)` captured before `.delete()`), since the instance
    itself may already be gone by the time this is called:
        log_activity(user=request.user, verb=ActivityLog.Verb.DELETED,
                     request=request, target=None, target_repr=repr_, metadata={...})
    """
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')

    # Resolve content type and uuid from the target object
    content_type = None
    object_uuid  = None

    if target:
        content_type = ContentType.objects.get_for_model(target)
        object_uuid  = getattr(target, 'uuid', None)
        if target_repr is None:
            target_repr = str(target)

    try:
        ActivityLog.objects.create(
            user=user,
            verb=verb,
            content_type=content_type,
            object_uuid=object_uuid,
            target_repr=target_repr or '',
            metadata=metadata or {},
            ip_address=ip,
        )
    except Exception as e:
        logger.error(
            f"Failed to write activity log: {e} "
            f"user={getattr(user, 'email', None)} "
            f"verb={verb}"
        )