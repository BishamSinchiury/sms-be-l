import logging

from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Academics.models import ClassSubjectConfig, OptionalSubjectGroup
from Academics.serializers import ClassSubjectConfigSerializer
from Academics.serializers.class_subject_config import ConfigOptionalGroupSerializer
from rbac.mixins import ActivityLoggingMixin

logger = logging.getLogger("academics")


class ClassSubjectConfigViewSet(
    ActivityLoggingMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Subject blueprint for a school grade + stream combination.
    No destroy — DELETE returns 405.
    Optional groups managed via nested actions.
    Tenant isolation via grade__org.
    """

    queryset = ClassSubjectConfig.objects.select_related(
        "grade", "grade__org",
    ).prefetch_related(
        "streams",
        "compulsory_subjects",
        "optional_groups",
        "optional_groups__subjects",
    ).all()

    serializer_class    = ClassSubjectConfigSerializer
    log_metadata_fields = ["grade_id"]

    # ── queryset ──────────────────────────────────────────────────────────────

    def get_queryset(self):
        qs  = super().get_queryset()
        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        if org:
            qs = qs.filter(grade__org=org)

        if grade_id := self.request.query_params.get("grade_id"):
            qs = qs.filter(grade_id=grade_id)

        if stream_id := self.request.query_params.get("stream_id"):
            qs = qs.filter(streams__id=stream_id)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))

        return qs

    # ── write ─────────────────────────────────────────────────────────────────

    def perform_create(self, serializer):
        serializer.save()
        i = serializer.instance
        logger.info(
            "ClassSubjectConfig created: id=%s grade_id=%s "
            "compulsory=%s optional_groups=%s by user_id=%s",
            i.pk, i.grade_id,
            i.compulsory_count, i.optional_group_count,
            getattr(self.request.user, "id", None),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        i = serializer.instance
        logger.info(
            "ClassSubjectConfig updated: id=%s grade_id=%s "
            "compulsory=%s optional_groups=%s is_active=%s by user_id=%s",
            i.pk, i.grade_id,
            i.compulsory_count, i.optional_group_count, i.is_active,
            getattr(self.request.user, "id", None),
        )

    # ── nested: optional groups ───────────────────────────────────────────────

    def _get_group_or_404(self, config, group_pk):
        try:
            return config.optional_groups.get(pk=group_pk)
        except OptionalSubjectGroup.DoesNotExist:
            return None

    @action(detail=True, methods=["get"], url_path="optional-groups")
    def list_optional_groups(self, request, pk=None):
        config = self.get_object()
        groups = config.optional_groups.prefetch_related("subjects").all()
        return Response(ConfigOptionalGroupSerializer(groups, many=True).data)

    @action(detail=True, methods=["post"], url_path="optional-groups/add")
    def add_optional_group(self, request, pk=None):
        config     = self.get_object()
        serializer = ConfigOptionalGroupSerializer(
            data=request.data,
            context={"config": config, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(config=config)
        serializer.save_subjects(instance, serializer.validated_data.get("subject_ids"))
        logger.info(
            "Config OptionalGroup created: id=%s config_id=%s name=%r by user_id=%s",
            instance.pk, config.pk, instance.name,
            getattr(request.user, "id", None),
        )
        return Response(
            ConfigOptionalGroupSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True, methods=["patch"],
        url_path=r"optional-groups/(?P<group_pk>[^/.]+)/update",
    )
    def update_optional_group(self, request, pk=None, group_pk=None):
        config = self.get_object()
        group  = self._get_group_or_404(config, group_pk)
        if group is None:
            return Response(
                {"detail": "Optional group not found for this config."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ConfigOptionalGroupSerializer(
            group, data=request.data, partial=True,
            context={"config": config, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        serializer.save_subjects(instance, serializer.validated_data.get("subject_ids"))
        logger.info(
            "Config OptionalGroup updated: id=%s config_id=%s name=%r by user_id=%s",
            instance.pk, config.pk, instance.name,
            getattr(request.user, "id", None),
        )
        return Response(ConfigOptionalGroupSerializer(instance).data)

    @action(
        detail=True, methods=["delete"],
        url_path=r"optional-groups/(?P<group_pk>[^/.]+)/remove",
    )
    def remove_optional_group(self, request, pk=None, group_pk=None):
        config = self.get_object()
        group  = self._get_group_or_404(config, group_pk)
        if group is None:
            return Response(
                {"detail": "Optional group not found for this config."},
                status=status.HTTP_404_NOT_FOUND,
            )
        group_id, group_name = group.pk, group.name
        group.delete()
        logger.info(
            "Config OptionalGroup deleted: id=%s config_id=%s name=%r by user_id=%s",
            group_id, config.pk, group_name,
            getattr(request.user, "id", None),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)