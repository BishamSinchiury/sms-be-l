from django.contrib import admin

from .models import (
    Enrollment,
    EnrollmentSubjectSelection,
    GuardianProfile,
    Student,
    StudentProfile,
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ["user", "org", "status", "is_active", "created_at"]
    list_filter   = ["status", "is_active", "org"]
    search_fields = ["user__email"]


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display  = ["user_profile", "admission_number", "roll_number"]
    search_fields = ["admission_number", "user_profile__user__email"]


@admin.register(GuardianProfile)
class GuardianProfileAdmin(admin.ModelAdmin):
    list_display  = ["user_profile", "relation_to_student", "occupation"]
    list_filter   = ["relation_to_student"]
    search_fields = ["user_profile__user__email"]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "status", "enrolled_on"]
    list_filter  = ["status"]


@admin.register(EnrollmentSubjectSelection)
class EnrollmentSubjectSelectionAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "optional_group", "subject"]
