import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort
from database import query_db, execute_db
from auth import student_required, validate_csrf
from storage import storage_service

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.before_request
@student_required
def require_student():
    """Ensure user is logged in as student and account is active."""
    pass

def get_student_profile():
    student = query_db(
        "SELECT id, user_id, register_no, name, college, department, semester, class_section, phone FROM students WHERE user_id = ?",
        (g.user['id'],),
        one=True
    )
    if not student:
        abort(403, description="Student record not found.")
    return student

@student_bp.route('/dashboard')
def dashboard():
    """
    Student Dashboard:
    Displays enrolled subjects for student's department and semester,
    all assignments posted for these subjects, and student's submission status/grades.
    """
    student = get_student_profile()

    # 1. Subjects enrolled based on department & semester
    enrolled_subjects = query_db("""
        SELECT s.id, s.subject_code, s.subject_name, s.credits,
               (SELECT COUNT(*) FROM assignments a WHERE a.subject_id = s.id AND a.is_published = 1) as assignments_count
        FROM subjects s
        WHERE s.department = ? AND s.semester = ?
        ORDER BY s.subject_code
    """, (student['department'], student['semester']))

    # 2. All assignments for the student's enrolled subjects
    assignments_raw = query_db("""
        SELECT a.id, a.title, a.deadline, a.max_marks, a.created_at,
               s.subject_code, s.subject_name,
               t.name as teacher_name,
               sub.id as submission_id, sub.submitted_at, sub.is_late, sub.grade, sub.feedback
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        JOIN teachers t ON a.teacher_id = t.id
        LEFT JOIN submissions sub ON a.id = sub.assignment_id AND sub.student_id = ?
        WHERE s.department = ? AND s.semester = ? AND a.is_published = 1
        ORDER BY a.deadline ASC
    """, (student['id'], student['department'], student['semester']))

    # Categorize and compute stats
    total_assignments = len(assignments_raw)
    submitted_count = 0
    pending_count = 0
    graded_count = 0

    now = datetime.now()
    assignments_list = []
    for item in assignments_raw:
        row = dict(item)
        if row['submission_id']:
            submitted_count += 1
            if row['grade'] is not None:
                graded_count += 1
            row['status'] = 'Late' if row['is_late'] else 'Submitted'
        else:
            pending_count += 1
            try:
                dl_dt = datetime.fromisoformat(str(row['deadline']))
                row['status'] = 'Overdue' if now > dl_dt else 'Pending'
            except Exception:
                row['status'] = 'Pending'
        assignments_list.append(row)

    stats = {
        'enrolled_subjects_count': len(enrolled_subjects),
        'total_assignments': total_assignments,
        'submitted_count': submitted_count,
        'pending_count': pending_count,
        'graded_count': graded_count
    }

    return render_template(
        'student/dashboard.html',
        student=student,
        stats=stats,
        subjects=enrolled_subjects,
        assignments=assignments_list
    )

@student_bp.route('/assignment/<int:assignment_id>', methods=['GET', 'POST'])
def view_assignment(assignment_id):
    """
    View assignment instructions and submit assignment file.
    """
    student = get_student_profile()

    # Verify assignment is for student's department and semester
    assignment = query_db("""
        SELECT a.*, s.subject_code, s.subject_name, s.department, s.semester, t.name as teacher_name
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        JOIN teachers t ON a.teacher_id = t.id
        WHERE a.id = ? AND s.department = ? AND s.semester = ? AND a.is_published = 1
    """, (assignment_id, student['department'], student['semester']), one=True)

    if not assignment:
        flash("Assignment not found or not eligible for your department and semester.", "danger")
        return redirect(url_for('student.dashboard'))

    # Existing submission by this student
    submission = query_db(
        "SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?",
        (assignment_id, student['id']),
        one=True
    )

    if request.method == 'POST':
        validate_csrf()
        uploaded_file = request.files.get('submission_file')

        if not uploaded_file or uploaded_file.filename == '':
            flash("Please choose a file to submit.", "danger")
            return render_template('student/assignment_view.html', assignment=assignment, submission=submission, student=student)

        # File extension validation
        allowed_exts = assignment['allowed_extensions'] or 'pdf,doc,docx,zip'
        if not storage_service.is_allowed_file(uploaded_file.filename, allowed_extensions=allowed_exts):
            flash(f"Invalid file extension. Allowed formats are: {allowed_exts}", "danger")
            return render_template('student/assignment_view.html', assignment=assignment, submission=submission, student=student)

        # File size validation (convert MB to bytes)
        max_bytes = (assignment['max_file_size_mb'] or 10) * 1024 * 1024
        uploaded_file.seek(0, os.SEEK_END)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)

        if file_size > max_bytes:
            flash(f"File size exceeds maximum limit of {assignment['max_file_size_mb']} MB.", "danger")
            return render_template('student/assignment_view.html', assignment=assignment, submission=submission, student=student)

        # Determine if late
        now = datetime.now()
        is_late = 0
        try:
            dl_dt = datetime.fromisoformat(str(assignment['deadline']))
            if now > dl_dt:
                is_late = 1
        except Exception:
            pass

        # Save file safely
        custom_prefix = f"{student['register_no']}_A{assignment_id}"
        orig_filename, _, stored_path = storage_service.save_file(
            uploaded_file,
            target_type='submissions',
            custom_name=custom_prefix
        )

        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # Save or update submission
        if submission:
            execute_db("""
                UPDATE submissions
                SET file_filename = ?, file_path = ?, submitted_at = ?, is_late = ?
                WHERE id = ?
            """, (orig_filename, stored_path, now_str, is_late, submission['id']))
            flash("Your assignment submission has been successfully updated!", "success")
        else:
            execute_db("""
                INSERT INTO submissions (assignment_id, student_id, file_filename, file_path, submitted_at, is_late)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (assignment_id, student['id'], orig_filename, stored_path, now_str, is_late))
            if is_late:
                flash("Assignment submitted successfully. Note: It was marked as a Late Submission.", "warning")
            else:
                flash("Assignment submitted successfully on time!", "success")

        return redirect(url_for('student.view_assignment', assignment_id=assignment_id))

    return render_template('student/assignment_view.html', assignment=assignment, submission=submission, student=student)

@student_bp.route('/download/<file_type>/<int:target_id>')
def download_file(file_type, target_id):
    """
    Student secure file download.
    Can download teacher's reference attachment or student's own submission.
    """
    student = get_student_profile()

    if file_type == 'attachment':
        assignment = query_db("""
            SELECT a.attachment_path, a.attachment_filename
            FROM assignments a
            JOIN subjects s ON a.subject_id = s.id
            WHERE a.id = ? AND s.department = ? AND s.semester = ?
        """, (target_id, student['department'], student['semester']), one=True)
        if not assignment or not assignment['attachment_path']:
            abort(404, description="Attachment not available.")
        return storage_service.get_file_download_response(assignment['attachment_path'], assignment['attachment_filename'])

    elif file_type == 'submission':
        sub = query_db(
            "SELECT file_path, file_filename FROM submissions WHERE id = ? AND student_id = ?",
            (target_id, student['id']),
            one=True
        )
        if not sub:
            abort(403, description="Unauthorized: Cannot download this file.")
        return storage_service.get_file_download_response(sub['file_path'], sub['file_filename'])

    else:
        abort(400)
