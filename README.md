# AI SAS - Smart Academic System

A Django + MySQL + Bootstrap portal for teachers, students and admins.

| Role | What they can do |
|------|------------------|
| Student | Enrol in courses, take timed exams, see marks, check date-wise attendance, open daily class material, see meetings |
| Faculty | Manage courses, schedule exams and questions, grade written answers, take attendance by date, upload class material, schedule meetings |
| Admin | Approve faculty, manage users, view/export subscribers, oversee courses (`/myadmin/`) |

Every page except the home, login, register and subscribe pages requires login, and each area (`/student/`, `/faculty/`, `/myadmin/`) is limited to its own role.

## 1. Copy the files

Copy everything in this folder into your project (`D:\pyproject\AI_SAS`), merging with the existing folders.

## 2. Create the MySQL database

```sql
CREATE DATABASE ai_sas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 3. Configure

Copy `.env.example` to `.env` and fill in the DB details, or set the same names as environment variables:

```
DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS,
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
```

`settings.py` reads environment variables. If you use a `.env` file, load it in your shell first
(or install `python-dotenv` and load it at the top of `settings.py`).

## 4. Install and run

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
python manage.py makemigrations anonymous faculty
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run `makemigrations anonymous faculty` **before the first `migrate`**: the custom user model
(`anonymous.User`) must be migrated before Django's admin tables.
If you already ran `migrate` against this database with the default user model, drop and recreate the database first.

`mysqlclient` on Windows normally installs from a wheel. If it fails, install a matching wheel or
the MySQL Connector C build tools.

## 5. First use

1. Log in at `/login/` with the superuser you created (it gets the admin role automatically) - you land on `/myadmin/`.
2. Students register at `/register/` and can log in immediately.
3. Faculty register at `/register/` but cannot log in until an admin approves them under **Users -> Approve**.
4. A teacher creates a course; students enrol from **My courses**.

## Notes

- Uploaded class material is stored in `media/` and served only through a permission-checked view
  (`/files/materials/<id>/`), never as a public URL.
- Allowed upload types and the 20 MB limit are set in `faculty/forms.py`.
- Written exam answers are graded by the teacher; multiple-choice answers are graded automatically.
  Correct answers are shown to students only after the exam window closes.
- Attendance percentage counts Present and Late as attended; below 75% is flagged.
- Static files: `python manage.py collectstatic` is only needed for production.
