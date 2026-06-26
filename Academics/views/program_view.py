import logging

from rest_framework import mixins, viewsets

from Academics.models import Program
from Academics.serializers import ProgramSerializer
from rbac.mixins import ActivityLoggingMixin

logger = logging.getLogger("academics")


class ProgramViewSet(
    ActivityLoggingMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    No destroy — Program.delete() raises NotImplementedError at the model
    level as a backstop, but we drop DestroyModelMixin here too so DELETE
    requests get a clean 405 instead of bubbling up into a 500.

    Audit logging (ActivityLog) is handled automatically by
    ActivityLoggingMixin — create/update get logged with no extra code
    here. log_metadata_fields controls what gets captured.
    """

    queryset = Program.objects.select_related("level", "org").all()
    serializer_class = ProgramSerializer
    log_metadata_fields = ["name", "short", "level_id"]

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
        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        serializer.save(org=org)
        instance = serializer.instance
        logger.info(
            "Program created: id=%s name=%r org_id=%s level_id=%s by user_id=%s",
            instance.pk, instance.name, instance.org_id, instance.level_id,
            getattr(self.request.user, "id", None),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)  # saves + writes ActivityLog
        instance = serializer.instance
        logger.info(
            "Program updated: id=%s name=%r short=%r level_id=%s is_active=%s by user_id=%s",
            instance.pk, instance.name, instance.short, instance.level_id, instance.is_active,
            getattr(self.request.user, "id", None),
        )