# Cloud-Based Assignment Submission and Tracking System (CSM)

An enterprise-grade, secure, role-based academic portal designed for colleges and universities to manage assignment distribution, student submissions, and grading. Built using **Python Flask**, **SQLite / MySQL**, and a modern **Bootstrap 5 (Blue & White)** responsive interface, architected for future deployment on **AWS EC2, Amazon S3, and Amazon RDS**.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Module Architecture & Features](#module-architecture--features)
3. [Pre-configured Test Credentials](#pre-configured-test-credentials)
4. [Step-by-Step Windows & VS Code Setup Guide](#step-by-step-windows--vs-code-setup-guide)
5. [Automated Testing Suite (All 12 Scenarios)](#automated-testing-suite)
6. [Security Architecture & Implementation](#security-architecture--implementation)
7. [Database Schema (Relational Model)](#database-schema)
8. [AWS Cloud Deployment Guide (EC2, S3, RDS)](#aws-cloud-deployment-guide)
9. [Viva / Mini-Project Evaluation Q&A](#viva--mini-project-evaluation-qa)

---

## Project Overview

In traditional college systems, assignments are collected manually through emails or physical hard copies, causing file loss, lack of deadline enforcement, and tedious grading.

The **Cloud-Based Assignment Submission and Tracking System (CSM)** provides an integrated platform:
- **Administrators** create faculty profiles and allocate subjects.
- **Teachers** activate accounts via single-use secure tokens, post assignments with reference attachments, and track submissions against the entire student roster (including non-submitted students) with real-time turn-in percentages.
- **Students** view assignments targeted to their department and semester, upload solutions with client- and server-side file validation, and view their evaluated grades and feedback.

---

## Module Architecture & Features

### 1. Teacher Module (Core Focus)
- **Admin-Only Account Creation**: Faculty cannot register publicly. Only administrators can create teacher accounts with college email, employee ID, department, and allocated subjects.
- **Single-Use Token Activation**: When created, a cryptographically signed token is generated. The teacher accesses `/teacher/activate/<token>` to set their own password securely. Passwords are never stored in plaintext.
- **Teacher Login**: Custom login page with College Assignment Portal logo, teacher email, password field, show/hide password toggle, and validation alerts. Enforces `role == 'teacher'` and `is_active == 1`.
- **Teacher Dashboard (Modern Blue-and-White Theme)**:
  - Welcome greeting with teacher's name and department.
  - **4 Live Metric Cards**:
    1. Assigned Subjects count.
    2. Total Assignments posted.
    3. Total Student Submissions received.
    4. Total Pending Submissions (calculated dynamically against eligible student rosters).
- **"My Subjects" Cards**: Shows *only* courses allocated to the logged-in teacher. Displays subject code, title, department, semester, assignments count, and an **"Open Subject"** action button.
- **Create Assignment Form**:
  - Title & description/instructions.
  - Attachment upload for reference guides/rubrics.
  - Deadline datetime picker (enforces deadline >= creation time).
  - Allowed file types whitelist (e.g. `pdf,doc,docx,zip`).
  - Max file size validation (MB).
  - Automatically targets eligible students whose department and semester match the course.
- **Student Submission Tracking ("View Submissions")**:
  - **Metric Counters**: Total Eligible Students, Submitted, Pending, Late Submissions, and Turn-in Rate Percentage with progress bar.
  - **Complete Roster Comparison**: Compares the student roster with submission records. Displays submitted students (with download link and grades) AND non-submitted students (flagged as `Pending / Awaiting Upload`). Each student is counted once.
  - **Live Search & Filter Tabs**: Filter dynamically by `All`, `Submitted`, `Pending`, or `Late`.
  - **Grading & Feedback Modal**: Faculty can enter scores (validated against `max_marks`) and personalized feedback comments.

### 2. Administrator Module
- **Dashboard**: High-level system statistics (faculty, students, subjects, submissions).
- **Manage Teachers**:
  - View all registered teachers with status badges and assigned subjects.
  - Add new teachers with multi-subject assignment.
  - On-screen modal to copy single-use activation links.
  - Edit teacher profile and course allocations.
  - One-click Activate / Deactivate toggles.
- **Subject Catalog Management**: Add and inspect course codes, departments, semesters, and credits.

### 3. Student Module
- **Self-Registration & Login**: Students can register with register number, department, semester, and section.
- **Student Dashboard**: Shows enrolled subjects matching their department and semester, along with active assignments.
- **Assignment View & Submission**:
  - Download teacher's reference guides.
  - Upload submission files with client-side and server-side size and extension validation.
  - Automatic `Late Submission` flag if submitted after deadline.
  - Inspect awarded grades and teacher feedback.

---

## Pre-configured Test Credentials

The database comes pre-seeded with realistic demonstration accounts:

| Role | Name | Email / Login ID | Password | Status / Course Allocation |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | System Admin | `admin@college.edu` | `Admin@123` | Full administration privileges |
| **Teacher** | Prof. Alan Turing | `alan.turing@college.edu` | `Teacher@123` | Active &bull; Assigned to **CS501** & **CS503** |
| **Teacher** | Dr. Ada Lovelace | `ada.lovelace@college.edu` | `Teacher@123` | Active &bull; Assigned to **CS502** |
| **Teacher** | Prof. Grace Hopper | `grace.hopper@college.edu` | `Teacher@123` | Inactive (Used to test inactive blocking & activation) |
| **Student** | John Doe | `john.doe@student.college.edu` (or `21CS001`) | `Student@123` | CSE Sem 5 &bull; Submitted for CS501 |
| **Student** | Jane Smith | `jane.smith@student.college.edu` (or `21CS002`) | `Student@123` | CSE Sem 5 &bull; Pending submission |
| **Student** | Robert Johnson | `robert.johnson@student.college.edu` (or `21CS003`) | `Student@123` | CSE Sem 5 &bull; Pending submission |
| **Student** | Emily Davis | `emily.davis@student.college.edu` (or `21IT001`) | `Student@123` | IT Sem 5 &bull; Not eligible for CS501 |

---

## Step-by-Step Windows & VS Code Setup Guide

### Prerequisites
- **Python 3.10+** (Tested on Python 3.14)
- **Visual Studio Code** (or any preferred IDE)
- Modern web browser (Chrome, Edge, Firefox)

### Step 1: Open the Project in VS Code
1. Launch VS Code.
2. Select **File -> Open Folder...** and choose:
   ```
   C:\Users\<YourUsername>\OneDrive\Desktop\csm
   ```

### Step 2: Open a PowerShell Terminal
In VS Code, press `` Ctrl + ` `` or go to **Terminal -> New Terminal**.

### Step 3: Install Required Dependencies
Run:
```powershell
pip install -r requirements.txt
```

### Step 4: Initialize and Seed the Database
Run the database initialization script to create tables and pre-populate test data:
```powershell
python init_db.py
```
*Output will display schema creation and pre-configured credentials.*

### Step 5: Start the Flask Application
Run:
```powershell
python app.py
```
You will see:
```
=================================================================
 Cloud-Based Assignment Submission and Tracking System (CSM) 
 Server running at: http://127.0.0.1:5000
=================================================================
```

### Step 6: Open the Application in your Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```
- For Teacher Login: `http://127.0.0.1:5000/teacher/login`
- For Admin Login: `http://127.0.0.1:5000/admin/login`
- For Student Login: `http://127.0.0.1:5000/student/login`

---

## Automated Testing Suite

The repository includes a comprehensive automated test suite `test_app.py` covering all 12 scenarios specified in the assignment requirements.

To run the tests:
```powershell
python test_app.py
```

### Test Scenarios Verified:
1. `test_01_admin_creates_teacher`: Admin creates a teacher account with employee ID, department, and assigned subjects; account starts as inactive with single-use activation link generated.
2. `test_02_teacher_activates_account`: Teacher visits activation link, sets a password, and the account transitions to active while token is invalidated.
3. `test_03_teacher_logs_in_successfully`: Authenticates with hashed password and redirects to Teacher Dashboard.
4. `test_04_incorrect_credentials_rejected`: Wrong passwords reject authentication with danger alerts.
5. `test_05_inactive_accounts_blocked`: Deactivated teachers are blocked from logging in.
6. `test_06_teacher_sees_only_assigned_subjects`: 'My Subjects' renders only the courses assigned to that specific teacher.
7. `test_07_teacher_publishes_assignment`: Teacher uploads reference materials and publishes an assignment with validation.
8. `test_08_eligible_students_see_assignment`: Assignment automatically appears for matching department/semester students and is hidden from other departments.
9. `test_09_roster_tracking_submitted_and_pending`: Submissions page calculates submitted vs. pending non-submitted students from class roster.
10. `test_10_teacher_downloads_file_and_grades`: Teacher downloads student submission files and records scores/feedback.
11. `test_11_student_blocked_from_teacher_routes`: Role-based authorization decorator blocks student accounts with `403 Forbidden`.
12. `test_12_teacher_cannot_access_other_teacher_assignments`: IDOR defense ensures faculty cannot view, edit, or grade assignments owned by other teachers.

---

## Security Architecture & Implementation

1. **Password Hashing**: Passwords are never stored in plain text. Stored using `Werkzeug`'s secure `pbkdf2:sha256` key derivation algorithm with unique cryptographic salt per user.
2. **Role-Based Authorization Decorators**: Protected routes enforce `@admin_required`, `@teacher_required`, and `@student_required`. If a user attempts to change URLs manually (e.g. student navigating to `/teacher/dashboard`), Flask aborts with `403 Forbidden`.
3. **Insecure Direct Object Reference (IDOR) Defenses**:
   - Every assignment modification or submission viewing route verifies that `assignment.teacher_id == current_teacher.id`.
   - Teachers cannot view or grade assignments belonging to other teachers.
4. **CSRF Protection**: All mutating requests (`POST`) enforce session CSRF validation tokens.
5. **Safe File Uploads & Traversal Prevention**:
   - Files are sanitized using `werkzeug.utils.secure_filename`.
   - Extensions checked against a strict whitelist (`pdf, doc, docx, zip`).
   - File size enforced on client and server (`MAX_CONTENT_LENGTH = 25MB`).
   - Private downloads verify identity before streaming files via `send_from_directory`.

---

## Database Schema

```mermaid
erDiagram
    USERS ||--o| TEACHERS : "has profile"
    USERS ||--o| STUDENTS : "has profile"
    USERS ||--o{ ACTIVATION_TOKENS : "has tokens"
    TEACHERS ||--o{ TEACHER_SUBJECTS : "teaches"
    SUBJECTS ||--o{ TEACHER_SUBJECTS : "assigned to"
    TEACHERS ||--o{ ASSIGNMENTS : "creates"
    SUBJECTS ||--o{ ASSIGNMENTS : "contains"
    ASSIGNMENTS ||--o{ SUBMISSIONS : "receives"
    STUDENTS ||--o{ SUBMISSIONS : "submits"

    USERS {
        int id PK
        string email UK
        string password_hash
        string role "admin|teacher|student"
        int is_active
        datetime created_at
    }

    TEACHERS {
        int id PK
        int user_id FK
        string name
        string employee_id UK
        string department
        string college
        string phone
    }

    STUDENTS {
        int id PK
        int user_id FK
        string register_no UK
        string name
        string department
        int semester
        string class_section
    }

    SUBJECTS {
        int id PK
        string subject_code UK
        string subject_name
        string department
        int semester
        int credits
    }

    ASSIGNMENTS {
        int id PK
        int subject_id FK
        int teacher_id FK
        string title
        text description
        string attachment_path
        int max_marks
        datetime deadline
    }

    SUBMISSIONS {
        int id PK
        int assignment_id FK
        int student_id FK
        string file_path
        datetime submitted_at
        int is_late
        float grade
        text feedback
    }
```

---

## AWS Cloud Deployment Guide

When taking this application from local development to production on **Amazon Web Services (AWS)**:

### 1. Amazon EC2 (Compute & Web Server)
1. **Launch EC2 Instance**: Choose Ubuntu 24.04 LTS or Amazon Linux 2023 (`t3.small` or `t3.medium`).
2. **Security Group Inbound Rules**:
   - Port 22 (SSH) - Your IP
   - Port 80 (HTTP) - Anywhere (`0.0.0.0/0`)
   - Port 443 (HTTPS) - Anywhere (`0.0.0.0/0`)
3. **Application Deployment**:
   ```bash
   sudo apt update && sudo apt install python3-pip python3-venv nginx -y
   git clone <your-repo-url> /var/www/csm
   cd /var/www/csm
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt gunicorn
   ```
4. **Gunicorn Systemd Service**: Create `/etc/systemd/system/csm.service`:
   ```ini
   [Unit]
   Description=Gunicorn instance to serve CSM Flask app
   After=network.target

   [Service]
   User=ubuntu
   Group=www-data
   WorkingDirectory=/var/www/csm
   Environment="PATH=/var/www/csm/venv/bin"
   ExecStart=/var/www/csm/venv/bin/gunicorn --workers 3 --bind unix:csm.sock -m 007 "app:create_app()"

   [Install]
   WantedBy=multi-user.target
   ```
5. **Nginx Reverse Proxy**: Configure `/etc/nginx/sites-available/csm` to proxy requests to `unix:/var/www/csm/csm.sock`.

### 2. Amazon S3 (Scalable Object Storage)
- Local disk uploads can be switched to S3 with zero code rewriting:
- In `.env`:
  ```ini
  USE_S3=True
  AWS_ACCESS_KEY_ID=AKIAxxxxxxxx
  AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxx
  AWS_REGION=us-east-1
  S3_BUCKET_NAME=college-csm-submissions
  ```
- `storage.py` automatically detects S3 configuration and streams attachments and submissions directly to Amazon S3 with pre-signed secure download URLs.

### 3. Amazon RDS for MySQL (Managed Database)
- In AWS RDS Console, create a MySQL 8.0 instance with Multi-AZ for high availability.
- Connect your EC2 instance Security Group to RDS Security Group on port 3306.
- Set environment variable:
  ```ini
  DATABASE_URL=mysql+pymysql://admin_user:YourStrongPassword@csm-rds.xxxx.us-east-1.rds.amazonaws.com:3306/csm_db
  ```

---

## Viva / Mini-Project Evaluation Q&A

**Q1: Why are teachers not allowed to self-register publicly?**
> *Answer*: Public registration would allow any student or outsider to create a faculty account and view examination solutions. Restricting teacher creation strictly to the authorized administrator ensures that only verified college faculty can post assignments and evaluate submissions.

**Q2: How does single-use token activation improve security?**
> *Answer*: If an admin sets a password, they know the teacher's credentials, creating a privacy issue. With single-use activation tokens, a cryptographically random token (`secrets.token_urlsafe(32)`) is generated. The teacher chooses their own confidential password. Once used, the token is marked `is_used = 1` and cannot be re-used.

**Q3: How are pending submissions calculated if a student hasn't submitted anything yet?**
> *Answer*: In SQL, a query fetches all eligible students whose department and semester match the subject. A second query fetches existing submissions. By comparing the eligible roster with submissions, non-submitted students are displayed with a "Pending" status badge, ensuring an accurate turn-in percentage:
> `Turn-in % = (Unique Submitted Students / Total Eligible Roster) * 100`.

**Q4: How does the application prevent unauthorized file downloads (IDOR)?**
> *Answer*: File downloads do not simply serve static files by filename. The route `/teacher/download/<file_type>/<id>` first verifies in the database that the logged-in teacher is the owner of the assignment linked to that submission. Unauthorized users receive an HTTP 403 Forbidden.

**Q5: How does the system handle database concurrency in SQLite?**
> *Answer*: SQLite connection initializes with `PRAGMA journal_mode = WAL;` (Write-Ahead Logging). This allows multiple concurrent readers while a write operation is occurring, significantly enhancing speed and concurrency.
