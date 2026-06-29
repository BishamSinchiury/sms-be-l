import logging

from rest_framework import generics, mixins, status, viewsets
from rest_framework.response import Response

from .models import Enrollment, EnrollmentSubjectSelection, Student
from .serializers import (
    EnrollmentSerializer,
    EnrollmentSubjectSelectionSerializer,
    StudentCreateSerializer,
    StudentReadSerializer,
)

logger = logging.getLogger(__name__)


class StudentCreateView(generics.CreateAPIView):
    """POST /api/students/create/ — provision student + guardian accounts."""

    serializer_class = StudentCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        logger.info(
            "Student created: id=%s email=%s org_id=%s by user_id=%s",
            student.pk, student.user.email, student.org_id,
            getattr(request.user, "id", None),
        )
        return Response(StudentReadSerializer(student).data, status=status.HTTP_201_CREATED)


class StudentListView(generics.ListAPIView):
    """GET /api/students/ — list all students (org-scoped)."""

    serializer_class = StudentReadSerializer

    def get_queryset(self):
        qs = Student.objects.select_related(
            "user", "user__profile", "user__profile__personal",
            "user__profile__student_profile",
            "guardian",
        ).all()

        org = getattr(self.request.user, "org", None)
        if org:
            qs = qs.filter(org=org)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(user__email__icontains=search)

        return qs


class StudentDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/students/<id>/ — retrieve or update a student's status/is_active."""

    serializer_class = StudentReadSerializer

    def get_queryset(self):
        qs = Student.objects.select_related(
            "user", "user__profile", "user__profile__personal",
            "user__profile__student_profile",
            "guardian",
        )
        org = getattr(self.request.user, "org", None)
        if org:
            qs = qs.filter(org=org)
        return qs


class EnrollmentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD for Enrollment (no destroy — update status instead)."""

    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        qs = Enrollment.objects.select_related(
            "student", "program", "sem", "grade", "class_config", "stream",
        ).all()

        student_id = self.request.query_params.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)

        return qs


class EnrollmentSubjectSelectionViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Full CRUD for subject selections (destroy allowed — student can change picks)."""

    serializer_class = EnrollmentSubjectSelectionSerializer

    def get_queryset(self):
        qs = EnrollmentSubjectSelection.objects.select_related(
            "enrollment", "optional_group", "subject",
        ).all()

        enrollment_id = self.request.query_params.get("enrollment")
        if enrollment_id:
            qs = qs.filter(enrollment_id=enrollment_id)

        return qs
