import os
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from config import Config

def init_db(force=False):
    """Initializes the database schema and seeds initial data."""
    if force and os.path.exists(Config.DB_PATH):
        try:
            os.remove(Config.DB_PATH)
            print("[init_db] Removed existing database.")
        except Exception as e:
            print(f"[init_db] Could not remove existing DB: {e}")

    # Ensure upload directories exist
    os.makedirs(Config.ASSIGNMENT_UPLOADS, exist_ok=True)
    os.makedirs(Config.SUBMISSION_UPLOADS, exist_ok=True)

    conn = sqlite3.connect(Config.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    cursor = conn.cursor()

    print("[init_db] Creating tables...")

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
        is_active INTEGER NOT NULL DEFAULT 1,
        must_change_password INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Teachers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        employee_id TEXT UNIQUE NOT NULL COLLATE NOCASE,
        department TEXT NOT NULL,
        college TEXT NOT NULL DEFAULT 'Apex Institute of Technology',
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        register_no TEXT UNIQUE NOT NULL COLLATE NOCASE,
        name TEXT NOT NULL,
        college TEXT NOT NULL DEFAULT 'Apex Institute of Technology',
        department TEXT NOT NULL,
        semester INTEGER NOT NULL,
        class_section TEXT DEFAULT 'A',
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Subjects Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_code TEXT UNIQUE NOT NULL COLLATE NOCASE,
        subject_name TEXT NOT NULL,
        department TEXT NOT NULL,
        semester INTEGER NOT NULL,
        credits INTEGER DEFAULT 3,
        college TEXT NOT NULL DEFAULT 'Apex Institute of Technology',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Teacher Subject Allocations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teacher_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        academic_year TEXT DEFAULT '2026-2027',
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(teacher_id, subject_id)
    );
    """)

    # 6. Assignments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        description TEXT,
        attachment_filename TEXT,
        attachment_path TEXT,
        max_marks INTEGER DEFAULT 100,
        allowed_extensions TEXT DEFAULT 'pdf,doc,docx,zip',
        max_file_size_mb INTEGER DEFAULT 10,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deadline TIMESTAMP NOT NULL,
        is_published INTEGER DEFAULT 1
    );
    """)

    # 7. Submissions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        file_filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_late INTEGER DEFAULT 0,
        grade REAL,
        feedback TEXT,
        graded_at TIMESTAMP,
        graded_by INTEGER REFERENCES teachers(id),
        UNIQUE(assignment_id, student_id)
    );
    """)

    # 8. Activation Tokens Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activation_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token TEXT UNIQUE NOT NULL,
        token_type TEXT DEFAULT 'activation' CHECK(token_type IN ('activation', 'reset')),
        expires_at TIMESTAMP NOT NULL,
        is_used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    print("[init_db] Schema created successfully.")

    # Check if data already seeded
    cursor.execute("SELECT COUNT(*) FROM users;")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_data(conn)
    else:
        print("[init_db] Database already contains records. Skipping initial seeding.")

    conn.close()

def seed_data(conn):
    """Seeds the initial users, subjects, teachers, students, assignments, and sample submissions."""
    cursor = conn.cursor()
    print("[init_db] Seeding initial data...")

    # Default Passwords
    admin_pw = generate_password_hash("Admin@123", method='pbkdf2:sha256')
    teacher_pw = generate_password_hash("Teacher@123", method='pbkdf2:sha256')
    student_pw = generate_password_hash("Student@123", method='pbkdf2:sha256')

    # 1. Admin Account
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, is_active, must_change_password) VALUES (?, ?, 'admin', 1, 0)",
        ("admin@college.edu", admin_pw)
    )

    # 2. Subjects
    subjects = [
        ("CS501", "Cloud Computing & Distributed Systems", "Computer Science", 5, 4),
        ("CS502", "Database Management Systems", "Computer Science", 5, 4),
        ("CS503", "Full Stack Web Technologies", "Computer Science", 5, 3),
        ("IT501", "Network Security & Cryptography", "Information Technology", 5, 4),
        ("EC501", "Embedded Systems & IoT", "Electronics & Comm", 5, 3),
    ]
    cursor.executemany(
        "INSERT INTO subjects (subject_code, subject_name, department, semester, credits) VALUES (?, ?, ?, ?, ?)",
        subjects
    )

    # 3. Teachers
    # Teacher 1: Alan Turing (Active, has subjects CS501 and CS503)
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, is_active, must_change_password) VALUES (?, ?, 'teacher', 1, 0)",
        ("alan.turing@college.edu", teacher_pw)
    )
    turing_user_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO teachers (user_id, name, employee_id, department, college, phone) VALUES (?, ?, ?, ?, ?, ?)",
        (turing_user_id, "Prof. Alan Turing", "EMP101", "Computer Science", "Apex Institute of Technology", "+91 9876543210")
    )
    turing_id = cursor.lastrowid

    # Teacher 2: Ada Lovelace (Active, has subject CS502)
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, is_active, must_change_password) VALUES (?, ?, 'teacher', 1, 0)",
        ("ada.lovelace@college.edu", teacher_pw)
    )
    ada_user_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO teachers (user_id, name, employee_id, department, college, phone) VALUES (?, ?, ?, ?, ?, ?)",
        (ada_user_id, "Dr. Ada Lovelace", "EMP102", "Computer Science", "Apex Institute of Technology", "+91 9876543211")
    )
    ada_id = cursor.lastrowid

    # Teacher 3: Grace Hopper (Inactive - for testing inactive blocking and activation)
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, is_active, must_change_password) VALUES (?, ?, 'teacher', 0, 1)",
        ("grace.hopper@college.edu", teacher_pw)
    )
    grace_user_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO teachers (user_id, name, employee_id, department, college, phone) VALUES (?, ?, ?, ?, ?, ?)",
        (grace_user_id, "Prof. Grace Hopper", "EMP103", "Information Technology", "Apex Institute of Technology", "+91 9876543212")
    )
    grace_id = cursor.lastrowid

    # Allocate subjects to Alan Turing (CS501: id 1, CS503: id 3)
    cursor.execute("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, 1)", (turing_id,))
    cursor.execute("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, 3)", (turing_id,))
    # Allocate subject to Ada Lovelace (CS502: id 2)
    cursor.execute("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, 2)", (ada_id,))
    # Allocate subject to Grace Hopper (IT501: id 4)
    cursor.execute("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (?, 4)", (grace_id,))

    # 4. Students (CSE Semester 5 - Eligible for CS501, CS502, CS503)
    students = [
        ("john.doe@student.college.edu", "21CS001", "John Doe", "Computer Science", 5, "A"),
        ("jane.smith@student.college.edu", "21CS002", "Jane Smith", "Computer Science", 5, "A"),
        ("robert.johnson@student.college.edu", "21CS003", "Robert Johnson", "Computer Science", 5, "B"),
        ("emily.davis@student.college.edu", "21IT001", "Emily Davis", "Information Technology", 5, "A"),
    ]

    student_records = []
    for email, reg_no, name, dept, sem, sec in students:
        cursor.execute(
            "INSERT INTO users (email, password_hash, role, is_active, must_change_password) VALUES (?, ?, 'student', 1, 0)",
            (email, student_pw)
        )
        uid = cursor.lastrowid
        cursor.execute(
            "INSERT INTO students (user_id, register_no, name, college, department, semester, class_section) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uid, reg_no, name, "Apex Institute of Technology", dept, sem, sec)
        )
        student_records.append((cursor.lastrowid, name, reg_no))

    # 5. Assignments posted by Prof. Alan Turing
    now = datetime.now()
    deadline_future = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    deadline_past = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

    # Assignment 1 for CS501: Cloud Computing (Active deadline)
    sample_guide_file = os.path.join(Config.ASSIGNMENT_UPLOADS, "sample_cloud_lab_manual.pdf")
    with open(sample_guide_file, "w", encoding="utf-8") as f:
        f.write("%PDF-1.4 Sample Cloud Computing Lab Manual for Mini Project")

    cursor.execute("""
    INSERT INTO assignments (subject_id, teacher_id, title, description, attachment_filename, attachment_path, max_marks, allowed_extensions, max_file_size_mb, deadline, is_published)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        1,  # CS501
        turing_id,
        "Assignment 1: AWS EC2 & S3 Cloud Architecture Design",
        "Design a high-availability cloud architecture using AWS EC2, S3, and RDS. Submit a detailed PDF report including architecture diagrams, cost optimization calculations, and security group rules.",
        "sample_cloud_lab_manual.pdf",
        os.path.join("uploads", "assignments", "sample_cloud_lab_manual.pdf"),
        100,
        "pdf,doc,docx,zip",
        15,
        deadline_future
    ))
    assignment_1_id = cursor.lastrowid

    # Assignment 2 for CS503: Web Technologies
    cursor.execute("""
    INSERT INTO assignments (subject_id, teacher_id, title, description, attachment_filename, attachment_path, max_marks, allowed_extensions, max_file_size_mb, deadline, is_published)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        3,  # CS503
        turing_id,
        "Assignment 1: Responsive Web Application with Bootstrap 5",
        "Build a multi-page responsive web portal incorporating modern UI cards, responsive navbar, and form validation using Bootstrap 5 and vanilla JavaScript.",
        None,
        None,
        50,
        "zip,html,pdf",
        20,
        deadline_future
    ))

    # 6. Sample Submission from John Doe (student_records[0][0])
    john_student_id = student_records[0][0]
    sample_sub_file = os.path.join(Config.SUBMISSION_UPLOADS, "21CS001_Assignment1_CloudReport.pdf")
    with open(sample_sub_file, "w", encoding="utf-8") as f:
        f.write("%PDF-1.4 John Doe 21CS001 Cloud Architecture Assignment Submission Content")

    cursor.execute("""
    INSERT INTO submissions (assignment_id, student_id, file_filename, file_path, submitted_at, is_late, grade, feedback, graded_at, graded_by)
    VALUES (?, ?, ?, ?, ?, 0, 92.5, ?, ?, ?)
    """, (
        assignment_1_id,
        john_student_id,
        "21CS001_Assignment1_CloudReport.pdf",
        os.path.join("uploads", "submissions", "21CS001_Assignment1_CloudReport.pdf"),
        (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
        "Excellent architectural diagram and well thought-out VPC subnetting! Keep up the good work.",
        now.strftime("%Y-%m-%d %H:%M:%S"),
        turing_id
    ))

    # 7. Activation token for Prof. Grace Hopper (for testing activation flow)
    from auth import create_activation_token
    # We will insert a known test activation token for testing convenience
    cursor.execute("""
    INSERT INTO activation_tokens (user_id, token, token_type, expires_at, is_used)
    VALUES (?, 'TEST_ACTIVATION_TOKEN_GRACE_123', 'activation', ?, 0)
    """, (
        grace_user_id,
        (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    print("[init_db] Seeding completed successfully!")
    print("-----------------------------------------------------------------")
    print("Pre-configured Credentials:")
    print("Admin:    admin@college.edu           / Admin@123")
    print("Teacher:  alan.turing@college.edu     / Teacher@123 (Active)")
    print("Teacher:  ada.lovelace@college.edu    / Teacher@123 (Active)")
    print("Teacher:  grace.hopper@college.edu    / Teacher@123 (Inactive / Inactivation test)")
    print("Student:  john.doe@student.college.edu / Student@123 (CSE Sem 5)")
    print("Student:  jane.smith@student.college.edu / Student@123 (CSE Sem 5 - Pending Submissions)")
    print("-----------------------------------------------------------------")

if __name__ == '__main__':
    init_db(force=True)
