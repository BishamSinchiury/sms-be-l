from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from organization.models import Organization
from core.models import PersonalDetail, ContactDetail, AddressDetail
from users.models import CustomUser, UserProfile
from Academics.models import AcademicYear, Program, Sem, Grade, ClassSubjectConfig, SchoolLevel, UniversityLevel
from .models import Student, GuardianProfile, StudentProfile, Enrollment

class StudentAndEnrollmentTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org", domain_name="test.org")
        
        self.student_personal = {
            "first_name": "Alice",
            "last_name": "Smith",
        }
        self.guardian_personal = {
            "first_name": "Bob",
            "last_name": "Smith",
        }

    def test_create_student_success(self):
        student = Student.objects.create_student(
            org=self.org,
            student_email="alice@test.org",
            student_personal=self.student_personal,
            guardian_email="bob@test.org",
            guardian_personal=self.guardian_personal,
            guardian_relation="father",
            admission_number="ADM-001"
        )
        
        self.assertEqual(student.user.email, "alice@test.org")
        self.assertEqual(student.guardian.email, "bob@test.org")
        self.assertEqual(student.user.profile.personal.first_name, "Alice")
        self.assertEqual(student.guardian.profile.personal.first_name, "Bob")
        self.assertEqual(student.user.profile.student_profile.admission_number, "ADM-001")
        self.assertEqual(student.guardian.profile.guardian_profile.relation_to_student, "father")

    def test_create_student_duplicate_email_fails(self):
        Student.objects.create_student(
            org=self.org,
            student_email="alice@test.org",
            student_personal=self.student_personal,
            guardian_email="bob@test.org",
            guardian_personal=self.guardian_personal,
            guardian_relation="father",
            admission_number="ADM-001"
        )
        
        # Second student with the same email should fail to create atomically
        with self.assertRaises(IntegrityError):
            Student.objects.create_student(
                org=self.org,
                student_email="alice@test.org",  # duplicate!
                student_personal={"first_name": "Eve", "last_name": "Evil"},
                guardian_email="eve.mom@test.org",
                guardian_personal={"first_name": "Mom", "last_name": "Evil"},
                guardian_relation="mother",
                admission_number="ADM-002"
            )

    def test_enrollment_xor_validation(self):
        student = Student.objects.create_student(
            org=self.org,
            student_email="alice@test.org",
            student_personal=self.student_personal,
            guardian_email="bob@test.org",
            guardian_personal=self.guardian_personal,
            guardian_relation="father",
            admission_number="ADM-001"
        )
        
        # Create academic prerequisites
        uni_lvl = UniversityLevel.objects.create(name="Bachelor", rank=1)
        sch_lvl = SchoolLevel.objects.create(name="High School", rank=1)
        
        program = Program.objects.create(org=self.org, level=uni_lvl, name="BSc CS")
        sem = Sem.objects.create(program=program, level_rank=1, name="Sem 1")
        
        grade = Grade.objects.create(level=sch_lvl, name="Grade 10", rank=10)
        year = AcademicYear.objects.create(org=self.org, name="2025", start_date="2025-01-01", end_date="2025-12-31")
        config = ClassSubjectConfig.objects.create(grade=grade, academic_year=year)
        
        # Valid University Enrollment
        enr1 = Enrollment(student=student, program=program, sem=sem)
        enr1.clean()  # Should not raise
        enr1.save()
        
        # Valid School Enrollment
        enr2 = Enrollment(student=student, grade=grade, class_config=config)
        enr2.clean()  # Should not raise
        enr2.save()

        # Invalid: Both Uni and School populated
        enr3 = Enrollment(student=student, program=program, sem=sem, grade=grade, class_config=config)
        with self.assertRaises(ValidationError):
            enr3.clean()
            
        # Invalid: Missing program but has sem
        enr4 = Enrollment(student=student, sem=sem)
        with self.assertRaises(ValidationError):
            enr4.clean()
            
        # Invalid: Neither paths provided
        enr5 = Enrollment(student=student)
        with self.assertRaises(ValidationError):
            enr5.clean()
