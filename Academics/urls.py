from django.urls import path, include
from rest_framework.routers import DefaultRouter

from Academics.views import (
    AcademicYearViewSet,
    UniversityLevelViewSet,
    SchoolLevelViewSet,
    ProgramViewSet,
    GradeViewSet,
    SemViewSet,
    StreamViewSet,
    SubjectViewSet,
    ClassSubjectConfigViewSet,
)

router = DefaultRouter()
router.register(r'academic-years',        AcademicYearViewSet,        basename='academic-years')
router.register(r'university-levels',     UniversityLevelViewSet,     basename='university-levels')
router.register(r'school-levels',         SchoolLevelViewSet,         basename='school-levels')
router.register(r'programs',              ProgramViewSet,             basename='programs')
router.register(r'grades',               GradeViewSet,               basename='grades')
router.register(r'semesters',            SemViewSet,                 basename='semesters')
router.register(r'streams',              StreamViewSet,              basename='streams')
router.register(r'subjects',             SubjectViewSet,             basename='subjects')
router.register(r'class-subject-configs', ClassSubjectConfigViewSet, basename='class-subject-configs')

urlpatterns = [
    path('', include(router.urls)),
]