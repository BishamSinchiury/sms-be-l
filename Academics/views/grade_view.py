import logging

from rest_framework import mixins, viewsets

from Academics.models import Grade
from Academics.serializers import GradeSerializer
from rbac.mixins import ActivityLoggingMixin

logger = logging.getLogger("academics")


class GradeViewSet(
    ActivityLoggingMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    No destroy — Grade.delete() raises NotImplementedError at the model
    level as a backstop, but DestroyModelMixin is dropped here too so
    DELETE requests get a clean 405 instead of bubbling up into a 500.

    Audit logging (ActivityLog) is handled automatically by
    ActivityLoggingMixin on create/update — see log_metadata_fields below
    for what gets captured.
    """

    queryset = Grade.objects.select_related("level", "org").all()
    serializer_class = GradeSerializer
    log_metadata_fields = ["name", "short", "level_id", "order"]

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        if org is not None:
            qs = qs.filter(org=org)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))

        level = self.request.query_params.get("level")
        if level is not None:
            qs = qs.filter(level=level)

        return qs

    def perform_create(self, serializer):
        super().perform_create(serializer)  # saves + writes ActivityLog
        instance = serializer.instance
        logger.info(
            "Grade created: id=%s name=%r org_id=%s level_id=%s order=%s by user_id=%s",
            instance.pk, instance.name, instance.org_id, instance.level_id, instance.order,
            getattr(self.request.user, "id", None),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)  # saves + writes ActivityLog
        instance = serializer.instance
        logger.info(
            "Grade updated: id=%s name=%r short=%r level_id=%s order=%s is_active=%s by user_id=%s",
            instance.pk, instance.name, instance.short, instance.level_id,
            instance.order, instance.is_active,
            getattr(self.request.user, "id", None),
        )