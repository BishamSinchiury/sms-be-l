from rest_framework import mixins, viewsets

from Academics.models import UniversityLevel, SchoolLevel
from Academics.serializers import UniversityLevelSerializer, SchoolLevelSerializer


class _BaseLevelViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read + update only. No create, no destroy.

    These models are seed data populated via management command
    (`seed_levels`); rows can't be created or deleted through the API
    — `Model.delete()` itself raises NotImplementedError as a backstop.
    Only `order` and `is_active` are meant to be changed here (enforced
    in the serializer via read_only_fields on name/org).
    """

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request.user, "org", None) or getattr(self.request, "org", None)
        if org is not None:
            qs = qs.filter(org=org)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))

        return qs


class UniversityLevelViewSet(_BaseLevelViewSet):
    queryset = UniversityLevel.objects.all()
    serializer_class = UniversityLevelSerializer


class SchoolLevelViewSet(_BaseLevelViewSet):
    queryset = SchoolLevel.objects.all()
    serializer_class = SchoolLevelSerializer