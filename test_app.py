import os
import unittest
import io
from app import create_app
from config import Config
from init_db import init_db
from database import query_db

class CSMTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fresh test database
        cls.test_db_path = os.path.join(Config.BASE_DIR, 'test_csm.sqlite3')
        Config.DB_PATH = cls.test_db_path
        init_db(force=True)
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

    @classmethod
    def tearDownClass(cls):
        # Cleanup test database file if desired
        pass

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess['_csrf_token'] = 'test-token'
        self.csrf = 'test-token'

    def tearDown(self):
        self.app_context.pop()

    def login(self, email, password, role='teacher'):
        if role == 'teacher':
            return self.client.post('/teacher/login', data={'csrf_token': self.csrf, 'email': email, 'password': password}, follow_redirects=True)
        elif role == 'admin':
            return self.client.post('/admin/login', data={'csrf_token': self.csrf, 'email': email, 'password': password}, follow_redirects=True)
        elif role == 'student':
            return self.client.post('/student/login', data={'csrf_token': self.csrf, 'email_or_reg': email, 'password': password}, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # -------------------------------------------------------------
    # Scenario 1: Admin creates a teacher account
    # -------------------------------------------------------------
    def test_01_admin_creates_teacher(self):
        print("\n[Test 1] Testing Admin Teacher Account Creation...")
        self.login('admin@college.edu', 'Admin@123', role='admin')
        res = self.client.post('/admin/teachers/create', data={
            'csrf_token': self.csrf,
            'name': 'Dr. Richard Feynman',
            'email': 'richard.feynman@college.edu',
            'employee_id': 'EMP109',
            'department': 'Computer Science',
            'college': 'Apex Institute of Technology',
            'phone': '9988776655',
            'subjects': ['1', '2'] # CS501 and CS502
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Dr. Richard Feynman", res.data)
        self.assertIn(b"Single-Use Activation Link Generated", res.data)

        # Verify teacher exists in DB and is inactive until activation
        user = query_db("SELECT id, is_active FROM users WHERE email = 'richard.feynman@college.edu'", one=True)
        self.assertIsNotNone(user)
        self.assertEqual(user['is_active'], 0) # inactive until activated
        self.logout()
        print("  -> Passed: Teacher account created with inactive state and activation link generated.")

    # -------------------------------------------------------------
    # Scenario 2: Teacher activates the account and sets a password
    # -------------------------------------------------------------
    def test_02_teacher_activates_account(self):
        print("\n[Test 2] Testing Teacher Account Activation via Token...")
        # Get activation token for Grace Hopper (seeded in init_db)
        token_record = query_db("SELECT token FROM activation_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'grace.hopper@college.edu') AND is_used = 0", one=True)
        self.assertIsNotNone(token_record)
        token = token_record['token']

        # Activate account
        res = self.client.post(f'/teacher/activate/{token}', data={
            'csrf_token': self.csrf,
            'password': 'NewPassword@2026',
            'confirm_password': 'NewPassword@2026'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"successfully activated", res.data)

        # Check DB that Grace Hopper is now active and token is marked used
        user = query_db("SELECT is_active FROM users WHERE email = 'grace.hopper@college.edu'", one=True)
        self.assertEqual(user['is_active'], 1)
        used_token = query_db("SELECT is_used FROM activation_tokens WHERE token = ?", (token,), one=True)
        self.assertEqual(used_token['is_used'], 1)
        print("  -> Passed: Account activated and password updated securely.")

    # -------------------------------------------------------------
    # Scenario 3: Teacher logs in successfully
    # -------------------------------------------------------------
    def test_03_teacher_logs_in_successfully(self):
        print("\n[Test 3] Testing Teacher Successful Login...")
        res = self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome, Prof. Alan Turing!", res.data)
        self.assertIn(b"Teacher Dashboard", res.data)
        self.logout()
        print("  -> Passed: Teacher authenticated and redirected to Teacher Dashboard.")

    # -------------------------------------------------------------
    # Scenario 4: Incorrect credentials are rejected
    # -------------------------------------------------------------
    def test_04_incorrect_credentials_rejected(self):
        print("\n[Test 4] Testing Incorrect Credentials Rejection...")
        res = self.login('alan.turing@college.edu', 'WrongPassword!123', role='teacher')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid email or password", res.data)
        print("  -> Passed: Invalid credentials securely rejected.")

    # -------------------------------------------------------------
    # Scenario 5: Inactive accounts are blocked
    # -------------------------------------------------------------
    def test_05_inactive_accounts_blocked(self):
        print("\n[Test 5] Testing Inactive Teacher Account Blocked from Login...")
        # Admin deactivates Alan Turing temporarily
        self.login('admin@college.edu', 'Admin@123', role='admin')
        teacher = query_db("SELECT id FROM teachers WHERE employee_id = 'EMP101'", one=True)
        self.client.post(f'/admin/teachers/{teacher["id"]}/toggle-status', data={'csrf_token': self.csrf}, follow_redirects=True)
        self.logout()

        # Alan Turing tries to log in
        res = self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')
        self.assertIn(b"inactive or pending activation", res.data)

        # Restore Alan Turing active status
        self.login('admin@college.edu', 'Admin@123', role='admin')
        self.client.post(f'/admin/teachers/{teacher["id"]}/toggle-status', data={'csrf_token': self.csrf}, follow_redirects=True)
        self.logout()
        print("  -> Passed: Inactive teacher account successfully blocked.")

    # -------------------------------------------------------------
    # Scenario 6: Teacher sees only assigned subjects
    # -------------------------------------------------------------
    def test_06_teacher_sees_only_assigned_subjects(self):
        print("\n[Test 6] Testing Teacher Sees Only Assigned Subjects...")
        # Alan Turing has CS501 and CS503, but NOT CS502 (assigned to Ada Lovelace)
        self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')
        res = self.client.get('/teacher/dashboard')
        self.assertIn(b"CS501", res.data)
        self.assertIn(b"CS503", res.data)
        self.assertNotIn(b"CS502", res.data)
        self.logout()
        print("  -> Passed: 'My Subjects' shows strictly assigned courses.")

    # -------------------------------------------------------------
    # Scenario 7: Teacher publishes an assignment
    # -------------------------------------------------------------
    def test_07_teacher_publishes_assignment(self):
        print("\n[Test 7] Testing Teacher Assignment Creation...")
        self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')
        sample_file = (io.BytesIO(b"Assignment 2 Instructions content"), "instructions.pdf")
        res = self.client.post('/teacher/subject/1/assignment/create', data={
            'csrf_token': self.csrf,
            'title': 'Assignment 2: Cloud Load Balancing Lab',
            'description': 'Configure an Application Load Balancer across two EC2 instances.',
            'deadline': '2026-11-01T23:59',
            'max_marks': '100',
            'allowed_extensions': 'pdf,doc,docx,zip',
            'max_file_size_mb': '10',
            'attachment': sample_file
        }, content_type='multipart/form-data', follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Assignment 2: Cloud Load Balancing Lab", res.data)
        self.assertIn(b"successfully published", res.data)

        # Verify DB
        created_a = query_db("SELECT id FROM assignments WHERE title = 'Assignment 2: Cloud Load Balancing Lab'", one=True)
        self.assertIsNotNone(created_a)
        self.logout()
        print("  -> Passed: Assignment published successfully.")

    # -------------------------------------------------------------
    # Scenario 8: Eligible students can see the assignment
    # -------------------------------------------------------------
    def test_08_eligible_students_see_assignment(self):
        print("\n[Test 8] Testing Eligible Student Assignment Visibility...")
        # John Doe (CSE Sem 5) is eligible for CS501 (CSE Sem 5)
        self.login('john.doe@student.college.edu', 'Student@123', role='student')
        res = self.client.get('/student/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Assignment 2: Cloud Load Balancing Lab", res.data)
        self.logout()

        # Emily Davis (IT Sem 5) is NOT eligible for CS501
        self.login('emily.davis@student.college.edu', 'Student@123', role='student')
        res = self.client.get('/student/dashboard')
        self.assertNotIn(b"Assignment 2: Cloud Load Balancing Lab", res.data)
        self.logout()
        print("  -> Passed: Automatic eligibility by department & semester working perfectly.")

    # -------------------------------------------------------------
    # Scenario 9: Teacher sees submitted and non-submitted students
    # -------------------------------------------------------------
    def test_09_roster_tracking_submitted_and_pending(self):
        print("\n[Test 9] Testing Student Submission Tracking with Roster Comparison...")
        self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')
        res = self.client.get('/teacher/assignment/1/submissions')
        self.assertEqual(res.status_code, 200)

        # Total eligible CSE Sem 5 students: John Doe, Jane Smith, Robert Johnson (3 students)
        self.assertIn(b"John Doe", res.data)
        self.assertIn(b"Jane Smith", res.data)
        self.assertIn(b"Robert Johnson", res.data)

        # John Doe has submitted
        self.assertIn(b"badge-submitted", res.data)
        # Jane Smith has not submitted -> Pending
        self.assertIn(b"badge-pending", res.data)
        self.logout()
        print("  -> Passed: Both submitted and pending roster members displayed.")

    # -------------------------------------------------------------
    # Scenario 10: Teacher downloads authorized files and provides grades
    # -------------------------------------------------------------
    def test_10_teacher_downloads_file_and_grades(self):
        print("\n[Test 10] Testing Teacher File Download and Grading...")
        self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')
        # Download submission 1 (John Doe)
        dl_res = self.client.get('/teacher/download/submission/1')
        self.assertEqual(dl_res.status_code, 200)

        # Grade submission 1
        grade_res = self.client.post('/teacher/submission/1/grade', data={
            'csrf_token': self.csrf,
            'grade': '98.5',
            'feedback': 'Terrific implementation! Clean diagram.'
        }, follow_redirects=True)
        self.assertEqual(grade_res.status_code, 200)
        self.assertIn(b"Grade and feedback saved successfully", grade_res.data)

        # Verify DB
        sub = query_db("SELECT grade, feedback FROM submissions WHERE id = 1", one=True)
        self.assertEqual(sub['grade'], 98.5)
        self.assertIn("Terrific implementation", sub['feedback'])
        self.logout()
        print("  -> Passed: File downloaded and grade saved.")

    # -------------------------------------------------------------
    # Scenario 11: Student accounts cannot access teacher routes (403)
    # -------------------------------------------------------------
    def test_11_student_blocked_from_teacher_routes(self):
        print("\n[Test 11] Testing Role Authorization: Student Blocked from Teacher Routes...")
        self.login('john.doe@student.college.edu', 'Student@123', role='student')
        res = self.client.get('/teacher/dashboard')
        self.assertEqual(res.status_code, 403)
        self.assertIn(b"Access Forbidden", res.data)
        self.logout()
        print("  -> Passed: Student blocked from teacher dashboard with 403 Forbidden.")

    # -------------------------------------------------------------
    # Scenario 12: Teacher cannot access another teacher's assignments (IDOR / 403)
    # -------------------------------------------------------------
    def test_12_teacher_cannot_access_other_teacher_assignments(self):
        print("\n[Test 12] Testing IDOR Defense: Teacher Cannot Access Other Teacher's Assignment...")
        # Ada Lovelace tries to view or grade Alan Turing's Assignment 1
        self.login('ada.lovelace@college.edu', 'Teacher@123', role='teacher')
        res = self.client.get('/teacher/assignment/1/submissions')
        self.assertEqual(res.status_code, 403)
        self.assertIn(b"Access Forbidden", res.data)
        self.logout()
    # -------------------------------------------------------------
    # Scenario 13: Subject Details Page with assignments and empty assignment state
    # -------------------------------------------------------------
    def test_13_subject_details_page_rendering(self):
        print("\n[Test 13] Testing Subject Details Page (with and without assignments)...")
        self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')
        
        # 1. Subject with assignments (CS501 - id 1)
        res = self.client.get('/teacher/subject/1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"CS501", res.data)
        self.assertIn(b"Cloud Computing &amp; Distributed Systems", res.data)
        self.assertIn(b"Create Assignment", res.data)
        self.assertIn(b"Teacher Dashboard", res.data)
        self.assertIn(b"Assignments (", res.data)
        self.assertIn(b"View Submissions & Grade", res.data)

        # 2. Subject without assignments
        # Create a new subject assigned to Turing with 0 assignments
        from database import execute_db
        sub_id = execute_db(
            "INSERT INTO subjects (subject_code, subject_name, department, semester, credits) VALUES ('CS509', 'Quantum Computing', 'Computer Science', 5, 3)"
        )
        turing_user = query_db("SELECT id FROM users WHERE email = 'alan.turing@college.edu'", one=True)
        turing_rec = query_db("SELECT id FROM teachers WHERE user_id = ?", (turing_user['id'],), one=True)
        execute_db("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)", (turing_rec['id'], sub_id))

        res_empty = self.client.get(f'/teacher/subject/{sub_id}')
        self.assertEqual(res_empty.status_code, 200)
        self.assertIn(b"CS509", res_empty.data)
        self.assertIn(b"No Assignments Posted Yet", res_empty.data)
        self.assertIn(b"Create First Assignment", res_empty.data)

        self.logout()
        print("  -> Passed: Subject details renders cleanly with assignments and with empty state.")

    # -------------------------------------------------------------
    # Scenario 14: View Submissions with submissions, zero submissions & pending roster
    # -------------------------------------------------------------
    def test_14_view_submissions_page_rendering(self):
        print("\n[Test 14] Testing View Submissions Page (with and without submissions)...")
        self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')

        # 1. Assignment with submissions (Assignment 1)
        res = self.client.get('/teacher/assignment/1/submissions')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Submissions Tracking", res.data)
        self.assertIn(b"Eligible Students", res.data)
        self.assertIn(b"Turn-in Rate", res.data)
        self.assertIn(b"John Doe", res.data)
        self.assertIn(b"Jane Smith", res.data)
        self.assertIn(b"badge-submitted", res.data)
        self.assertIn(b"badge-pending", res.data)
        self.assertIn(b"gradeModal", res.data)
        self.assertIn(b"Save Grade & Feedback", res.data)

        # 2. Assignment with ZERO submissions (Assignment 2 created in test_07)
        a2 = query_db("SELECT id FROM assignments WHERE title = 'Assignment 2: Cloud Load Balancing Lab'", one=True)
        if a2:
            a2_id = a2['id']
            res_zero = self.client.get(f'/teacher/assignment/{a2_id}/submissions')
            self.assertEqual(res_zero.status_code, 200)
            self.assertIn(b"0%", res_zero.data)  # Turn-in rate 0%
            self.assertIn(b"Awaiting Upload", res_zero.data)

        self.logout()
        print("  -> Passed: Submissions tracking works with submissions and with zero submissions.")

    # -------------------------------------------------------------
    # Scenario 15: Unauthorized Access (403) and Invalid IDs (404)
    # -------------------------------------------------------------
    def test_15_unauthorized_access_and_invalid_ids(self):
        print("\n[Test 15] Testing Unauthorized Access (403) and Invalid IDs (404)...")
        # Login as Alan Turing
        self.login('alan.turing@college.edu', 'Teacher@123', role='teacher')

        # Unauthorized subject: CS502 (id 2) is assigned to Ada Lovelace, not Alan Turing -> 403
        res_unauth_sub = self.client.get('/teacher/subject/2')
        self.assertEqual(res_unauth_sub.status_code, 403)

        # Invalid subject: Subject 99999 does not exist in the database -> 404
        res_invalid_sub = self.client.get('/teacher/subject/99999')
        self.assertEqual(res_invalid_sub.status_code, 404)

        # Invalid assignment: Assignment 99999 does not exist in the database -> 404
        res_invalid_assign = self.client.get('/teacher/assignment/99999/submissions')
        self.assertEqual(res_invalid_assign.status_code, 404)

        self.logout()

        # Login as Ada Lovelace
        self.login('ada.lovelace@college.edu', 'Teacher@123', role='teacher')

        # Unauthorized assignment: Assignment 1 belongs to Alan Turing, not Ada Lovelace -> 403
        res_unauth_assign = self.client.get('/teacher/assignment/1/submissions')
        self.assertEqual(res_unauth_assign.status_code, 403)

        self.logout()
        print("  -> Passed: 403 returned for unauthorized access; 404 returned for invalid subject/assignment IDs.")

    # -------------------------------------------------------------
    # Scenario 16: Admin Deletes a Teacher
    # -------------------------------------------------------------
    def test_16_admin_deletes_teacher(self):
        print("\n[Test 16] Testing Admin Teacher Deletion...")
        # Check non-admin blocked (e.g. student)
        self.login('john.doe@student.college.edu', 'Student@123', role='student')
        res_blocked = self.client.post('/admin/teachers/1/delete', data={'csrf_token': self.csrf}, follow_redirects=True)
        self.assertIn(res_blocked.status_code, [401, 403])
        self.logout()

        # Login as Admin
        self.login('admin@college.edu', 'Admin@123', role='admin')

        # First verify teacher Richard Feynman from Test 1 exists
        teacher = query_db("SELECT id, user_id FROM teachers WHERE employee_id = 'EMP109'", one=True)
        self.assertIsNotNone(teacher)
        teacher_id = teacher['id']
        user_id = teacher['user_id']

        # Delete teacher
        res = self.client.post(f'/admin/teachers/{teacher_id}/delete', data={'csrf_token': self.csrf}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"was successfully deleted", res.data)

        # Verify teacher record and user record are removed
        deleted_teacher = query_db("SELECT id FROM teachers WHERE id = ?", (teacher_id,), one=True)
        self.assertIsNone(deleted_teacher)

        deleted_user = query_db("SELECT id FROM users WHERE id = ?", (user_id,), one=True)
        self.assertIsNone(deleted_user)

        # Verify allocations for that teacher are also deleted
        allocations = query_db("SELECT id FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
        self.assertEqual(len(allocations), 0)

        self.logout()
        print("  -> Passed: Teacher and associated user account/allocations deleted cleanly.")

    # -------------------------------------------------------------
    # Scenario 17: Admin Deletes an Unwanted Subject
    # -------------------------------------------------------------
    def test_17_admin_deletes_subject(self):
        print("\n[Test 17] Testing Admin Subject Deletion...")
        # Login as Admin
        self.login('admin@college.edu', 'Admin@123', role='admin')

        # Create a temporary subject to delete
        self.client.post('/admin/subjects', data={
            'csrf_token': self.csrf,
            'subject_code': 'TEMP999',
            'subject_name': 'Obsolete Subject',
            'department': 'Computer Science',
            'semester': '6',
            'credits': '3'
        }, follow_redirects=True)

        subject = query_db("SELECT id, subject_code FROM subjects WHERE subject_code = 'TEMP999'", one=True)
        self.assertIsNotNone(subject)
        subject_id = subject['id']

        # Delete the subject
        res = self.client.post(f'/admin/subjects/{subject_id}/delete', data={'csrf_token': self.csrf}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"was successfully deleted", res.data)

        # Verify subject is gone
        deleted_subject = query_db("SELECT id FROM subjects WHERE id = ?", (subject_id,), one=True)
        self.assertIsNone(deleted_subject)

        self.logout()
        print("  -> Passed: Unwanted subject deleted cleanly.")

if __name__ == '__main__':
    unittest.main(verbosity=2)


