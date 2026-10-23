import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from database import query_db, execute_db
from auth import admin_required, hash_password, create_activation_token, validate_csrf

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@admin_required
def require_admin():
    """Enforce admin authorization on all admin routes."""
    pass

@admin_bp.route('/dashboard')
def dashboard():
    """Admin Dashboard showing high-level system statistics."""
    stats = {
        'teachers_count': query_db("SELECT COUNT(*) as c FROM teachers", one=True)['c'],
        'students_count': query_db("SELECT COUNT(*) as c FROM students", one=True)['c'],
        'subjects_count': query_db("SELECT COUNT(*) as c FROM subjects", one=True)['c'],
        'assignments_count': query_db("SELECT COUNT(*) as c FROM assignments", one=True)['c'],
        'submissions_count': query_db("SELECT COUNT(*) as c FROM submissions", one=True)['c']
    }

    # Fetch recent activities
    recent_teachers = query_db("""
        SELECT t.id, t.name, t.employee_id, t.department, u.email, u.is_active, t.created_at
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC LIMIT 5
    """)

    recent_assignments = query_db("""
        SELECT a.id, a.title, a.created_at, s.subject_code, s.subject_name, t.name as teacher_name
        FROM assignments a
        JOIN subjects s ON a.subject_id = s.id
        JOIN teachers t ON a.teacher_id = t.id
        ORDER BY a.created_at DESC LIMIT 5
    """)

    return render_template('admin/dashboard.html', stats=stats, recent_teachers=recent_teachers, recent_assignments=recent_assignments)

@admin_bp.route('/teachers')
def manage_teachers():
    """
    Manage Teachers page:
    Lists all teachers with status, department, employee ID, and assigned subjects.
    """
    teachers_raw = query_db("""
        SELECT t.id, t.user_id, t.name, t.employee_id, t.department, t.college, t.phone, t.created_at,
               u.email, u.is_active
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
    """)

    teachers = []
    for row in teachers_raw:
        teacher_dict = dict(row)
        # Fetch assigned subjects for each teacher
        subjects = query_db("""
            SELECT s.id, s.subject_code, s.subject_name, s.semester, s.department
            FROM subjects s
            JOIN teacher_subjects ts ON s.id = ts.subject_id
            WHERE ts.teacher_id = ?
            ORDER BY s.subject_code
        """, (teacher_dict['id'],))
        teacher_dict['assigned_subjects'] = subjects
        teachers.append(teacher_dict)

    # All subjects for quick modal or reference
    all_subjects = query_db("SELECT id, subject_code, subject_name, department, semester FROM subjects ORDER BY department, semester")

    # Retrieve any newly generated activation link from flash/session
    new_activation_link = session.pop('new_activation_link', None)
    new_teacher_name = session.pop('new_teacher_name', None)
    new_teacher_email = session.pop('new_teacher_email', None)

    return render_template(
        'admin/manage_teachers.html',
        teachers=teachers,
        all_subjects=all_subjects,
        new_activation_link=new_activation_link,
        new_teacher_name=new_teacher_name,
        new_teacher_email=new_teacher_email
    )

@admin_bp.route('/teachers/create', methods=['GET', 'POST'])
def create_teacher():
    """
    Create a new teacher account (Admin Only).
    Admin enters teacher name, college email, employee ID, department, and assigns subjects.
    Generates a secure, single-use activation link.
    """
    all_subjects = query_db("SELECT id, subject_code, subject_name, department, semester FROM subjects ORDER BY department, semester")

    if request.method == 'POST':
        validate_csrf()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        employee_id = request.form.get('employee_id', '').strip().upper()
        department = request.form.get('department', '').strip()
        college = request.form.get('college', 'Apex Institute of Technology').strip()
        phone = request.form.get('phone', '').strip()
        selected_subject_ids = request.form.getlist('subjects')

        # Server-side validation
        if not all([name, email, employee_id, department]):
            flash("Teacher name, college email, employee ID, and department are mandatory.", "danger")
            return render_template('admin/create_teacher.html', all_subjects=all_subjects, **request.form)

        # Check unique email
        if query_db("SELECT id FROM users WHERE LOWER(email) = ?", (email,), one=True):
            flash(f"A user with email '{email}' already exists in the system.", "danger")
            return render_template('admin/create_teacher.html', all_subjects=all_subjects, **request.form)

        # Check unique employee ID
        if query_db("SELECT id FROM teachers WHERE LOWER(employee_id) = ?", (employee_id.lower(),), one=True):
            flash(f"A teacher with Employee ID '{employee_id}' is already registered.", "danger")
            return render_template('admin/create_teacher.html', all_subjects=all_subjects, **request.form)

        # Create user account with a temporary secure placeholder hash (inactive until activation)
        temp_placeholder_pw = secrets.token_hex(16)
        pw_hash = hash_password(temp_placeholder_pw)
        user_id = execute_db(
            "INSERT INTO users (email, password_hash, role, is_active, must_change_password) VALUES (?, ?, 'teacher', 0, 1)",
            (email, pw_hash)
        )

        # Insert teacher profile
        teacher_id = execute_db(
            """INSERT INTO teachers (user_id, name, employee_id, department, college, phone)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, name, employee_id, department, college, phone)
        )

        # Assign subjects
        if selected_subject_ids:
            for sub_id in selected_subject_ids:
                try:
                    execute_db(
                        "INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)",
                        (teacher_id, int(sub_id))
                    )
                except Exception as e:
                    pass

        # Generate single-use activation token
        activation_token = create_activation_token(user_id, token_type='activation', expiry_hours=48)
        activation_url = url_for('auth.activate_teacher', token=activation_token, _external=True)

        # Store in session for the presentation modal / alert
        session['new_activation_link'] = activation_url
        session['new_teacher_name'] = name
        session['new_teacher_email'] = email

        flash(f"Teacher account for '{name}' successfully created! Single-use activation link generated.", "success")
        return redirect(url_for('admin.manage_teachers'))

    return render_template('admin/create_teacher.html', all_subjects=all_subjects)

@admin_bp.route('/teachers/<int:teacher_id>/edit', methods=['GET', 'POST'])
def edit_teacher(teacher_id):
    """
    Edit teacher details and subject assignments.
    """
    teacher = query_db("""
        SELECT t.id, t.user_id, t.name, t.employee_id, t.department, t.college, t.phone,
               u.email, u.is_active
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        WHERE t.id = ?
    """, (teacher_id,), one=True)

    if not teacher:
        flash("Teacher not found.", "danger")
        return redirect(url_for('admin.manage_teachers'))

    all_subjects = query_db("SELECT id, subject_code, subject_name, department, semester FROM subjects ORDER BY department, semester")
    
    # Get currently assigned subject IDs
    assigned_subject_ids = [row['subject_id'] for row in query_db(
        "SELECT subject_id FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,)
    )]

    if request.method == 'POST':
        validate_csrf()
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()
        is_active = 1 if request.form.get('is_active') == '1' else 0
        selected_subject_ids = [int(x) for x in request.form.getlist('subjects')]

        if not name or not department:
            flash("Teacher name and department cannot be blank.", "danger")
            return render_template('admin/edit_teacher.html', teacher=teacher, all_subjects=all_subjects, assigned_subject_ids=assigned_subject_ids)

        # Update teacher profile
        execute_db(
            "UPDATE teachers SET name = ?, department = ?, phone = ? WHERE id = ?",
            (name, department, phone, teacher_id)
        )

        # Update user active status
        execute_db("UPDATE users SET is_active = ? WHERE id = ?", (is_active, teacher['user_id']))

        # Update assigned subjects: delete existing and reinsert selected
        execute_db("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))
        for sub_id in selected_subject_ids:
            execute_db("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, ?)", (teacher_id, sub_id))

        flash(f"Teacher details for '{name}' successfully updated.", "success")
        return redirect(url_for('admin.manage_teachers'))

    return render_template(
        'admin/edit_teacher.html',
        teacher=teacher,
        all_subjects=all_subjects,
        assigned_subject_ids=assigned_subject_ids
    )

@admin_bp.route('/teachers/<int:teacher_id>/toggle-status', methods=['POST'])
def toggle_teacher_status(teacher_id):
    """
    Activate or deactivate teacher account.
    """
    validate_csrf()
    teacher = query_db("SELECT t.id, t.user_id, t.name, u.is_active FROM teachers t JOIN users u ON t.user_id = u.id WHERE t.id = ?", (teacher_id,), one=True)
    if not teacher:
        flash("Teacher not found.", "danger")
        return redirect(url_for('admin.manage_teachers'))

    new_status = 0 if teacher['is_active'] else 1
    execute_db("UPDATE users SET is_active = ? WHERE id = ?", (new_status, teacher['user_id']))

    status_str = "activated" if new_status == 1 else "deactivated"
    flash(f"Teacher account for '{teacher['name']}' has been {status_str}.", "info")
    return redirect(url_for('admin.manage_teachers'))

@admin_bp.route('/teachers/<int:teacher_id>/generate-activation', methods=['POST'])
def generate_teacher_activation(teacher_id):
    """
    Generates a new single-use activation link for an existing teacher.
    """
    validate_csrf()
    teacher = query_db("SELECT t.user_id, t.name, u.email FROM teachers t JOIN users u ON t.user_id = u.id WHERE t.id = ?", (teacher_id,), one=True)
    if not teacher:
        flash("Teacher not found.", "danger")
        return redirect(url_for('admin.manage_teachers'))

    token = create_activation_token(teacher['user_id'], token_type='activation', expiry_hours=48)
    activation_url = url_for('auth.activate_teacher', token=token, _external=True)

    session['new_activation_link'] = activation_url
    session['new_teacher_name'] = teacher['name']
    session['new_teacher_email'] = teacher['email']

    flash(f"New activation link generated for {teacher['name']}.", "success")
    return redirect(url_for('admin.manage_teachers'))

@admin_bp.route('/teachers/<int:teacher_id>/delete', methods=['POST'])
def delete_teacher(teacher_id):
    """
    Delete a teacher account, profile, course allocations, assignments, and associated user account.
    """
    validate_csrf()
    teacher = query_db("SELECT t.id, t.user_id, t.name, t.employee_id FROM teachers t WHERE t.id = ?", (teacher_id,), one=True)
    if not teacher:
        flash("Teacher not found or already deleted.", "danger")
        return redirect(url_for('admin.manage_teachers'))

    teacher_name = teacher['name']
    user_id = teacher['user_id']

    # 1. Clear graded_by reference in submissions if this teacher graded any to avoid FK constraint error
    execute_db("UPDATE submissions SET graded_by = NULL WHERE graded_by = ?", (teacher_id,))

    # 2. Delete assignments created by this teacher (and their submissions)
    execute_db("""
        DELETE FROM submissions WHERE assignment_id IN (
            SELECT id FROM assignments WHERE teacher_id = ?
        )
    """, (teacher_id,))
    execute_db("DELETE FROM assignments WHERE teacher_id = ?", (teacher_id,))

    # 3. Remove teacher-subject allocations
    execute_db("DELETE FROM teacher_subjects WHERE teacher_id = ?", (teacher_id,))

    # 4. Remove teacher profile
    execute_db("DELETE FROM teachers WHERE id = ?", (teacher_id,))

    # 5. Remove user account & activation tokens
    execute_db("DELETE FROM activation_tokens WHERE user_id = ?", (user_id,))
    execute_db("DELETE FROM users WHERE id = ?", (user_id,))

    flash(f"Teacher '{teacher_name}' (ID: {teacher['employee_id']}) was successfully deleted.", "success")
    return redirect(url_for('admin.manage_teachers'))

@admin_bp.route('/subjects', methods=['GET', 'POST'])
def manage_subjects():
    """Manage subjects: list all and add new subjects."""
    if request.method == 'POST':
        validate_csrf()
        code = request.form.get('subject_code', '').strip().upper()
        name = request.form.get('subject_name', '').strip()
        dept = request.form.get('department', '').strip()
        sem = request.form.get('semester', '').strip()
        credits = request.form.get('credits', '3').strip()

        if not all([code, name, dept, sem]):
            flash("All subject fields are mandatory.", "danger")
        elif query_db("SELECT id FROM subjects WHERE LOWER(subject_code) = ?", (code.lower(),), one=True):
            flash(f"Subject with code '{code}' already exists.", "danger")
        else:
            execute_db(
                "INSERT INTO subjects (subject_code, subject_name, department, semester, credits) VALUES (?, ?, ?, ?, ?)",
                (code, name, dept, int(sem), int(credits))
            )
            flash(f"Subject '{code} - {name}' added successfully.", "success")
            return redirect(url_for('admin.manage_subjects'))

    subjects = query_db("""
        SELECT s.id, s.subject_code, s.subject_name, s.department, s.semester, s.credits,
               COUNT(DISTINCT ts.teacher_id) as allocated_teachers_count,
               COUNT(DISTINCT a.id) as assignments_count
        FROM subjects s
        LEFT JOIN teacher_subjects ts ON s.id = ts.subject_id
        LEFT JOIN assignments a ON s.id = a.subject_id
        GROUP BY s.id
        ORDER BY s.department, s.semester, s.subject_code
    """)
    return render_template('admin/manage_subjects.html', subjects=subjects)

@admin_bp.route('/subjects/<int:subject_id>/delete', methods=['POST'])
def delete_subject(subject_id):
    """
    Delete an unwanted subject from the course catalog.
    Also removes allocations, assignments, and submissions associated with the subject.
    """
    validate_csrf()
    subject = query_db("SELECT id, subject_code, subject_name FROM subjects WHERE id = ?", (subject_id,), one=True)
    if not subject:
        flash("Subject not found or already deleted.", "danger")
        return redirect(url_for('admin.manage_subjects'))

    code = subject['subject_code']
    name = subject['subject_name']

    # 1. Clean submissions associated with assignments in this subject
    execute_db("""
        DELETE FROM submissions WHERE assignment_id IN (
            SELECT id FROM assignments WHERE subject_id = ?
        )
    """, (subject_id,))

    # 2. Clean assignments under this subject
    execute_db("DELETE FROM assignments WHERE subject_id = ?", (subject_id,))

    # 3. Clean teacher subject allocations
    execute_db("DELETE FROM teacher_subjects WHERE subject_id = ?", (subject_id,))

    # 4. Delete the subject itself
    execute_db("DELETE FROM subjects WHERE id = ?", (subject_id,))

    flash(f"Subject '{code} - {name}' was successfully deleted.", "success")
    return redirect(url_for('admin.manage_subjects'))

