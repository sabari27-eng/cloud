"""Check the live database for teacher/subject data."""
from app import create_app
app = create_app()
with app.app_context():
    from database import query_db

    teachers = query_db('''SELECT t.id, t.name, t.employee_id, u.email, u.is_active
                           FROM teachers t JOIN users u ON t.user_id = u.id''')
    print('Teachers:')
    for t in teachers:
        print(f"  ID={t['id']} | {t['name']} | {t['email']} | active={t['is_active']}")

    ts = query_db('SELECT teacher_id, subject_id FROM teacher_subjects')
    print('Teacher-Subject assignments:')
    for row in ts:
        print(f"  teacher_id={row['teacher_id']} -> subject_id={row['subject_id']}")

    subjects = query_db('SELECT id, subject_code, subject_name FROM subjects')
    print('Subjects:')
    for s in subjects:
        print(f"  ID={s['id']} | {s['subject_code']} | {s['subject_name']}")

    assignments = query_db('SELECT id, subject_id, teacher_id, title FROM assignments')
    print('Assignments:')
    for a in assignments:
        print(f"  ID={a['id']} | subject_id={a['subject_id']} | teacher_id={a['teacher_id']} | {a['title']}")

    submissions = query_db('SELECT id, assignment_id, student_id FROM submissions')
    print('Submissions:')
    for sub in submissions:
        print(f"  ID={sub['id']} | assignment_id={sub['assignment_id']} | student_id={sub['student_id']}")
