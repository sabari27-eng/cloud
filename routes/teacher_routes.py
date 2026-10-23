import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort, current_app
from database import query_db, execute_db
from auth import teacher_required, validate_csrf
from storage import storage_service

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

@teacher_bp.before_request
@teacher_required
def require_teacher():
    """Ensure user is logged in as teacher and account is active."""
    pass

def get_teacher_profile():
    """Returns the teacher record linked to g.user['id']."""
    teacher = query_db("SELECT id, name, employee_id, department, college, phone FROM teachers WHERE user_id = ?", (g.user['id'],), one=True)
    if not teacher:
        abort(403, description="Teacher profile not found for this account.")
    return teacher

def verify_subject_assigned(teacher_id, subject_id):
    """Verifies that the teacher is authorized/assigned to this subject."""
    subject = query_db("SELECT id FROM subjects WHERE id = ?", (subject_id,), one=True)
    if not subject:
        abort(404, description="Subject not found.")
    allocation = query_db(
        "SELECT id FROM teacher_subjects WHERE teacher_id = ? AND subject_id = ?",
        (teacher_id, subject_id),
        one=True
    )
    if not allocation:
        flash("Unauthorized: You are not assigned to this subject.", "danger")
        abort(403, description="Unauthorized: You are not assigned to this subject.")

def verify_assignment_ownership(teacher_id, assignment_id):
    """Verifies that the assignment belongs to the logged-in teacher."""
    assignment_exists = query_db("SELECT id, teacher_id FROM assignments WHERE id = ?", (assignment_id,), one=True)
    if not assignment_exists:
        abort(404, description="Assignment not found.")

    assignment = query_db(
        """SELECT a.*, s.subject_code, s.subject_name, s.department as subject_dept, s.semester as subject_sem
           FROM assignments a
           JOIN subjects s ON a.subject_id = s.id
           WHERE a.id = ? AND a.teacher_id = ?""",
        (assignment_id, teacher_id),
        one=True
    )
    if not assignment:
        flash("Unauthorized: You do not have permission to view or manage this assignment.", "danger")
        abort(403, description="Unauthorized: You do not have permission to view or manage this assignment.")
    return assignment

@teacher_bp.route('/dashboard')
def dashboard():
    """
    Teacher Dashboard:
    Modern blue-and-white layout showing teacher info, 4 key stats, and 'My Subjects' cards.
    """
    teacher = get_teacher_profile()

    # 1. Assigned Subjects for this teacher
    assigned_subjects = query_db("""
        SELECT s.id, s.subject_code, s.subject_name, s.department, s.semester, s.credits,
               (SELECT COUNT(*) FROM assignments a WHERE a.subject_id = s.id AND a.teacher_id = ?) as assignments_count
        FROM subjects s
        JOIN teacher_subjects ts ON s.id = ts.subject_id
        WHERE ts.teacher_id = ?
        ORDER BY s.department, s.semester, s.subject_code
    """, (teacher['id'], teacher['id']))

    # 2. Total Assignments Posted by this teacher
    assignments_stat = query_db(
        "SELECT COUNT(*) as count FROM assignments WHERE teacher_id = ?",
        (teacher['id'],),
        one=True
    )
    total_assignments = assignments_stat['count'] if assignments_stat else 0

    # 3. Total Student Submissions for assignments posted by this teacher
    submissions_stat = query_db("""
        SELECT COUNT(sub.id) as count
        FROM submissions sub
        JOIN assignments a ON sub.assignment_id = a.id
        WHERE a.teacher_id = ?
    """, (teacher['id'],), one=True)
    total_submissions = submissions_stat['count'] if submissions_stat else 0

    # 4. Total Pending Submissions across all assignments posted by this teacher
    # For each assignment: count eligible students - count submitted students
    total_pending = 0
    all_teacher_assignments = query_db("""
        SELECT a.id, s.department, s.semester
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.teacher_id = ?
    """, (teacher['id'],))

    for a in all_teacher_assignments:
        eligible_count = query_db(
            "SELECT COUNT(*) as c FROM students WHERE department = ? AND semester = ?",
            (a['department'], a['semester']),
            one=True
        )['c']
        submitted_count = query_db(
            "SELECT COUNT(DISTINCT student_id) as c FROM submissions WHERE assignment_id = ?",
            (a['id'],),
            one=True
        )['c']
        pending_for_assignment = max(0, eligible_count - submitted_count)
        total_pending += pending_for_assignment

    stats = {
        'assigned_subjects_count': len(assigned_subjects),
        'total_assignments': total_assignments,
        'total_submissions': total_submissions,
        'total_pending': total_pending
    }

    # Fetch recent assignments
    recent_assignments = query_db("""
        SELECT a.id, a.title, a.created_at, a.deadline, s.subject_code, s.subject_name,
               (SELECT COUNT(*) FROM submissions sub WHERE sub.assignment_id = a.id) as sub_count
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.teacher_id = ?
        ORDER BY a.created_at DESC
        LIMIT 5
    """, (teacher['id'],))

    return render_template(
        'teacher/dashboard.html',
        teacher=teacher,
        stats=stats,
        subjects=assigned_subjects,
        recent_assignments=recent_assignments
    )

@teacher_bp.route('/subject/<int:subject_id>')
def subject_details(subject_id):
    """
    View assigned subject details and its posted assignments.
    """
    teacher = get_teacher_profile()
    verify_subject_assigned(teacher['id'], subject_id)

    subject_raw = query_db("SELECT * FROM subjects WHERE id = ?", (subject_id,), one=True)
    if not subject_raw:
        abort(404, description="Subject not found.")
    subject = dict(subject_raw)

    # Assignments created by this teacher for this subject
    assignments_raw = query_db("""
        SELECT a.*,
               (SELECT COUNT(DISTINCT student_id) FROM submissions sub WHERE sub.assignment_id = a.id) as submitted_count,
               (SELECT COUNT(*) FROM students st JOIN users u ON st.user_id = u.id WHERE st.department = ? AND st.semester = ? AND u.is_active = 1) as eligible_count
        FROM assignments a
        WHERE a.subject_id = ? AND a.teacher_id = ?
        ORDER BY a.created_at DESC
    """, (subject['department'], subject['semester'], subject_id, teacher['id']))

    assignments = [dict(a) for a in assignments_raw]

    return render_template('teacher/subject_details.html', teacher=teacher, subject=subject, assignments=assignments)

@teacher_bp.route('/subject/<int:subject_id>/assignment/create', methods=['GET', 'POST'])
def create_assignment(subject_id):
    """
    Create Assignment form within an assigned subject.
    Validates deadline, allowed extensions, and file sizes.
    """
    teacher = get_teacher_profile()
    verify_subject_assigned(teacher['id'], subject_id)

    subject = query_db("SELECT * FROM subjects WHERE id = ?", (subject_id,), one=True)

    if request.method == 'POST':
        validate_csrf()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        deadline_str = request.form.get('deadline', '').strip()
        max_marks = request.form.get('max_marks', '100').strip()
        allowed_extensions = request.form.get('allowed_extensions', 'pdf,doc,docx,zip').strip().lower()
        max_file_size_mb = request.form.get('max_file_size_mb', '10').strip()
        attachment_file = request.files.get('attachment')

        # Validations
        if not title:
            flash("Assignment title is required.", "danger")
            return render_template('teacher/create_assignment.html', subject=subject, **request.form)

        if not deadline_str:
            flash("Submission deadline is required.", "danger")
            return render_template('teacher/create_assignment.html', subject=subject, **request.form)

        try:
            # HTML datetime-local format: YYYY-MM-DDTHH:MM
            deadline_clean = deadline_str.replace('T', ' ')
            if len(deadline_clean) == 16:
                deadline_clean += ":00"
            deadline_dt = datetime.strptime(deadline_clean, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            flash("Invalid deadline date and time format.", "danger")
            return render_template('teacher/create_assignment.html', subject=subject, **request.form)

        # File attachment handling (optional)
        attachment_orig_filename = None
        attachment_path = None
        if attachment_file and attachment_file.filename:
            if not storage_service.is_allowed_file(attachment_file.filename):
                flash("Uploaded reference attachment file type is not allowed.", "danger")
                return render_template('teacher/create_assignment.html', subject=subject, **request.form)
            attachment_orig_filename, _, attachment_path = storage_service.save_file(attachment_file, target_type='assignments')

        # Insert assignment record
        assignment_id = execute_db("""
            INSERT INTO assignments (
                subject_id, teacher_id, title, description, attachment_filename, attachment_path,
                max_marks, allowed_extensions, max_file_size_mb, deadline, is_published
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            subject_id,
            teacher['id'],
            title,
            description,
            attachment_orig_filename,
            attachment_path,
            int(max_marks) if max_marks.isdigit() else 100,
            allowed_extensions,
            int(max_file_size_mb) if max_file_size_mb.isdigit() else 10,
            deadline_clean
        ))

        flash(f"Assignment '{title}' has been successfully published! It is now visible to all eligible students.", "success")
        return redirect(url_for('teacher.subject_details', subject_id=subject_id))

    return render_template('teacher/create_assignment.html', subject=subject)

@teacher_bp.route('/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
def edit_assignment(assignment_id):
    """Edit assignment details."""
    teacher = get_teacher_profile()
    assignment = verify_assignment_ownership(teacher['id'], assignment_id)

    if request.method == 'POST':
        validate_csrf()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        deadline_str = request.form.get('deadline', '').strip()
        max_marks = request.form.get('max_marks', '100').strip()
        allowed_extensions = request.form.get('allowed_extensions', 'pdf,doc,docx,zip').strip().lower()
        max_file_size_mb = request.form.get('max_file_size_mb', '10').strip()
        attachment_file = request.files.get('attachment')

        if not title or not deadline_str:
            flash("Title and deadline are required.", "danger")
            return render_template('teacher/edit_assignment.html', assignment=assignment)

        deadline_clean = deadline_str.replace('T', ' ')
        if len(deadline_clean) == 16:
            deadline_clean += ":00"

        attachment_orig_filename = assignment['attachment_filename']
        attachment_path = assignment['attachment_path']

        if attachment_file and attachment_file.filename:
            if not storage_service.is_allowed_file(attachment_file.filename):
                flash("Invalid attachment file type.", "danger")
                return render_template('teacher/edit_assignment.html', assignment=assignment)
            attachment_orig_filename, _, attachment_path = storage_service.save_file(attachment_file, target_type='assignments')

        execute_db("""
            UPDATE assignments SET
                title = ?, description = ?, deadline = ?, max_marks = ?,
                allowed_extensions = ?, max_file_size_mb = ?,
                attachment_filename = ?, attachment_path = ?
            WHERE id = ?
        """, (
            title, description, deadline_clean,
            int(max_marks) if max_marks.isdigit() else 100,
            allowed_extensions,
            int(max_file_size_mb) if max_file_size_mb.isdigit() else 10,
            attachment_orig_filename, attachment_path,
            assignment_id
        ))

        flash("Assignment updated successfully.", "success")
        return redirect(url_for('teacher.subject_details', subject_id=assignment['subject_id']))

    return render_template('teacher/edit_assignment.html', assignment=assignment)

@teacher_bp.route('/assignment/<int:assignment_id>/submissions')
def view_submissions(assignment_id):
    """
    Student Submission Tracking:
    Displays stats (eligible students, submitted, pending, late, percentage)
    and full roster comparison table including non-submitted students.
    """
    teacher = get_teacher_profile()
    assignment = dict(verify_assignment_ownership(teacher['id'], assignment_id))

    # 1. Fetch all eligible students whose department and semester match the subject
    eligible_students = query_db("""
        SELECT s.id as student_id, s.register_no, s.name as student_name, s.department, s.semester, s.class_section,
               u.email as student_email
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.department = ? AND s.semester = ? AND u.is_active = 1
        ORDER BY s.register_no ASC
    """, (assignment['subject_dept'], assignment['subject_sem']))

    # 2. Fetch all submissions for this assignment
    submissions_raw = query_db("""
        SELECT sub.id as submission_id, sub.student_id, sub.file_filename, sub.file_path,
               sub.submitted_at, sub.is_late, sub.grade, sub.feedback, sub.graded_at
        FROM submissions sub
        WHERE sub.assignment_id = ?
    """, (assignment_id,))

    submissions_map = {row['student_id']: dict(row) for row in submissions_raw}

    # 3. Build unified tracking roster
    roster = []
    seen_student_ids = set()

    for student in eligible_students:
        s_id = student['student_id']
        seen_student_ids.add(s_id)
        sub = submissions_map.get(s_id)
        if sub:
            # Check if late
            is_late = bool(sub.get('is_late', 0))
            if not is_late and sub.get('submitted_at') and assignment.get('deadline'):
                try:
                    clean_sub = str(sub['submitted_at']).replace('T', ' ').split('.')[0].strip()
                    clean_dl = str(assignment['deadline']).replace('T', ' ').split('.')[0].strip()
                    if len(clean_sub) == 16: clean_sub += ":00"
                    if len(clean_dl) == 16: clean_dl += ":00"
                    sub_time = datetime.strptime(clean_sub, "%Y-%m-%d %H:%M:%S")
                    dl_time = datetime.strptime(clean_dl, "%Y-%m-%d %H:%M:%S")
                    if sub_time > dl_time:
                        is_late = True
                except Exception:
                    pass

            status = 'Late' if is_late else 'Submitted'

            item = {
                'student_id': s_id,
                'register_no': student['register_no'],
                'student_name': student['student_name'],
                'student_email': student['student_email'],
                'class_section': student['class_section'],
                'status': status,
                'submission_id': sub['submission_id'],
                'file_filename': sub['file_filename'],
                'file_path': sub['file_path'],
                'submitted_at': sub['submitted_at'],
                'grade': sub['grade'],
                'feedback': sub['feedback'],
                'graded_at': sub['graded_at']
            }
        else:
            item = {
                'student_id': s_id,
                'register_no': student['register_no'],
                'student_name': student['student_name'],
                'student_email': student['student_email'],
                'class_section': student['class_section'],
                'status': 'Pending',
                'submission_id': None,
                'file_filename': None,
                'file_path': None,
                'submitted_at': None,
                'grade': None,
                'feedback': None,
                'graded_at': None
            }
        roster.append(item)

    # In case any submitted student is not in eligible_students list, include them
    for s_id, sub in submissions_map.items():
        if s_id not in seen_student_ids:
            st = query_db("""
                SELECT s.id as student_id, s.register_no, s.name as student_name, s.department, s.semester, s.class_section,
                       u.email as student_email
                FROM students s
                JOIN users u ON s.user_id = u.id
                WHERE s.id = ?
            """, (s_id,), one=True)
            if st:
                seen_student_ids.add(s_id)
                is_late = bool(sub.get('is_late', 0))
                status = 'Late' if is_late else 'Submitted'
                roster.append({
                    'student_id': s_id,
                    'register_no': st['register_no'],
                    'student_name': st['student_name'],
                    'student_email': st['student_email'],
                    'class_section': st['class_section'],
                    'status': status,
                    'submission_id': sub['submission_id'],
                    'file_filename': sub['file_filename'],
                    'file_path': sub['file_path'],
                    'submitted_at': sub['submitted_at'],
                    'grade': sub['grade'],
                    'feedback': sub['feedback'],
                    'graded_at': sub['graded_at']
                })

    total_eligible = len(roster)
    submitted_count = sum(1 for item in roster if item['submission_id'] is not None)
    late_count = sum(1 for item in roster if item['status'] == 'Late')
    pending_count = sum(1 for item in roster if item['submission_id'] is None)
    submission_percentage = round((submitted_count / total_eligible * 100), 1) if total_eligible > 0 else 0.0

    stats = {
        'total_eligible': total_eligible,
        'submitted_count': submitted_count,
        'pending_count': pending_count,
        'late_count': late_count,
        'submission_percentage': submission_percentage
    }

    return render_template(
        'teacher/view_submissions.html',
        assignment=assignment,
        roster=roster,
        stats=stats
    )

@teacher_bp.route('/submission/<int:submission_id>/grade', methods=['POST'])
def grade_submission(submission_id):
    """
    Teacher enters grades and feedback for a student submission.
    """
    validate_csrf()
    teacher = get_teacher_profile()

    # Verify submission belongs to an assignment taught by this teacher
    sub = query_db("""
        SELECT sub.id, sub.assignment_id, a.teacher_id, a.max_marks
        FROM submissions sub
        JOIN assignments a ON sub.assignment_id = a.id
        WHERE sub.id = ?
    """, (submission_id,), one=True)

    if not sub or sub['teacher_id'] != teacher['id']:
        flash("Unauthorized: You cannot grade this submission.", "danger")
        abort(403)

    grade_val = request.form.get('grade', '').strip()
    feedback = request.form.get('feedback', '').strip()

    try:
        grade = float(grade_val) if grade_val else None
        if grade is not None and (grade < 0 or grade > sub['max_marks']):
            flash(f"Grade must be between 0 and {sub['max_marks']}.", "danger")
            return redirect(url_for('teacher.view_submissions', assignment_id=sub['assignment_id']))
    except ValueError:
        flash("Invalid grade value. Please enter a number.", "danger")
        return redirect(url_for('teacher.view_submissions', assignment_id=sub['assignment_id']))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_db("""
        UPDATE submissions
        SET grade = ?, feedback = ?, graded_at = ?, graded_by = ?
        WHERE id = ?
    """, (grade, feedback, now_str, teacher['id'], submission_id))

    flash("Grade and feedback saved successfully!", "success")
    return redirect(url_for('teacher.view_submissions', assignment_id=sub['assignment_id']))

@teacher_bp.route('/download/<file_type>/<int:target_id>')
def download_file(file_type, target_id):
    """
    Teacher file download route.
    file_type: 'attachment' (assignment reference file) or 'submission' (student submitted file)
    Enforces authorization: teacher must own the corresponding assignment.
    """
    teacher = get_teacher_profile()

    if file_type == 'attachment':
        assignment = verify_assignment_ownership(teacher['id'], target_id)
        if not assignment['attachment_path']:
            abort(404, description="No attachment for this assignment.")
        return storage_service.get_file_download_response(assignment['attachment_path'], assignment['attachment_filename'])

    elif file_type == 'submission':
        sub = query_db("""
            SELECT sub.file_path, sub.file_filename, a.teacher_id
            FROM submissions sub
            JOIN assignments a ON sub.assignment_id = a.id
            WHERE sub.id = ?
        """, (target_id,), one=True)
        if not sub or sub['teacher_id'] != teacher['id']:
            flash("Unauthorized file access.", "danger")
            abort(403)
        return storage_service.get_file_download_response(sub['file_path'], sub['file_filename'])

    else:
        abort(400, description="Invalid download type.")
