import logging

from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Academics.models import (
    Subject,
    ClassSubjectConfig, OptionalSubjectGroup,
)
from Academics.serializers import (
    SubjectSerializer,
    ClassSubjectConfigSerializer,
    ConfigOptionalGroupSerializer,
)
from rbac.mixins import ActivityLoggingMixin

logger = logging.getLogger("academics")


# ─────────────────────────────────────────────────────────────────────────────
# Subject
# ─────────────────────────────────────────────────────────────────────────────

class SubjectViewSet(
    ActivityLoggingMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD for org-scoped subjects.
    No destroy — soft-deactivate via is_active instead.
    """

    queryset            = Subject.objects.select_related("org").all()
    serializer_class    = SubjectSerializer
    log_metadata_fields = ["name", "code"]

    def get_queryset(self):
        qs  = super().get_queryset()
        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        if org:
            qs = qs.filter(org=org)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)

        return qs

    def perform_create(self, serializer):
        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        serializer.save(org=org)
        instance = serializer.instance
        logger.info(
            "Subject created: id=%s name=%r code=%r org_id=%s by user_id=%s",
            instance.pk, instance.name, instance.code, instance.org_id,
            getattr(self.request.user, "id", None),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "Subject updated: id=%s name=%r code=%r is_active=%s by user_id=%s",
            instance.pk, instance.name, instance.code, instance.is_active,
            getattr(self.request.user, "id", None),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ClassSubjectConfig
# ─────────────────────────────────────────────────────────────────────────────

class ClassSubjectConfigViewSet(
    ActivityLoggingMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Subject blueprint for a grade+stream combination.
    Optional groups are managed via nested /optional-groups/ actions.
    No destroy — deactivate via is_active.
    """

    queryset = ClassSubjectConfig.objects.prefetch_related(
        "streams",
        "compulsory_subjects",
        "optional_groups",
        "optional_groups__subjects",
    ).select_related("grade", "grade__org").all()

    serializer_class    = ClassSubjectConfigSerializer
    log_metadata_fields = ["grade_id"]

    def get_queryset(self):
        qs  = super().get_queryset()
        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        if org:
            qs = qs.filter(grade__org=org)

        grade_id = self.request.query_params.get("grade_id")
        if grade_id:
            qs = qs.filter(grade_id=grade_id)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))

        return qs

    def perform_create(self, serializer):
        serializer.save()
        instance = serializer.instance
        logger.info(
            "ClassSubjectConfig created: id=%s grade_id=%s by user_id=%s",
            instance.pk, instance.grade_id,
            getattr(self.request.user, "id", None),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        logger.info(
            "ClassSubjectConfig updated: id=%s grade_id=%s is_active=%s by user_id=%s",
            instance.pk, instance.grade_id, instance.is_active,
            getattr(self.request.user, "id", None),
        )

    # ── Nested optional group management ─────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="optional-groups")
    def list_optional_groups(self, request, pk=None):
        config     = self.get_object()
        groups     = config.optional_groups.prefetch_related("subjects").all()
        serializer = ConfigOptionalGroupSerializer(groups, many=True)
        return Response(serializer.data)

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
            "OptionalSubjectGroup created: id=%s config_id=%s name=%r by user_id=%s",
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
        try:
            group = config.optional_groups.get(pk=group_pk)
        except OptionalSubjectGroup.DoesNotExist:
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
            "OptionalSubjectGroup updated: id=%s config_id=%s name=%r by user_id=%s",
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
        try:
            group = config.optional_groups.get(pk=group_pk)
        except OptionalSubjectGroup.DoesNotExist:
            return Response(
                {"detail": "Optional group not found for this config."},
                status=status.HTTP_404_NOT_FOUND,
            )
        group_id, group_name = group.pk, group.name
        group.delete()
        logger.info(
            "OptionalSubjectGroup deleted: id=%s config_id=%s name=%r by user_id=%s",
            group_id, config.pk, group_name,
            getattr(request.user, "id", None),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
