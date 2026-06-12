# rbac/utils.py
import logging
from django.contrib.contenttypes.models import ContentType
from rbac.models import ActivityLog

logger = logging.getLogger(__name__)


def log_activity(user, action, request=None, target=None, metadata=None):
    """
    Logs any user action against any model in the system.

    Usage:
        log_activity(
            user=request.user,
            action=ActivityLog.Action.USER_DEACTIVATED,
            request=request,
            target=some_user,        # any model instance
            metadata={'reason': '..'}
        )
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

    try:
        ActivityLog.objects.create(
            user=user,
            action=action,
            content_type=content_type,
            object_uuid=object_uuid,
            metadata=metadata or {},
            ip_address=ip,
        )
    except Exception as e:
        logger.error(
            f"Failed to write activity log: {e} "
            f"user={getattr(user, 'email', None)} "
            f"action={action}"
        )