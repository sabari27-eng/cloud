from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from database import query_db, execute_db
from auth import hash_password, verify_password, create_activation_token, verify_token, validate_csrf

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def home():
    """Landing portal page with quick role selection and overview."""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'student':
            return redirect(url_for('student.dashboard'))
    return render_template('index.html')

@auth_bp.route('/portal')
def login_portal():
    """Portal selection page."""
    return render_template('index.html')

@auth_bp.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    """Teacher login page with college logo, validation, and role checks."""
    if 'user_id' in session and session.get('role') == 'teacher':
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        validate_csrf()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email address and password.", "danger")
            return render_template('auth/teacher_login.html', email=email)

        # Lookup user by email
        user = query_db(
            """SELECT u.id, u.email, u.password_hash, u.role, u.is_active, u.must_change_password,
                      t.name as teacher_name, t.employee_id
               FROM users u
               LEFT JOIN teachers t ON u.id = t.user_id
               WHERE LOWER(u.email) = ?""",
            (email,),
            one=True
        )

        if not user or not verify_password(user['password_hash'], password):
            flash("Invalid email or password. Please verify your credentials.", "danger")
            return render_template('auth/teacher_login.html', email=email)

        # Check role authorization
        if user['role'] != 'teacher':
            flash("Access Restricted: This login is exclusively for faculty members. Students and Admins must use their respective portals.", "warning")
            return render_template('auth/teacher_login.html', email=email)

        # Check account activation status
        if not user['is_active']:
            flash("Your teacher account is currently inactive or pending activation. Please use your activation link or contact the administrator.", "danger")
            return render_template('auth/teacher_login.html', email=email)

        # Successful login
        session.clear()
        session['user_id'] = user['id']
        session['role'] = 'teacher'
        session['email'] = user['email']
        session['name'] = user['teacher_name'] or 'Teacher'

        flash(f"Welcome back, {user['teacher_name']}! You have logged into the Teacher Portal.", "success")
        return redirect(url_for('teacher.dashboard'))

    return render_template('auth/teacher_login.html')

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        validate_csrf()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please provide admin credentials.", "danger")
            return render_template('auth/admin_login.html', email=email)

        user = query_db(
            "SELECT id, email, password_hash, role, is_active FROM users WHERE LOWER(email) = ?",
            (email,),
            one=True
        )

        if not user or not verify_password(user['password_hash'], password):
            flash("Invalid administrator credentials.", "danger")
            return render_template('auth/admin_login.html', email=email)

        if user['role'] != 'admin':
            flash("Unauthorized: Non-admin account.", "danger")
            return render_template('auth/admin_login.html', email=email)

        if not user['is_active']:
            flash("Administrator account is disabled.", "danger")
            return render_template('auth/admin_login.html', email=email)

        session.clear()
        session['user_id'] = user['id']
        session['role'] = 'admin'
        session['email'] = user['email']
        session['name'] = 'System Administrator'

        flash("Welcome to the Administration Panel.", "success")
        return redirect(url_for('admin.dashboard'))

    return render_template('auth/admin_login.html')

@auth_bp.route('/student/login', methods=['GET', 'POST'])
def student_login():
    """Student login page."""
    if 'user_id' in session and session.get('role') == 'student':
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        validate_csrf()
        email_or_reg = request.form.get('email_or_reg', '').strip()
        password = request.form.get('password', '')

        if not email_or_reg or not password:
            flash("Please enter your Student Email or Register Number and password.", "danger")
            return render_template('auth/student_login.html', email_or_reg=email_or_reg)

        user = query_db(
            """SELECT u.id, u.email, u.password_hash, u.role, u.is_active,
                      s.name as student_name, s.register_no, s.department, s.semester
               FROM users u
               JOIN students s ON u.id = s.user_id
               WHERE LOWER(u.email) = ? OR LOWER(s.register_no) = ?""",
            (email_or_reg.lower(), email_or_reg.lower()),
            one=True
        )

        if not user or not verify_password(user['password_hash'], password):
            flash("Invalid student credentials.", "danger")
            return render_template('auth/student_login.html', email_or_reg=email_or_reg)

        if user['role'] != 'student':
            flash("Access denied: Not a student account.", "danger")
            return render_template('auth/student_login.html', email_or_reg=email_or_reg)

        if not user['is_active']:
            flash("Student account has been deactivated. Contact admin.", "danger")
            return render_template('auth/student_login.html', email_or_reg=email_or_reg)

        session.clear()
        session['user_id'] = user['id']
        session['role'] = 'student'
        session['email'] = user['email']
        session['name'] = user['student_name']
        session['register_no'] = user['register_no']

        flash(f"Welcome back, {user['student_name']}!", "success")
        return redirect(url_for('student.dashboard'))

    return render_template('auth/student_login.html')

@auth_bp.route('/student/register', methods=['GET', 'POST'])
def student_register():
    """Student self-registration."""
    if request.method == 'POST':
        validate_csrf()
        name = request.form.get('name', '').strip()
        register_no = request.form.get('register_no', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        college = request.form.get('college', 'Apex Institute of Technology').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '').strip()
        class_section = request.form.get('class_section', 'A').strip().upper()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([name, register_no, email, department, semester, password]):
            flash("Please fill in all mandatory fields.", "danger")
            return render_template('auth/student_register.html', **request.form)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/student_register.html', **request.form)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template('auth/student_register.html', **request.form)

        # Check uniqueness of email and register_no
        existing_email = query_db("SELECT id FROM users WHERE LOWER(email) = ?", (email,), one=True)
        if existing_email:
            flash("An account with this email already exists. Please login instead.", "warning")
            return render_template('auth/student_register.html', **request.form)

        existing_reg = query_db("SELECT id FROM students WHERE LOWER(register_no) = ?", (register_no.lower(),), one=True)
        if existing_reg:
            flash("A student with this Register Number is already registered.", "warning")
            return render_template('auth/student_register.html', **request.form)

        pw_hash = hash_password(password)
        user_id = execute_db(
            "INSERT INTO users (email, password_hash, role, is_active, must_change_password) VALUES (?, ?, 'student', 1, 0)",
            (email, pw_hash)
        )
        execute_db(
            """INSERT INTO students (user_id, register_no, name, college, department, semester, class_section, phone)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, register_no, name, college, department, int(semester), class_section, phone)
        )

        flash("Student registration successful! You can now log in.", "success")
        return redirect(url_for('auth.student_login'))

    return render_template('auth/student_register.html')

@auth_bp.route('/teacher/activate/<token>', methods=['GET', 'POST'])
def activate_teacher(token):
    """
    Teacher account activation using a secure single-use token.
    Allows teacher to set their own password securely.
    """
    record, error = verify_token(token, token_type='activation')
    if error:
        flash(error, "danger")
        return redirect(url_for('auth.teacher_login'))

    user_id = record['user_id']
    teacher = query_db("SELECT name, department, employee_id FROM teachers WHERE user_id = ?", (user_id,), one=True)

    if request.method == 'POST':
        validate_csrf()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not password or len(password) < 8:
            flash("Password must be at least 8 characters long for security.", "danger")
            return render_template('auth/activate_account.html', token=token, record=record, teacher=teacher)

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter carefully.", "danger")
            return render_template('auth/activate_account.html', token=token, record=record, teacher=teacher)

        # Hash new password
        pw_hash = hash_password(password)

        # Update user status to active and update password
        execute_db(
            "UPDATE users SET password_hash = ?, is_active = 1, must_change_password = 0 WHERE id = ?",
            (pw_hash, user_id)
        )

        # Mark token as used
        execute_db("UPDATE activation_tokens SET is_used = 1 WHERE id = ?", (record['id'],))

        flash("Your teacher account has been successfully activated! You can now log in with your credentials.", "success")
        return redirect(url_for('auth.teacher_login'))

    return render_template('auth/activate_account.html', token=token, record=record, teacher=teacher)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password request page."""
    if request.method == 'POST':
        validate_csrf()
        email = request.form.get('email', '').strip().lower()
        user = query_db("SELECT id, email, role FROM users WHERE LOWER(email) = ?", (email,), one=True)
        if user:
            token = create_activation_token(user['id'], token_type='reset', expiry_hours=24)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            # In development, flash the link directly so user can test without mail server
            flash(f"[Dev Mode] Password reset link generated: {reset_url}", "info")
            flash("A password reset link has been dispatched to your email address.", "success")
        else:
            # Prevent email enumeration by giving a neutral message
            flash("If the provided email exists in our records, a reset link has been sent.", "info")
        return redirect(url_for('auth.login_portal'))

    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token."""
    record, error = verify_token(token, token_type='reset')
    if error:
        flash(error, "danger")
        return redirect(url_for('auth.login_portal'))

    if request.method == 'POST':
        validate_csrf()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template('auth/forgot_password.html', token=token)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/forgot_password.html', token=token)

        pw_hash = hash_password(password)
        execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, record['user_id']))
        execute_db("UPDATE activation_tokens SET is_used = 1 WHERE id = ?", (record['id'],))

        flash("Password successfully reset! You can now log in.", "success")
        if record['role'] == 'teacher':
            return redirect(url_for('auth.teacher_login'))
        elif record['role'] == 'admin':
            return redirect(url_for('auth.admin_login'))
        else:
            return redirect(url_for('auth.student_login'))

    return render_template('auth/forgot_password.html', token=token, is_reset_step=True)

@auth_bp.route('/logout')
def logout():
    """Logs out user and clears session."""
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for('auth.login_portal'))
