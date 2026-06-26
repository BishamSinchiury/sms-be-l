from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from Academics.models import AcademicYear
from Academics.serializers import AcademicYearSerializer


class AcademicYearViewSet(ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated]

    lookup_field = "uuid"

    def get_queryset(self):
        return AcademicYear.objects.filter(org=self.request.user.org)

    def perform_create(self, serializer):
        print(self.request.user.org)
        serializer.save(org=self.request.user.org)

    