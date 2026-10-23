"""
Deep investigation script: Hits the LIVE running Flask server at port 5000,
logs in as teacher, and fetches both pages to check for actual errors.
Also checks for subtle template issues that may render but produce wrong content.
"""
import requests

BASE = "http://127.0.0.1:5000"
session = requests.Session()

# Step 1: Login as teacher
print("=== Step 1: Login as Teacher ===")
# Get login page first (for CSRF token if needed)
login_page = session.get(f"{BASE}/teacher/login")
print(f"  GET /teacher/login -> {login_page.status_code}")

# Extract CSRF token from the login form
import re
csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else ''
print(f"  CSRF token found: {bool(csrf_token)}")

# Post login
login_resp = session.post(f"{BASE}/teacher/login", data={
    'csrf_token': csrf_token,
    'email': 'alan.turing@college.edu',
    'password': 'Teacher@123'
}, allow_redirects=True)
print(f"  POST /teacher/login -> {login_resp.status_code} (final URL: {login_resp.url})")
if 'Teacher Dashboard' in login_resp.text:
    print("  Login SUCCESS - Teacher Dashboard loaded")
else:
    print("  Login ISSUE - checking content...")
    print(f"  Content snippet: {login_resp.text[:500]}")

# Step 2: Test subject_details page
print("\n=== Step 2: Subject Details Page ===")
sd_resp = session.get(f"{BASE}/teacher/subject/1")
print(f"  GET /teacher/subject/1 -> {sd_resp.status_code}")
if sd_resp.status_code == 200:
    body = sd_resp.text
    # Check for error indicators
    if 'Internal Server Error' in body or 'Traceback' in body:
        print("  ERROR: Server error found in page!")
        # Extract error
        err_match = re.search(r'<pre[^>]*>(.*?)</pre>', body, re.DOTALL)
        if err_match:
            print(f"  Error details: {err_match.group(1)[:1000]}")
    elif 'jinja2' in body.lower() or 'UndefinedError' in body:
        print("  ERROR: Jinja2 template error found!")
    elif 'TemplateSyntaxError' in body:
        print("  ERROR: Template syntax error!")
    else:
        # Check for expected content
        checks = {
            'CS501': 'subject_code' in body or 'CS501' in body,
            'subject_name': 'Cloud Computing' in body,
            'assignments_list': 'Assignments' in body,
            'create_assignment_btn': 'Create Assignment' in body,
            'breadcrumb': 'breadcrumb' in body,
        }
        all_pass = True
        for name, passed in checks.items():
            status = "OK" if passed else "MISSING"
            if not passed:
                all_pass = False
            print(f"  Check '{name}': {status}")
        if all_pass:
            print("  Subject Details page: ALL CHECKS PASSED")
else:
    print(f"  ERROR: Unexpected status code {sd_resp.status_code}")
    print(f"  Content: {sd_resp.text[:1000]}")

# Step 3: Test view_submissions page
print("\n=== Step 3: View Submissions Page ===")
vs_resp = session.get(f"{BASE}/teacher/assignment/1/submissions")
print(f"  GET /teacher/assignment/1/submissions -> {vs_resp.status_code}")
if vs_resp.status_code == 200:
    body = vs_resp.text
    if 'Internal Server Error' in body or 'Traceback' in body:
        print("  ERROR: Server error found in page!")
        err_match = re.search(r'<pre[^>]*>(.*?)</pre>', body, re.DOTALL)
        if err_match:
            print(f"  Error details: {err_match.group(1)[:1000]}")
    elif 'jinja2' in body.lower() or 'UndefinedError' in body:
        print("  ERROR: Jinja2 template error found!")
    elif 'TemplateSyntaxError' in body:
        print("  ERROR: Template syntax error!")
    else:
        checks = {
            'assignment_title': 'AWS EC2' in body,
            'stats_eligible': 'Eligible Students' in body,
            'stats_submitted': 'Submitted' in body,
            'stats_pending': 'Pending' in body,
            'stats_late': 'Late Submissions' in body,
            'roster_table': 'submissionsTable' in body,
            'grade_modal': 'gradeModal' in body,
            'filter_buttons': 'filter-btn' in body,
            'search_input': 'submissionSearchInput' in body,
            'john_doe': 'John Doe' in body,
            'badge_submitted': 'badge-submitted' in body,
            'badge_pending': 'badge-pending' in body,
        }
        all_pass = True
        for name, passed in checks.items():
            status = "OK" if passed else "MISSING"
            if not passed:
                all_pass = False
            print(f"  Check '{name}': {status}")
        if all_pass:
            print("  View Submissions page: ALL CHECKS PASSED")
else:
    print(f"  ERROR: Unexpected status code {vs_resp.status_code}")
    print(f"  Content: {vs_resp.text[:1000]}")

# Step 4: Check for 403 on unauthorized access
print("\n=== Step 4: IDOR Protection ===")
idor_resp = session.get(f"{BASE}/teacher/subject/2")
print(f"  GET /teacher/subject/2 (not assigned) -> {idor_resp.status_code}")

idor_resp2 = session.get(f"{BASE}/teacher/assignment/999/submissions")
print(f"  GET /teacher/assignment/999/submissions (non-existent) -> {idor_resp2.status_code}")

print("\n=== Step 5: Check invalid assignment ===")
inv_resp = session.get(f"{BASE}/teacher/subject/999")
print(f"  GET /teacher/subject/999 (non-existent) -> {inv_resp.status_code}")

print("\nDone.")
