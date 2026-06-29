from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EnrollmentSubjectSelectionViewSet,
    EnrollmentViewSet,
    StudentCreateView,
    StudentDetailView,
    StudentListView,
)

router = DefaultRouter()
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("subject-selections", EnrollmentSubjectSelectionViewSet, basename="subject-selection")

urlpatterns = [
    path("students/",          StudentListView.as_view(),   name="student-list"),
    path("students/create/",   StudentCreateView.as_view(), name="student-create"),
    path("students/<int:pk>/", StudentDetailView.as_view(), name="student-detail"),
    path("", include(router.urls)),
]
