import logging

from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from Academics.models import Sem, OptionalSubjectGroup
from Academics.serializers import SemSerializer
from Academics.serializers import SemOptionalGroupSerializer
from rbac.mixins import ActivityLoggingMixin

logger = logging.getLogger("academics")


class SemViewSet(
    ActivityLoggingMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Semesters for university-level programs.
    No destroy — DELETE returns 405.
    Optional groups managed via nested actions.
    Tenant isolation via program__org.
    """

    queryset = Sem.objects.select_related(
        "program", "program__org",
    ).prefetch_related(
        "compulsory_subjects",
        "optional_groups",
        "optional_groups__subjects",
    ).all()

    serializer_class    = SemSerializer
    log_metadata_fields = ["name", "program_id", "order"]

    # ── queryset ──────────────────────────────────────────────────────────────

    def get_queryset(self):
        qs  = super().get_queryset()
        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        if org:
            qs = qs.filter(program__org=org)

        if program_id := self.request.query_params.get("program_id"):
            qs = qs.filter(program_id=program_id)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))

        return qs

    # ── write ─────────────────────────────────────────────────────────────────

    def perform_create(self, serializer):
        serializer.save()
        i = serializer.instance
        logger.info(
            "Sem created: id=%s name=%r program_id=%s order=%s "
            "compulsory=%s optional_groups=%s by user_id=%s",
            i.pk, i.name, i.program_id, i.order,
            i.compulsory_count, i.optional_group_count,
            getattr(self.request.user, "id", None),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        i = serializer.instance
        logger.info(
            "Sem updated: id=%s name=%r program_id=%s order=%s "
            "compulsory=%s optional_groups=%s is_active=%s by user_id=%s",
            i.pk, i.name, i.program_id, i.order,
            i.compulsory_count, i.optional_group_count, i.is_active,
            getattr(self.request.user, "id", None),
        )

    # ── nested: optional groups ───────────────────────────────────────────────

    def _get_group_or_404(self, sem, group_pk):
        try:
            return sem.optional_groups.get(pk=group_pk)
        except OptionalSubjectGroup.DoesNotExist:
            return None

    @action(detail=True, methods=["get"], url_path="optional-groups")
    def list_optional_groups(self, request, pk=None):
        sem    = self.get_object()
        groups = sem.optional_groups.prefetch_related("subjects").all()
        return Response(SemOptionalGroupSerializer(groups, many=True).data)

    @action(detail=True, methods=["post"], url_path="optional-groups/add")
    def add_optional_group(self, request, pk=None):
        sem        = self.get_object()
        serializer = SemOptionalGroupSerializer(
            data=request.data,
            context={"sem": sem, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(sem=sem)
        serializer.save_subjects(instance, serializer.validated_data.get("subject_ids"))
        logger.info(
            "Sem OptionalGroup created: id=%s sem_id=%s name=%r by user_id=%s",
            instance.pk, sem.pk, instance.name,
            getattr(request.user, "id", None),
        )
        return Response(
            SemOptionalGroupSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True, methods=["patch"],
        url_path=r"optional-groups/(?P<group_pk>[^/.]+)/update",
    )
    def update_optional_group(self, request, pk=None, group_pk=None):
        sem   = self.get_object()
        group = self._get_group_or_404(sem, group_pk)
        if group is None:
            return Response(
                {"detail": "Optional group not found for this semester."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SemOptionalGroupSerializer(
            group, data=request.data, partial=True,
            context={"sem": sem, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        serializer.save_subjects(instance, serializer.validated_data.get("subject_ids"))
        logger.info(
            "Sem OptionalGroup updated: id=%s sem_id=%s name=%r by user_id=%s",
            instance.pk, sem.pk, instance.name,
            getattr(request.user, "id", None),
        )
        return Response(SemOptionalGroupSerializer(instance).data)

    @action(
        detail=True, methods=["delete"],
        url_path=r"optional-groups/(?P<group_pk>[^/.]+)/remove",
    )
    def remove_optional_group(self, request, pk=None, group_pk=None):
        sem   = self.get_object()
        group = self._get_group_or_404(sem, group_pk)
        if group is None:
            return Response(
                {"detail": "Optional group not found for this semester."},
                status=status.HTTP_404_NOT_FOUND,
            )
        group_id, group_name = group.pk, group.name
        group.delete()
        logger.info(
            "Sem OptionalGroup deleted: id=%s sem_id=%s name=%r by user_id=%s",
            group_id, sem.pk, group_name,
            getattr(request.user, "id", None),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)