"""
Deep investigation: Uses Flask test client (not requests) but against the
LIVE database to reproduce the user-reported errors in subject_details
and view_submissions templates.
"""
import sys
import traceback

from app import create_app

app = create_app()
app.config['TESTING'] = False  # Keep debug-like behavior to see real tracebacks

CSRF = 'test-csrf'

print("=" * 70)
print("DEEP TEMPLATE INVESTIGATION")
print("=" * 70)

with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['_csrf_token'] = CSRF

    # Login as teacher
    login_resp = c.post('/teacher/login', data={
        'csrf_token': CSRF,
        'email': 'alan.turing@college.edu',
        'password': 'Teacher@123'
    }, follow_redirects=True)
    assert login_resp.status_code == 200, f"Login failed: {login_resp.status_code}"
    body = login_resp.data.decode(errors='replace')
    assert 'Teacher Dashboard' in body, "Not on dashboard after login"
    print("[OK] Login successful")

    # --- Test subject_details ---
    print("\n--- Testing /teacher/subject/1 ---")
    r1 = c.get('/teacher/subject/1')
    b1 = r1.data.decode(errors='replace')
    print(f"Status: {r1.status_code}")

    if r1.status_code == 500:
        print("*** 500 ERROR ***")
        print(b1[:3000])
    elif r1.status_code != 200:
        print(f"*** Unexpected status {r1.status_code} ***")
        print(b1[:2000])
    else:
        # Check for Werkzeug debugger traceback in the rendered HTML
        if 'Traceback' in b1 or 'debugger' in b1.lower():
            print("*** Debugger/Traceback found in 200 response! ***")
            print(b1[:3000])
        else:
            # Validate every expected element
            checks = [
                ('CS501', 'CS501' in b1),
                ('Cloud Computing', 'Cloud Computing' in b1),
                ('Create Assignment', 'Create Assignment' in b1),
                ('breadcrumb', 'breadcrumb' in b1),
                ('submitted_count', 'Submitted' in b1),
                ('eligible_count', 'eligible' in b1.lower()),
                ('View Submissions', 'View Submissions' in b1),
                ('assignment title', 'AWS EC2' in b1),
            ]
            for name, ok in checks:
                print(f"  {'OK' if ok else 'FAIL'}: {name}")

    # --- Test view_submissions ---
    print("\n--- Testing /teacher/assignment/1/submissions ---")
    r2 = c.get('/teacher/assignment/1/submissions')
    b2 = r2.data.decode(errors='replace')
    print(f"Status: {r2.status_code}")

    if r2.status_code == 500:
        print("*** 500 ERROR ***")
        print(b2[:3000])
    elif r2.status_code != 200:
        print(f"*** Unexpected status {r2.status_code} ***")
        print(b2[:2000])
    else:
        if 'Traceback' in b2 or 'debugger' in b2.lower():
            print("*** Debugger/Traceback found in 200 response! ***")
            print(b2[:3000])
        else:
            checks = [
                ('assignment.title', 'AWS EC2' in b2),
                ('assignment.subject_code', 'CS501' in b2),
                ('assignment.subject_dept', 'Computer Science' in b2),
                ('stats.total_eligible', 'Eligible Students' in b2),
                ('stats.submitted_count', 'Submitted' in b2),
                ('stats.pending_count', 'Pending' in b2),
                ('stats.late_count', 'Late' in b2),
                ('stats.submission_percentage', 'Turn-in Rate' in b2),
                ('roster: John Doe', 'John Doe' in b2),
                ('roster: Jane Smith', 'Jane Smith' in b2),
                ('badge-submitted', 'badge-submitted' in b2),
                ('badge-pending', 'badge-pending' in b2),
                ('gradeModal', 'gradeModal' in b2),
                ('gradeForm', 'gradeForm' in b2),
                ('filter-btn', 'filter-btn' in b2),
                ('search input', 'submissionSearchInput' in b2),
                ('csrf_token in modal', 'csrf_token' in b2),
                ('download link', 'download' in b2.lower()),
            ]
            for name, ok in checks:
                print(f"  {'OK' if ok else 'FAIL'}: {name}")

    # --- Test with NO submissions (create empty assignment, check view_submissions) ---
    print("\n--- Testing /teacher/assignment/2/submissions (no submissions) ---")
    r3 = c.get('/teacher/assignment/2/submissions')
    b3 = r3.data.decode(errors='replace')
    print(f"Status: {r3.status_code}")

    if r3.status_code == 200:
        if 'Traceback' in b3 or 'debugger' in b3.lower():
            print("*** Debugger/Traceback found! ***")
            print(b3[:3000])
        else:
            print("  OK: Page rendered without error (assignment with 0 submissions)")
            if '0' in b3:
                print("  OK: Shows 0 counts")
    elif r3.status_code == 500:
        print("*** 500 ERROR on assignment with no submissions ***")
        print(b3[:3000])
    else:
        print(f"  Status: {r3.status_code}")

    # --- Test IDOR ---
    print("\n--- Testing IDOR: /teacher/subject/2 (not assigned) ---")
    r4 = c.get('/teacher/subject/2')
    print(f"Status: {r4.status_code} (expected 403)")

    print("\n--- Testing IDOR: /teacher/assignment/999 (non-existent) ---")
    r5 = c.get('/teacher/assignment/999/submissions')
    print(f"Status: {r5.status_code} (expected 403)")

    # --- Logout ---
    c.get('/logout')

print("\n" + "=" * 70)
print("INVESTIGATION COMPLETE")
print("=" * 70)
