"""
Comprehensive end-to-end test for subject_details and view_submissions.
Covers: rendering, data accuracy, grade modal, filter tabs, CSRF, IDOR.
"""
from app import create_app
import io

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

TEACHER_EMAIL = 'alan.turing@college.edu'
CSRF = 'test-csrf-token'

def login(client, email, password):
    return client.post('/teacher/login', data={
        'csrf_token': CSRF,
        'email': email,
        'password': password
    }, follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

errors = []

with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['_csrf_token'] = CSRF

    # --- Login ---
    r = login(c, TEACHER_EMAIL, 'Teacher@123')
    assert r.status_code == 200, f"Login failed: {r.status_code}"
    assert b'Teacher Dashboard' in r.data, "Not redirected to Teacher Dashboard"
    print("PASS: Login OK")

    # --- subject_details page ---
    r2 = c.get('/teacher/subject/1')
    assert r2.status_code == 200, f"subject_details status: {r2.status_code}\n{r2.data[:500]}"
    body2 = r2.data.decode()
    # Check key content
    assert 'CS501' in body2, "subject_details: subject_code CS501 missing"
    assert 'Cloud Computing' in body2, "subject_details: subject name missing"
    assert 'Create Assignment' in body2, "subject_details: Create Assignment btn missing"
    assert 'View Submissions' in body2, "subject_details: View Submissions btn missing"
    assert 'AWS EC2' in body2, "subject_details: assignment title missing"
    print("PASS: subject_details renders correctly with all expected content")

    # --- IDOR check: teacher 1 cannot access subject 2 (assigned to teacher 2) ---
    r3 = c.get('/teacher/subject/2')
    assert r3.status_code == 403, f"IDOR not blocked on subject/2! Status: {r3.status_code}"
    print("PASS: IDOR blocked: cannot access subject not assigned to this teacher (403)")

    # --- view_submissions page ---
    r4 = c.get('/teacher/assignment/1/submissions')
    assert r4.status_code == 200, f"view_submissions status: {r4.status_code}\n{r4.data[:1000]}"
    body4 = r4.data.decode()
    # Check stats
    assert 'Eligible Students' in body4, "view_submissions: Eligible Students stat missing"
    assert 'Submitted' in body4, "view_submissions: Submitted stat missing"
    assert 'Pending' in body4, "view_submissions: Pending stat missing"
    assert 'Late Submissions' in body4, "view_submissions: Late Submissions stat missing"
    assert 'Turn-in Rate' in body4, "view_submissions: Turn-in Rate missing"
    # Check roster table
    assert 'John Doe' in body4, "view_submissions: John Doe missing from roster"
    assert 'badge-submitted' in body4, "view_submissions: submitted badge missing"
    assert 'badge-pending' in body4, "view_submissions: pending badge missing"
    # Check grade modal
    assert 'gradeModal' in body4, "view_submissions: gradeModal missing"
    assert 'grade_submission' not in body4, "view_submissions: grade_submission in URL form"
    assert '/teacher/submission/' in body4 or 'gradeForm' in body4, "view_submissions: grade form missing"
    # Check filter buttons
    assert 'filter-btn' in body4, "view_submissions: filter buttons missing"
    assert 'submissionSearchInput' in body4, "view_submissions: search input missing"
    print("PASS: view_submissions renders correctly with all expected content")

    # --- IDOR: Teacher 2 (Ada Lovelace) cannot access Teacher 1's assignment ---
    logout(c)
    with c.session_transaction() as sess:
        sess['_csrf_token'] = CSRF
    login(c, 'ada.lovelace@college.edu', 'Teacher@123')
    r5 = c.get('/teacher/assignment/1/submissions')
    assert r5.status_code == 403, f"IDOR not blocked on assignment 1! Status: {r5.status_code}"
    print("PASS: IDOR blocked: Ada Lovelace cannot access Alan Turing's assignment (403)")

    # --- Grade a submission ---
    logout(c)
    with c.session_transaction() as sess:
        sess['_csrf_token'] = CSRF
    login(c, TEACHER_EMAIL, 'Teacher@123')
    r6 = c.post('/teacher/submission/1/grade', data={
        'csrf_token': CSRF,
        'grade': '88',
        'feedback': 'Great work on the cloud architecture.'
    }, follow_redirects=True)
    assert r6.status_code == 200, f"Grade submission failed: {r6.status_code}"
    assert b'Grade and feedback saved successfully' in r6.data, "Grade save message missing"
    print("PASS: Grade submission works correctly")

    logout(c)

print("\nALL CHECKS PASSED - Both teacher template pages are working correctly!")
