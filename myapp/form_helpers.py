"""Server-side validation + duplicate checks shared by the superadmin and
teacher views.  Every validator returns ``(cleaned_data, error_message)``;
``error_message`` is ``None`` when the input is valid.
"""
import csv
import io
import re
from datetime import date, datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.db.models import Sum

from .models import (
    Announcement, Question_bank, Test, TaskSubmit, tbl_assignment, tbl_course,
    tbl_session, tbl_student, tbl_StudyMaterial, tbl_subject, tbl_teacher,
)

MOBILE_RE = re.compile(r"^\d{10}$")
USERNAME_RE = re.compile(r"^[\w.@+-]{3,50}$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,99}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-/]{0,49}$")

MATERIAL_EXT = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
                ".txt", ".md", ".zip", ".png", ".jpg", ".jpeg", ".mp4", ".csv"}
ASSIGNMENT_EXT = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
                  ".txt", ".zip", ".png", ".jpg", ".jpeg", ".py", ".java",
                  ".c", ".cpp", ".html", ".css", ".js", ".md"}
MAX_UPLOAD_MB = 25

STATUS_CHOICES = {"Active", "Inactive"}


# ------------------------------------------------------------------ basics
def clean(value):
    """Strip + collapse stray whitespace; ``None`` becomes ''."""
    return (value or "").strip()


def valid_email(value):
    try:
        validate_email(value)
        return True
    except ValidationError:
        return False


def valid_url(value):
    try:
        URLValidator(schemes=["http", "https"])(value)
        return True
    except ValidationError:
        return False


def parse_int(value, minimum=None, maximum=None):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    return number


def parse_date(value):
    try:
        return datetime.strptime(clean(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_time(value):
    value = clean(value)
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def check_upload(file, allowed_ext, label="File"):
    """Return an error string for a bad upload, else None."""
    if not file:
        return None
    name = file.name.lower()
    ext = name[name.rfind("."):] if "." in name else ""
    if ext not in allowed_ext:
        return f"{label}: '{ext or 'no extension'}' files are not allowed."
    if file.size > MAX_UPLOAD_MB * 1024 * 1024:
        return f"{label} is too large (max {MAX_UPLOAD_MB} MB)."
    return None


def read_csv_upload(file):
    """Return (rows, error) for an uploaded CSV file."""
    if not file:
        return None, "Please choose a CSV file."
    if not file.name.lower().endswith(".csv"):
        return None, "Only .csv files are allowed."
    if file.size > 5 * 1024 * 1024:
        return None, "CSV file is too large (max 5 MB)."
    try:
        text = file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "CSV file must be UTF-8 encoded."
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return None, "CSV file is empty."
    reader.fieldnames = [clean(h) for h in reader.fieldnames]
    return reader, None


def csv_missing_columns(reader, required):
    missing = [c for c in required if c not in (reader.fieldnames or [])]
    if missing:
        return "CSV is missing column(s): " + ", ".join(missing)
    return None


def summarize_import(label, added, skipped):
    """Build a user-facing message for bulk imports."""
    msg = f"{added} {label} added."
    if skipped:
        shown = "; ".join(skipped[:5])
        extra = f" (+{len(skipped) - 5} more)" if len(skipped) > 5 else ""
        msg += f" {len(skipped)} row(s) skipped: {shown}{extra}"
    return msg


# --------------------------------------------------------- users / duplicates
def username_taken(username, exclude_user=None):
    qs = User.objects.filter(username__iexact=username)
    if exclude_user is not None:
        qs = qs.exclude(pk=exclude_user.pk)
    return qs.exists()


def email_taken(email, exclude_student=None, exclude_teacher=None):
    students = tbl_student.objects.filter(email__iexact=email)
    teachers = tbl_teacher.objects.filter(email__iexact=email)
    if exclude_student is not None:
        students = students.exclude(pk=exclude_student.pk)
    if exclude_teacher is not None:
        teachers = teachers.exclude(pk=exclude_teacher.pk)
    return students.exists() or teachers.exists()


def mobile_taken(mobile, exclude_student=None, exclude_teacher=None):
    students = tbl_student.objects.filter(mobile=mobile)
    teachers = tbl_teacher.objects.filter(mobile=mobile)
    if exclude_student is not None:
        students = students.exclude(pk=exclude_student.pk)
    if exclude_teacher is not None:
        teachers = teachers.exclude(pk=exclude_teacher.pk)
    return students.exists() or teachers.exists()


def _password_error(password):
    if len(password) < 6:
        return "Password must be at least 6 characters."
    if len(password) > 16:
        return "Password must be at most 16 characters."
    return None


# ------------------------------------------------------------------ session
def validate_session(post, exclude_id=None):
    data = {
        "session_name": clean(post.get("session_name")),
        "status": clean(post.get("status")),
        "strt_date": parse_date(post.get("strt_date")),
        "end_date": parse_date(post.get("end_date")),
    }
    if not data["session_name"]:
        return data, "Session name is required."
    if len(data["session_name"]) > 100:
        return data, "Session name is too long (max 100 characters)."
    if not data["status"]:
        return data, "Please select a status."
    if not data["strt_date"] or not data["end_date"]:
        return data, "Please enter valid start and end dates."
    if data["end_date"] <= data["strt_date"]:
        return data, "End date must be after the start date."
    dup = tbl_session.objects.filter(session_name__iexact=data["session_name"])
    if exclude_id:
        dup = dup.exclude(id=exclude_id)
    if dup.exists():
        return data, "This session already exists."
    return data, None


# ------------------------------------------------------------------- course
def validate_course(post, exclude_id=None):
    data = {k: clean(post.get(k)) for k in
            ("session", "course_code", "course_name", "level", "duration",
             "status", "description")}
    for key, label in (("session", "Session"), ("course_code", "Course code"),
                       ("course_name", "Course name"), ("level", "Level"),
                       ("duration", "Duration"), ("status", "Status")):
        if not data[key]:
            return data, f"{label} is required."
    if len(data["course_code"]) > 100 or len(data["course_name"]) > 200:
        return data, "Course code or name is too long."
    base = tbl_course.objects.all()
    if exclude_id:
        base = base.exclude(id=exclude_id)
    if base.filter(course_code__iexact=data["course_code"]).exists():
        return data, "This course code already exists."
    if base.filter(course_name__iexact=data["course_name"]).exists():
        return data, "This course name already exists."
    return data, None


# ------------------------------------------------------------------ teacher
def validate_teacher(post, instance=None, require_password=True):
    """``instance`` is the tbl_teacher being edited (None when adding)."""
    data = {k: clean(post.get(k)) for k in
            ("employee_id", "name", "email", "mobile", "department",
             "designation", "username", "status")}
    data["password"] = post.get("password") or ""
    exclude_user = instance.user if instance else None

    if instance is None:
        emp = parse_int(data["employee_id"], minimum=1)
        if emp is None:
            return data, "Employee ID must be a positive number."
        data["employee_id"] = emp
        if tbl_teacher.objects.filter(employee_id=emp).exists():
            return data, "Employee ID already exists."
    if not NAME_RE.match(data["name"]):
        return data, "Enter a valid name (letters, spaces, . ' - only)."
    if not valid_email(data["email"]):
        return data, "Enter a valid email address."
    if not MOBILE_RE.match(data["mobile"]):
        return data, "Mobile number must be exactly 10 digits."
    if not data["department"] or not data["designation"]:
        return data, "Department and designation are required."
    if not USERNAME_RE.match(data["username"]):
        return data, ("Username must be 3-50 characters (letters, digits and "
                      "@ . + - _ only).")
    if not data["status"]:
        return data, "Please select a status."
    if data["password"] or require_password:
        err = _password_error(data["password"])
        if err:
            return data, err
    if email_taken(data["email"], exclude_teacher=instance):
        return data, "This email is already registered."
    if mobile_taken(data["mobile"], exclude_teacher=instance):
        return data, "This mobile number is already registered."
    if username_taken(data["username"], exclude_user=exclude_user):
        return data, "Username already exists."
    return data, None


# ------------------------------------------------------------------ subject
def validate_subject(post, exclude_id=None):
    data = {k: clean(post.get(k)) for k in
            ("course", "subject_code", "subject_name", "semester", "teacher",
             "status", "description")}
    credits = parse_int(post.get("credits"), minimum=1, maximum=30)
    data["credits"] = credits
    for key, label in (("course", "Course"), ("subject_code", "Subject code"),
                       ("subject_name", "Subject name"),
                       ("semester", "Semester"), ("status", "Status")):
        if not data[key]:
            return data, f"{label} is required."
    if credits is None:
        return data, "Credits must be a number between 1 and 30."
    base = tbl_subject.objects.all()
    if exclude_id:
        base = base.exclude(id=exclude_id)
    if base.filter(subject_code__iexact=data["subject_code"]).exists():
        return data, "This subject code already exists."
    if base.filter(course=data["course"], semester=data["semester"],
                   subject_name__iexact=data["subject_name"]).exists():
        return data, "This subject already exists for the selected course and semester."
    return data, None


# ------------------------------------------------------------------ student
STUDENT_COLUMNS = ["Enrollment_no", "name", "email", "mobile", "course",
                   "session", "sem", "username", "password", "status"]


def validate_student(post, instance=None, require_password=True):
    """``post`` can be a QueryDict or a CSV row dict."""
    data = {k: clean(post.get(k)) for k in
            ("Enrollment_no", "name", "email", "mobile", "course", "session",
             "sem", "username", "status")}
    data["password"] = (post.get("password") or "").strip()
    exclude_user = instance.user if instance else None

    if instance is None:
        if not ID_RE.match(data["Enrollment_no"]):
            return data, "Enter a valid Enrollment No. (letters, digits, - _ /)."
        if tbl_student.objects.filter(
                Enrollment_no__iexact=data["Enrollment_no"]).exists():
            return data, "Student with this Enrollment No. already exists."
    if not NAME_RE.match(data["name"]):
        return data, "Enter a valid name (letters, spaces, . ' - only)."
    if not valid_email(data["email"]):
        return data, "Enter a valid email address."
    if not MOBILE_RE.match(data["mobile"]):
        return data, "Mobile number must be exactly 10 digits."
    for key, label in (("course", "Course"), ("session", "Session"),
                       ("sem", "Semester"), ("status", "Status")):
        if not data[key]:
            return data, f"{label} is required."
    if not USERNAME_RE.match(data["username"]):
        return data, ("Username must be 3-50 characters (letters, digits and "
                      "@ . + - _ only).")
    if data["password"] or require_password:
        err = _password_error(data["password"])
        if err:
            return data, err
    if email_taken(data["email"], exclude_student=instance):
        return data, "This email is already registered."
    if mobile_taken(data["mobile"], exclude_student=instance):
        return data, "This mobile number is already registered."
    if username_taken(data["username"], exclude_user=exclude_user):
        return data, "Username already exists."
    return data, None


# ----------------------------------------------------------- study material
def validate_material(post, files, exclude_id=None, existing=None):
    data = {k: clean(post.get(k)) for k in
            ("title", "material_type", "course", "subject", "external_url",
             "status", "description")}
    upload = files.get("material_file") or files.get("file")
    for key, label in (("title", "Title"), ("material_type", "Material type"),
                       ("course", "Course"), ("subject", "Subject")):
        if not data[key]:
            return data, f"{label} is required."
    if len(data["title"]) > 200:
        return data, "Title is too long (max 200 characters)."
    if not data["status"]:
        data["status"] = "Published"
    if data["external_url"] and not valid_url(data["external_url"]):
        return data, "Enter a valid link starting with http:// or https://"
    err = check_upload(upload, MATERIAL_EXT, "Study material file")
    if err:
        return data, err
    has_old_file = bool(existing and existing.material_file)
    if not upload and not data["external_url"] and not has_old_file:
        return data, "Please upload a file or provide a link."
    dup = tbl_StudyMaterial.objects.filter(
        title__iexact=data["title"], course=data["course"],
        subject=data["subject"])
    if exclude_id:
        dup = dup.exclude(id=exclude_id)
    if dup.exists():
        return data, "This study material already exists for the selected course and subject."
    data["upload"] = upload
    return data, None


# --------------------------------------------------------------- assignment
def validate_assignment(post, files, exclude_id=None):
    data = {k: clean(post.get(k)) for k in
            ("title", "course", "subject", "status", "instructions")}
    data["due_date"] = parse_date(post.get("due_date"))
    data["total_marks"] = parse_int(post.get("total_marks"), 1, 1000)
    upload = files.get("attachment")
    for key, label in (("title", "Title"), ("course", "Course"),
                       ("subject", "Subject"), ("status", "Status")):
        if not data[key]:
            return data, f"{label} is required."
    if len(data["title"]) > 200:
        return data, "Title is too long (max 200 characters)."
    if data["due_date"] is None:
        return data, "Please enter a valid due date."
    if data["total_marks"] is None:
        return data, "Total marks must be a number between 1 and 1000."
    err = check_upload(upload, ASSIGNMENT_EXT, "Attachment")
    if err:
        return data, err
    dup = tbl_assignment.objects.filter(
        title__iexact=data["title"], course=data["course"],
        subject=data["subject"])
    if exclude_id:
        dup = dup.exclude(id=exclude_id)
    if dup.exists():
        return data, "This assignment already exists for the selected course and subject."
    data["upload"] = upload
    return data, None


# --------------------------------------------------------------------- test
def validate_test(post):
    data = {
        "test_title": clean(post.get("title")),
        "test_date": parse_date(post.get("test_date")),
        "course": clean(post.get("course")),
        "subject": clean(post.get("subject")),
        "state_time": parse_time(post.get("start_time")),
        "duration": parse_int(post.get("duration_minutes"), 1, 600),
        "total_marks": parse_int(post.get("total_marks"), 1, 1000),
        "status": clean(post.get("status")),
    }
    if not data["test_title"]:
        return data, "Test title is required."
    if len(data["test_title"]) > 200:
        return data, "Test title is too long (max 200 characters)."
    if not data["course"] or not data["subject"]:
        return data, "Please select a course and a subject."
    if data["test_date"] is None:
        return data, "Please enter a valid test date."
    if data["state_time"] is None:
        return data, "Please enter a valid start time."
    if data["duration"] is None:
        return data, "Duration must be between 1 and 600 minutes."
    if data["total_marks"] is None:
        return data, "Total marks must be a number between 1 and 1000."
    if not data["status"]:
        return data, "Please select a status."
    if Test.objects.filter(
            test_title__iexact=data["test_title"], course=data["course"],
            subject=data["subject"], test_date=data["test_date"]).exists():
        return data, "A test with the same title, course, subject and date already exists."
    return data, None


# ----------------------------------------------------------------- question
def validate_question(row, test):
    data = {
        "question": clean(row.get("question")),
        "option_a": clean(row.get("option_a")),
        "option_b": clean(row.get("option_b")),
        "option_c": clean(row.get("option_c")),
        "option_d": clean(row.get("option_d")),
        "correct_option": clean(row.get("correct_option")).upper(),
        "marks": parse_int(row.get("marks"), 1, 100),
    }
    if not data["question"]:
        return data, "Question text is required."
    options = [data[k] for k in ("option_a", "option_b", "option_c", "option_d")]
    if not all(options):
        return data, "All four options are required."
    if any(len(o) > 200 for o in options):
        return data, "Each option must be 200 characters or fewer."
    if len({o.lower() for o in options}) != 4:
        return data, "All four options must be different."
    if data["correct_option"] not in {"A", "B", "C", "D"}:
        return data, "Correct option must be A, B, C or D."
    if data["marks"] is None:
        return data, "Marks must be a number between 1 and 100."
    if Question_bank.objects.filter(
            test=test, question__iexact=data["question"]).exists():
        return data, "This question already exists in this test."
    used = Question_bank.objects.filter(test=test).aggregate(
        total=Sum("marks"))["total"] or 0
    if used + data["marks"] > test.total_marks:
        return data, (f"Total question marks would exceed the test's total "
                      f"marks ({test.total_marks}); {used} already used.")
    return data, None


def import_questions(test, file):
    """Bulk-create questions from a CSV. Returns (message, level)."""
    reader, err = read_csv_upload(file)
    if err:
        return err, "error"
    err = csv_missing_columns(
        reader, ["question", "option_a", "option_b", "option_c", "option_d",
                 "correct_option", "marks"])
    if err:
        return err, "error"
    added, skipped = 0, []
    for line_no, row in enumerate(reader, start=2):
        data, row_err = validate_question(row, test)
        if row_err:
            skipped.append(f"row {line_no}: {row_err}")
            continue
        Question_bank.objects.create(test=test, **data)
        added += 1
    level = "success" if added else "error"
    return summarize_import("question(s)", added, skipped), level


# ------------------------------------------------------------- announcement
AUDIENCES = {"All", "Students", "Teachers"}
PRIORITIES = {"Normal", "Important", "Urgent"}


def validate_announcement(post):
    data = {
        "title": clean(post.get("title")),
        "audience": clean(post.get("audience")),
        "priority": clean(post.get("priority")),
        "publish_date": parse_date(post.get("publish_date")),
        "message": clean(post.get("message")),
        "expiry_date": None,
    }
    expiry_raw = clean(post.get("expiry_date"))
    if not data["title"]:
        return data, "Title is required."
    if len(data["title"]) > 200:
        return data, "Title is too long (max 200 characters)."
    if data["audience"] not in AUDIENCES:
        return data, "Please select a valid audience."
    if data["priority"] not in PRIORITIES:
        return data, "Please select a valid priority."
    if data["publish_date"] is None:
        return data, "Please enter a valid publish date."
    if expiry_raw:
        data["expiry_date"] = parse_date(expiry_raw)
        if data["expiry_date"] is None:
            return data, "Please enter a valid expiry date."
        if data["expiry_date"] < data["publish_date"]:
            return data, "Expiry date cannot be before the publish date."
    if not data["message"]:
        return data, "Message is required."
    if Announcement.objects.filter(
            title__iexact=data["title"], audience=data["audience"],
            publish_date=data["publish_date"],
            message=data["message"]).exists():
        return data, "This announcement has already been published."
    return data, None


# --------------------------------------------------------------- submission
def validate_submission(assignment, student_user, upload):
    if not upload:
        return "Please choose a file to submit."
    err = check_upload(upload, ASSIGNMENT_EXT, "Submitted file")
    if err:
        return err
    if TaskSubmit.objects.filter(task=assignment, student=student_user).exists():
        return "You have already submitted this assignment."
    return None
