import logging

from rest_framework import mixins, viewsets

from Academics.models import Stream
from Academics.serializers import StreamSerializer
from rbac.mixins import ActivityLoggingMixin

logger = logging.getLogger("academics")


class StreamViewSet(
    ActivityLoggingMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    No destroy mixin — DELETE returns 405.
    Tenant isolation via level__org (Stream has no direct org FK).
    Audit logging handled by ActivityLoggingMixin.
    """

    queryset = Stream.objects.select_related("level", "level__org").all()
    serializer_class = StreamSerializer
    log_metadata_fields = ["name", "short", "level_id"]

    def get_queryset(self):
        qs = super().get_queryset()

        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        if org is not None:
            qs = qs.filter(level__org=org)

        level_id = self.request.query_params.get("level_id")
        if level_id is not None:
            qs = qs.filter(level_id=level_id)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))

        return qs

    def perform_create(self, serializer):
        serializer.save()
        instance = serializer.instance
        logger.info(
            "Stream created: id=%s name=%r short=%r level_id=%s by user_id=%s",
            instance.pk, instance.name, instance.short, instance.level_id,
            getattr(self.request.user, "id", None),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "Stream updated: id=%s name=%r short=%r level_id=%s is_active=%s by user_id=%s",
            instance.pk, instance.name, instance.short, instance.level_id, instance.is_active,
            getattr(self.request.user, "id", None),
        )