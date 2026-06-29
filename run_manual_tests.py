import os
import django
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sms.settings")
django.setup()

from organization.models import Organization
from Academics.models import AcademicYear, Program, Sem, Grade, ClassSubjectConfig, SchoolLevel, UniversityLevel, Subject, OptionalSubjectGroup
from Students.models import Student, GuardianProfile, StudentProfile, Enrollment, EnrollmentSubjectSelection
from Students.serializers import StudentCreateSerializer
from users.models import CustomUser

print("\n--- Running Comprehensive Edge Case Tests ---")

def run_tests():
    try:
        with transaction.atomic():
            print("\n[Setup] Creating core entities...")
            org, _ = Organization.objects.get_or_create(name="Test Org DB", domain_name="testdb.org")
            
            # Clean up existing test users just in case
            CustomUser.objects.filter(email__in=["alice.db@test.org", "bob.db@test.org", "duplicate@test.org", "stu2@test.org", "g2@test.org"]).delete()

            print("\n--- 1. Testing Student Creation & Serializer ---")
            # Serializer validation: Student and Guardian emails must differ
            serializer = StudentCreateSerializer(data={
                "org": org.id,
                "student_email": "same@test.org",
                "student_personal": {"first_name": "A", "last_name": "B"},
                "guardian_email": "same@test.org",
                "guardian_personal": {"first_name": "C", "last_name": "D"},
                "guardian_relation": "father",
                "admission_number": "ADM-100"
            })
            assert not serializer.is_valid(), "Serializer should reject matching student and guardian emails"
            assert "guardian_email" in serializer.errors
            print("✓ Serializer correctly blocks matching student/guardian emails.")

            # Create base student
            student_personal = {"first_name": "Alice", "last_name": "Smith"}
            guardian_personal = {"first_name": "Bob", "last_name": "Smith"}
            student = Student.objects.create_student(
                org=org,
                student_email="alice.db@test.org",
                student_personal=student_personal,
                guardian_email="bob.db@test.org",
                guardian_personal=guardian_personal,
                guardian_relation="father",
                admission_number="ADM-DB-001"
            )
            print("✓ Base student created successfully.")

            print("\n--- 2. Testing Enrollment XOR Logic (clean method) ---")
            uni_lvl, _ = UniversityLevel.objects.get_or_create(org=org, name="Bachelor", order=1)
            sch_lvl, _ = SchoolLevel.objects.get_or_create(org=org, name="High School", order=1)
            
            program, _ = Program.objects.get_or_create(org=org, level=uni_lvl, name="BSc CS")
            sem, _ = Sem.objects.get_or_create(program=program, order=1, name="Sem 1")
            
            grade, _ = Grade.objects.get_or_create(org=org, level=sch_lvl, name="Grade 10", order=10)
            config, _ = ClassSubjectConfig.objects.get_or_create(grade=grade)
            
            # 2a. Both paths provided
            enr_both = Enrollment(student=student, program=program, sem=sem, grade=grade, class_config=config)
            try:
                enr_both.clean()
                raise AssertionError("Should have blocked both paths")
            except ValidationError as e:
                print("✓ Correctly rejected providing BOTH University and School paths.")

            # 2b. Neither paths provided
            enr_neither = Enrollment(student=student)
            try:
                enr_neither.clean()
                raise AssertionError("Should have blocked neither paths")
            except ValidationError as e:
                print("✓ Correctly rejected providing NEITHER path.")

            # 2c. Partial University (missing Sem)
            enr_part_uni = Enrollment(student=student, program=program)
            try:
                enr_part_uni.clean()
                raise AssertionError("Should have blocked missing Sem")
            except ValidationError as e:
                print("✓ Correctly rejected Program without Sem.")

            # 2d. Partial School (missing ClassConfig)
            enr_part_sch = Enrollment(student=student, grade=grade)
            try:
                enr_part_sch.clean()
                raise AssertionError("Should have blocked missing Config")
            except ValidationError as e:
                print("✓ Correctly rejected Grade without ClassConfig.")

            print("\n--- 3. Testing Enrollment DB Constraints ---")
            # Create a valid enrollment
            valid_enr_1 = Enrollment.objects.create(student=student, program=program, sem=sem)
            
            # 3a. Unique constraint: Student cannot enroll in the same Sem twice
            try:
                with transaction.atomic():
                    Enrollment.objects.create(student=student, program=program, sem=sem)
                raise AssertionError("Allowed duplicate enrollment in same semester!")
            except IntegrityError:
                print("✓ Database correctly prevented duplicate enrollment for the same Semester.")

            # 3b. Unique constraint: Student cannot enroll in the same Grade Config twice
            valid_enr_2 = Enrollment.objects.create(student=student, grade=grade, class_config=config)
            try:
                with transaction.atomic():
                    Enrollment.objects.create(student=student, grade=grade, class_config=config)
                raise AssertionError("Allowed duplicate enrollment in same grade config!")
            except IntegrityError:
                print("✓ Database correctly prevented duplicate enrollment for the same Grade Config.")

            print("\n--- 4. Testing Subject Selection DB Constraints ---")
            sub1, _ = Subject.objects.get_or_create(org=org, name="Math", code="M101")
            sub2, _ = Subject.objects.get_or_create(org=org, name="Physics", code="P101")
            opt_grp, _ = OptionalSubjectGroup.objects.get_or_create(name="Science Electives", sem=sem)
            
            # Select subject 1 in the group
            EnrollmentSubjectSelection.objects.create(
                enrollment=valid_enr_1,
                optional_group=opt_grp,
                subject=sub1
            )
            
            # Try to select subject 2 in the same group (violates unique_together)
            try:
                with transaction.atomic():
                    EnrollmentSubjectSelection.objects.create(
                        enrollment=valid_enr_1,
                        optional_group=opt_grp,
                        subject=sub2
                    )
                raise AssertionError("Allowed selecting multiple subjects for the same optional group!")
            except IntegrityError:
                print("✓ Database correctly prevented multiple subject selections for the same optional group.")

            print("\nAll tests passed successfully!")
            # Rollback to keep dev db clean
            raise Exception("Force rollback to keep dev db clean")
            
    except Exception as e:
        if str(e) == "Force rollback to keep dev db clean":
            print("\n--- Testing complete. Dev DB rolled back successfully. ---")
        else:
            print(f"\n--- Tests failed! {e} ---")
            sys.exit(1)

if __name__ == "__main__":
    run_tests()
