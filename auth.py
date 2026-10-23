import functools
import secrets
from datetime import datetime, timedelta
from flask import session, redirect, url_for, flash, abort, request, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db, execute_db

def hash_password(password: str) -> str:
    """Hashes a plain text password using Werkzeug's default pbkdf2:sha256."""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(stored_hash: str, password: str) -> bool:
    """Safely verifies a password against its hash."""
    if not stored_hash or not password:
        return False
    return check_password_hash(stored_hash, password)

def generate_secure_token() -> str:
    """Generates a cryptographically strong, URL-safe random token."""
    return secrets.token_urlsafe(32)

from flask import session, redirect, url_for, flash, abort, request, g, current_app

def generate_csrf_token():
    """Generates or retrieves the session CSRF token."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']

def validate_csrf():
    """Validates the CSRF token on mutating requests."""
    if current_app.config.get('TESTING') and not current_app.config.get('WTF_CSRF_ENABLED', True):
        return

    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
        session_token = session.get('_csrf_token')
        if not token or not session_token or not secrets.compare_digest(token, session_token):
            flash("Security check failed (CSRF token missing or expired). Please try again.", "danger")
            abort(400, description="Invalid or missing CSRF token.")

def get_current_user():
    """Fetches the currently authenticated user's details from database."""
    if 'user_id' not in session:
        return None
    user_id = session['user_id']
    user = query_db("SELECT id, email, role, is_active, must_change_password FROM users WHERE id = ?", (user_id,), one=True)
    if not user:
        session.clear()
        return None
    
    user_data = dict(user)
    # Attach role specific details
    if user['role'] == 'teacher':
        teacher = query_db("SELECT id, name, employee_id, department, college, phone FROM teachers WHERE user_id = ?", (user_id,), one=True)
        if teacher:
            user_data['teacher'] = dict(teacher)
            user_data['profile_id'] = teacher['id']
            user_data['name'] = teacher['name']
    elif user['role'] == 'student':
        student = query_db("SELECT id, register_no, name, college, department, semester, class_section, phone FROM students WHERE user_id = ?", (user_id,), one=True)
        if student:
            user_data['student'] = dict(student)
            user_data['profile_id'] = student['id']
            user_data['name'] = student['name']
    elif user['role'] == 'admin':
        user_data['name'] = 'System Administrator'
    
    return user_data

def login_required(view):
    """Decorator ensuring a user is logged in."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login_portal'))
        user = get_current_user()
        if not user:
            flash("Session expired or user not found. Please log in again.", "warning")
            return redirect(url_for('auth.login_portal'))
        if not user.get('is_active', 1):
            session.clear()
            flash("Your account has been deactivated. Please contact the administrator.", "danger")
            return redirect(url_for('auth.login_portal'))
        g.user = user
        return view(**kwargs)
    return wrapped_view

def role_required(*allowed_roles):
    """Decorator ensuring the logged in user has one of the allowed roles."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if 'user_id' not in session:
                flash("Authentication required.", "warning")
                return redirect(url_for('auth.login_portal'))
            
            user = get_current_user()
            if not user:
                session.clear()
                flash("Session invalid.", "danger")
                return redirect(url_for('auth.login_portal'))
                
            if not user.get('is_active', 1):
                session.clear()
                flash("Your account is inactive. Please contact the administrator.", "danger")
                return redirect(url_for('auth.login_portal'))

            if user.get('role') not in allowed_roles:
                flash(f"Access Denied: You do not have permission to access this area ({', '.join(allowed_roles)} only).", "danger")
                abort(403)
                
            g.user = user
            return view(**kwargs)
        return wrapped_view
    return decorator

teacher_required = role_required('teacher')
admin_required = role_required('admin')
student_required = role_required('student')

def create_activation_token(user_id: int, token_type: str = 'activation', expiry_hours: int = 48) -> str:
    """Generates and persists an activation or reset token."""
    token = generate_secure_token()
    expires_at = (datetime.now() + timedelta(hours=expiry_hours)).strftime("%Y-%m-%d %H:%M:%S")
    # Invalidate previous unused tokens of the same type for this user
    execute_db(
        "UPDATE activation_tokens SET is_used = 1 WHERE user_id = ? AND token_type = ? AND is_used = 0",
        (user_id, token_type)
    )
    execute_db(
        "INSERT INTO activation_tokens (user_id, token, token_type, expires_at, is_used) VALUES (?, ?, ?, ?, 0)",
        (user_id, token, token_type, expires_at)
    )
    return token

def verify_token(token: str, token_type: str = 'activation'):
    """Validates an activation or reset token and returns the corresponding user."""
    record = query_db(
        """SELECT t.id, t.user_id, t.token, t.token_type, t.expires_at, t.is_used,
                  u.email, u.role, u.is_active
           FROM activation_tokens t
           JOIN users u ON t.user_id = u.id
           WHERE t.token = ? AND t.token_type = ? AND t.is_used = 0""",
        (token, token_type),
        one=True
    )
    if not record:
        return None, "Invalid or already used activation token."
    
    expires_at = record['expires_at']
    if isinstance(expires_at, str):
        clean_exp = expires_at.replace('T', ' ').split('.')[0]
        expires_at = datetime.strptime(clean_exp, "%Y-%m-%d %H:%M:%S")
        
    if datetime.now() > expires_at:
        return None, "This activation link has expired. Please contact the administrator."
        
    return record, None
