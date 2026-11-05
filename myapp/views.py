from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import*
from django.utils import timezone
from datetime import date, datetime
from django.contrib.auth.decorators import login_required
import csv
from django.db import IntegrityError, transaction

from datetime import date

from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.models import User
from django.apps import apps

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.apps import meet_v2

from django.views.decorators.cache import cache_control
from .compiler_helper import LANGUAGES, STARTER_CODE, run_code
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from .compiler_helper import LANGUAGES, STARTER_CODE, run_code

import json
from .form_helpers import (
    STUDENT_COLUMNS, csv_missing_columns, import_questions, read_csv_upload,
    summarize_import, validate_announcement, validate_assignment,
    validate_course, validate_material, validate_question, validate_session,
    validate_student, validate_subject, validate_submission, validate_teacher,
    validate_test,
)

# Google Meet integration lives in google_meet.py; keep URL-facing names here.
from .google_meet import (
    google_login, google_callback, schedule_meeting, start_meeting,
    student_classes, join_meeting, teacher_meetings, superadmin_meetings,
)
from .models import GoogleMeeting


# =========================
# LOGIN
# =========================
def home(request):

    if request.method == 'POST':

        try:
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')

            # Empty fields validation
            if not username or not password:
                messages.error(request,"Please enter username and password.")
                return render(request, 'login.html')

            # Authenticate user
            user = authenticate(
                request,
                username=username,
                password=password
            )

            # Wrong username/password
            if user is None:
                messages.error(request,"Username and password is invalid.")
                return render(request, 'login.html')

            # =========================
            # SUPER ADMIN
            # =========================
            if user.is_superuser:

                login(request, user)
                messages.success(request,"Login Successful")
                return redirect('superadmindash')

            # =========================
            # TEACHER
            # =========================
            elif hasattr(user, 'Teacher'):
                login(request, user)
                messages.success(request,"Login Successful")
                return redirect('tdash')

            # =========================
            # STUDENT
            # =========================
            elif hasattr(user, 'Student'):
                login(request, user)
                messages.success(request,"Login Successful")
                return redirect('sdashboard')

            # =========================
            # NO ROLE
            # =========================
            else:
                messages.error(request,"Your account does not have any assigned role.")
                return render(request, 'login.html')

        except Exception as e:
            messages.error(request,"Something went wrong. Please try again.")
            return render(request, 'login.html')

    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect("home")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required

@login_required
def superadmindash(request):

    # ==============================
    # BASIC COUNTS
    # ==============================

    total_students = tbl_student.objects.count()

    total_sessions = tbl_session.objects.count()

    active_courses = tbl_course.objects.filter(
        status="Active"
    ).count()

    total_teachers = tbl_teacher.objects.count()

    active_subjects = tbl_subject.objects.filter(
        status="Active"
    ).count()


    # ==============================
    # ONLINE CLASSES
    # ==============================

    online_classes = GoogleMeeting.objects.filter(
        status="scheduled",
        class_date__gte=timezone.now().date()
    ).count()

    upcoming_classes = GoogleMeeting.objects.filter(
        status="scheduled",
        class_date__gte=timezone.now().date()
    ).order_by(
        "class_date",
        "class_time"
    )[:5]


    # ==============================
    # ANNOUNCEMENTS
    # ==============================

    latest_announcements = Announcement.objects.all().order_by(
        "-publish_date",
        "-id"
    )[:5]


    # ==============================
    # ASSIGNMENTS
    # ==============================

    total_assignments = tbl_assignment.objects.count()

    pending_assignments = TaskSubmit.objects.filter(
        status="Submitted"
    ).count()

    evaluated_assignments = TaskSubmit.objects.filter(
        status="Evaluated"
    ).count()

    total_submissions = TaskSubmit.objects.count()


    # ==============================
    # TESTS
    # ==============================

    total_assessments = Test.objects.count()

    total_questions = Question_bank.objects.count()

    total_test_results = TestResult.objects.count()


    # ==============================
    # DASHBOARD CONTEXT
    # ==============================

    context = {

        # Basic
        "total_students": total_students,
        "total_sessions": total_sessions,
        "active_courses": active_courses,
        "total_teachers": total_teachers,
        "active_subjects": active_subjects,

        # Classes
        "online_classes": online_classes,
        "upcoming_classes": upcoming_classes,

        # Announcements
        "latest_announcements": latest_announcements,

        # Assignments
        "total_assignments": total_assignments,
        "total_submissions": total_submissions,
        "pending_assignments": pending_assignments,
        "evaluated_assignments": evaluated_assignments,

        # Tests
        "total_assessments": total_assessments,
        "total_questions": total_questions,
        "total_test_results": total_test_results,
    }

    return render(
        request,
        "superadmin/dashboard.html",
        context
    )

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def superbase(request):
    return render(request,"superadmin/base.html")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def addsession(request):
    if request.method == "POST":
        data, error = validate_session(request.POST)
        if error:
            messages.error(request, error)
        else:
            tbl_session.objects.create(**data, Dor=timezone.now())
            messages.success(request, "Your session is Successfully Uploaded")
            return redirect("addsession")

    return render(request, 'superadmin/addsession.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def showsession(request):
    sessions=tbl_session.objects.all()
    return render(request,'superadmin/showsession.html',{'sessions':sessions})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def editsession(request,id):
    session = get_object_or_404(tbl_session, id=id)

    if request.method == "POST":
        data, error = validate_session(request.POST, exclude_id=session.id)
        if error:
            messages.error(request, error)
        else:
            for key, value in data.items():
                setattr(session, key, value)
            session.save()
            messages.success(request,"Session updated successfully.")
            return redirect("showsession")
    return render(request,"superadmin/editsession.html",{"session": session})

@login_required
def deletesession(request,id):
    session = get_object_or_404(tbl_session, id=id)
    session.delete()

    messages.success(request, "Session deleted successfully.")
    return redirect("showsession")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def addcourse(request):

    sessions = tbl_session.objects.all()

    if request.method == "POST":
        data, error = validate_course(request.POST)
        if error:
            messages.error(request, error)
        else:
            tbl_course.objects.create(**data, Dor=timezone.now())
            messages.success(request,"Your course is Successfully Uploaded")
            return redirect("addcourse")

    return render(request,"superadmin/addcourse.html",{"sessions": sessions})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def viewcourse(request):
    courses = tbl_course.objects.all()
    return render(request,"superadmin/viewcourse.html",{"courses": courses})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def editcourse(request, id):
    course = get_object_or_404(tbl_course, id=id)
    sessions = tbl_session.objects.all()
    if request.method == "POST":
        data, error = validate_course(request.POST, exclude_id=course.id)
        if error:
            messages.error(request, error)
        else:
            for key, value in data.items():
                setattr(course, key, value)
            course.save()
            messages.success(request, "Course updated successfully.")
            return redirect("viewcourse")
    return render(request,"superadmin/editcourse.html",{"course": course,"sessions": sessions})


@login_required
def deletecourse(request, id):
    course = get_object_or_404(tbl_course, id=id)
    course.delete()
    messages.success(request, "Course deleted successfully.")
    return redirect("viewcourse")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def addteacher(request):

    if request.method == "POST":
        data, error = validate_teacher(request.POST)
        if error:
            messages.error(request, error)
        else:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=data["username"],
                        password=data["password"],
                        email=data["email"]
                    )
                    tbl_teacher.objects.create(
                        user=user, Dor=timezone.now(), **data
                    )
                messages.success(request,"Teacher is Successfully Added")
                return redirect("addteacher")
            except IntegrityError:
                messages.error(request, "Teacher already exists.")

    return render(request,"superadmin/addteacher.html")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def viewteacher(request):
    teachers = tbl_teacher.objects.all()
    return render(request,"superadmin/viewteacher.html",{"teachers": teachers})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def bulkteacher(request):

    if request.method == 'POST':
        reader, error = read_csv_upload(request.FILES.get('csv_file'))
        if not error:
            error = csv_missing_columns(reader, [
                "employee_id", "name", "email", "mobile", "department",
                "designation", "username", "password", "status"])
        if error:
            messages.error(request, error)
        else:
            added, skipped = 0, []
            for line_no, row in enumerate(reader, start=2):
                data, row_error = validate_teacher(row)
                if row_error:
                    skipped.append(f"row {line_no}: {row_error}")
                    continue
                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username=data["username"],
                            password=data["password"],
                            email=data["email"]
                        )
                        tbl_teacher.objects.create(
                            user=user, Dor=timezone.now(), **data
                        )
                    added += 1
                except IntegrityError:
                    skipped.append(f"row {line_no}: duplicate record")
            level = messages.success if added else messages.error
            level(request, summarize_import("teacher(s)", added, skipped))

    return render(request,'superadmin/bulkteacher.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def editteacher(request, employee_id):
    teacher = get_object_or_404(tbl_teacher, employee_id=employee_id)
    if request.method == "POST":
        data, error = validate_teacher(
            request.POST, instance=teacher, require_password=False)
        if error:
            messages.error(request, error)
        else:
            with transaction.atomic():
                for key in ("name", "email", "mobile", "department",
                            "designation", "username", "status"):
                    setattr(teacher, key, data[key])
                user = teacher.user
                user.username = data["username"]
                user.email = data["email"]
                if data["password"]:
                    teacher.password = data["password"]
                    user.set_password(data["password"])
                user.save()
                teacher.save()
            messages.success(request, "Teacher is Successfully Updated")
            return redirect("viewteacher")

    return render(request,"superadmin/editteacher.html",{"teacher": teacher})

@login_required
def deleteteacher(request, employee_id):

    teacher = get_object_or_404(tbl_teacher, employee_id=employee_id)
    teacher.user.delete()   # also removes the teacher row (cascade) and frees the username
    messages.success(request, "Teacher deleted successfully.")
    return redirect("viewteacher")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def addsubject(request):

    courses = tbl_course.objects.all()
    teachers = tbl_teacher.objects.all()
    if request.method == "POST":
        data, error = validate_subject(request.POST)
        if error:
            messages.error(request, error)
        else:
            tbl_subject.objects.create(**data, Dor=timezone.now())
            messages.success(request,"Subject is Successfully Added")
            return redirect("viewsubject")

    return render(request,"superadmin/addsubject.html",{"courses": courses,"teachers": teachers})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required    
def viewsubject(request):
    
    subjects = tbl_subject.objects.all()
    return render(request,"superadmin/viewsubject.html",{"subjects": subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def editsubject(request, id):
    subject = get_object_or_404(tbl_subject, id=id)
    courses = tbl_course.objects.all()
    teachers = tbl_teacher.objects.all()
    if request.method == "POST":
        data, error = validate_subject(request.POST, exclude_id=subject.id)
        if error:
            messages.error(request, error)
        else:
            for key, value in data.items():
                setattr(subject, key, value)
            subject.save()
            messages.success(request,"Subject updated successfully.")
            return redirect("viewsubject")
    return render(request,"superadmin/editsubject.html",{"subject": subject,"courses": courses,"teachers": teachers})

@login_required
def deletesubject(request, id):
    subject = get_object_or_404(tbl_subject, id=id)
    subject.delete()
    messages.success(request,"Subject deleted successfully.")
    return redirect("viewsubject")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def addstudent(request):

    sessions = tbl_session.objects.all()
    courses = tbl_course.objects.all()

    if request.method == 'POST':

        # Bulk CSV Upload
        file = request.FILES.get('csv_file')

        if file:
            reader, error = read_csv_upload(file)
            if not error:
                error = csv_missing_columns(reader, STUDENT_COLUMNS)
            if error:
                messages.error(request, error)
            else:
                added, skipped = 0, []
                for line_no, row in enumerate(reader, start=2):
                    data, row_error = validate_student(row)
                    if row_error:
                        skipped.append(f"row {line_no}: {row_error}")
                        continue
                    try:
                        with transaction.atomic():
                            user = User.objects.create_user(
                                username=data["username"],
                                password=data["password"],
                                email=data["email"]
                            )
                            tbl_student.objects.create(user=user, **data)
                        added += 1
                    except IntegrityError:
                        skipped.append(f"row {line_no}: duplicate record")
                level = messages.success if added else messages.error
                level(request, summarize_import("student(s)", added, skipped))

        # Single Student
        else:
            data, error = validate_student(request.POST)
            if error:
                messages.error(request, error)
            else:
                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username=data["username"],
                            password=data["password"],
                            email=data["email"]
                        )
                        tbl_student.objects.create(user=user, **data)
                    messages.success(request,"Student added successfully.")
                    return redirect("addstudent")
                except IntegrityError:
                    messages.error(request, "Student already exists.")

    return render(request,'superadmin/addstudent.html',{'sessions': sessions,'courses': courses})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def viewstudent(request):
    students=tbl_student.objects.all()
    return render(request,"superadmin/viewstudent.html",{'students':students})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def editstudent(request,Enrollment_no):

    student = get_object_or_404(tbl_student, Enrollment_no=Enrollment_no)
    sessions = tbl_session.objects.all()
    courses = tbl_course.objects.all()
    if request.method == "POST":

        post = request.POST.copy()
        post["sem"] = request.POST.get("semester", "")
        data, error = validate_student(
            post, instance=student, require_password=False)
        if error:
            messages.error(request, error)
        else:
            # The Enrollment No. is the primary key and can never be edited
            with transaction.atomic():
                for key in ("name", "email", "mobile", "session", "course",
                            "sem", "username", "status"):
                    setattr(student, key, data[key])
                user = student.user
                user.username = data["username"]
                user.email = data["email"]
                if data["password"]:
                    student.password = data["password"]
                    user.set_password(data["password"])
                user.save()
                student.save()
            messages.success(request,"Updated successfully.")
            return redirect("viewstudent")

    return render(request,"superadmin/editstudent.html",{
            "student": student,
            "sessions": sessions,
            "courses": courses
        })
    
@login_required
def deletestudent(request, Enrollment_no):

    student = get_object_or_404(tbl_student, Enrollment_no=Enrollment_no)
    student.user.delete()   # also removes the student row (cascade) and frees the username
    messages.success(request, "Student deleted successfully.")
    return redirect("viewstudent")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def uploadsm(request):
    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_material(request.POST, request.FILES)
        if error:
            messages.error(request, error)
        else:
            upload = data.pop("upload")
            tbl_StudyMaterial.objects.create(
                material_file=upload,
                create_by=request.user,
                **{**data, "external_url": data["external_url"] or None}
            )
            messages.success(request,"your study material successfully uploaded")
            return redirect("uploadsm")
    return render(request,'superadmin/uploadsm.html',{'courses':courses,'subjects':subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def viewsm(request):
    materials = tbl_StudyMaterial.objects.all()

    material_type = request.GET.get("material_type", "")
    search = request.GET.get("search", "")

    if material_type:
        materials = materials.filter(material_type=material_type)

    if search:
        materials = materials.filter(title__icontains=search)

    return render(
        request,
        "superadmin/viewsm.html",
        {
            "materials": materials,
            "selected_type": material_type,
            "search": search,
        }
    )

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def editsm(request,id):

    material = get_object_or_404(tbl_StudyMaterial, id=id)

    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_material(
            request.POST, request.FILES, exclude_id=material.id,
            existing=material)
        if error:
            messages.error(request, error)
        else:
            upload = data.pop("upload")
            for key, value in data.items():
                setattr(material, key, value or None if key == "external_url" else value)
            if upload:
                material.material_file = upload
            material.save()
            messages.success(request, "StudyMaterial updated successfully.")
            return redirect("viewsm")
    return render(request,"superadmin/editsm.html",{"material": material,"courses": courses,"subjects": subjects})


@login_required
def deletesm(request, id):
    material = get_object_or_404(tbl_StudyMaterial, id=id)
    material.delete()
    messages.success(request, "StudyMaterial deleted successfully.")
    return redirect("viewsm")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def addtask(request):

    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_assignment(request.POST, request.FILES)
        if error:
            messages.error(request, error)
        else:
            upload = data.pop("upload")
            tbl_assignment.objects.create(
                attachment=upload,
                create_by=request.user,
                Dor=timezone.now(),
                **data
            )
            messages.success(request,"Assignment successfully created")
            return redirect("addtask")
    return render(request,"superadmin/addtask.html",{"courses": courses,"subjects": subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def viewtask(request):
    assignments = tbl_assignment.objects.all()
    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()
    return render(request,"superadmin/viewtask.html",{"assignments": assignments,"courses": courses,"subjects": subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def edittask(request, id):

    task = get_object_or_404(tbl_assignment, id=id)

    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_assignment(
            request.POST, request.FILES, exclude_id=task.id)
        if error:
            messages.error(request, error)
        else:
            upload = data.pop("upload")
            for key, value in data.items():
                setattr(task, key, value)
            if upload:
                task.attachment = upload
            task.save()
            messages.success(request,"your task successfully updated")
            return redirect("viewtask")

    return render(request,"superadmin/edittask.html",{"task": task,"courses": courses,"subjects": subjects})


@login_required
def deletetask(request, id):

    task = get_object_or_404(tbl_assignment, id=id)
    task.delete()
    messages.success(request,"your task is deleted ")
    return redirect("viewtask")


def online_class(request):
    if not request.user.is_authenticated:
        return redirect("home")

    if request.user.is_superuser:
        return redirect("superadmin_schedule_class")

    if hasattr(request.user, "Teacher"):
        return redirect("teacher_schedule_class")

    return HttpResponse("Only teachers and superadmin can schedule classes.", status=403)


def superadmin_schedule_class(request):
    if not request.user.is_authenticated:
        return redirect("home")

    if not request.user.is_superuser:
        return HttpResponse("Only superadmin can schedule classes.", status=403)

    return render(
        request,
        "superadmin/onlineclass.html",
        {
            "teachers": tbl_teacher.objects.select_related("user").order_by("name"),
            "courses": tbl_course.objects.all(),
            "subjects": tbl_subject.objects.all(),
            "fixed_teacher": None,
        }
    )


def teacher_schedule_class(request):
    if not request.user.is_authenticated:
        return redirect("home")

    if not hasattr(request.user, "Teacher"):
        return HttpResponse("Only teachers can schedule classes.", status=403)

    profile = request.user.Teacher

    return render(
        request,
        "teacher/onlineclass.html",
        {
            "courses": profile.courses.all() if hasattr(profile, "courses") else tbl_course.objects.all(),
            "subjects": tbl_subject.objects.all(),
            "fixed_teacher": request.user,
        }
    )


def refreshmeeting_statuses(queryset):
    from datetime import datetime, timedelta
    from django.utils import timezone

    now = timezone.now()

    for item in queryset.filter(status="live"):
        start = item.started_at

        if not start:
            start = datetime.combine(item.class_date, item.class_time)

            if timezone.is_naive(start):
                start = timezone.make_aware(
                    start,
                    timezone.get_current_timezone()
                )

        if now >= start + timedelta(minutes=item.duration):
            item.status = "closed"
            item.save(update_fields=["status"])

    return queryset

def _store_attendance(request):
    """Save today's attendance for a course without creating duplicate rows."""
    course = (request.POST.get("course") or "").strip()
    students = tbl_student.objects.filter(course=course) if course else []
    if not course or not students:
        messages.error(request, "Please select a course that has students.")
        return

    today = timezone.localdate()
    created = updated = 0
    for student in students:
        status = request.POST.get(f"status_{student.Enrollment_no}", "Absent")
        if status not in ("Present", "Absent"):
            status = "Absent"
        existing = Attendence.objects.filter(
            Enrollment_no=student.Enrollment_no, Date__date=today
        ).first()
        if existing:
            existing.status = status
            existing.teacher_name = request.user.username
            existing.save()
            updated += 1
        else:
            Attendence.objects.create(
                Enrollment_no=student.Enrollment_no,
                name=student.name,
                course=student.course,
                mobile=student.mobile,
                teacher_name=request.user.username,
                Date=timezone.now(),
                status=status,
            )
            created += 1
    if updated and not created:
        messages.success(request, "Today's attendance was already taken, so it has been updated.")
    else:
        messages.success(request, "Attendance saved successfully.")


@login_required
def attendance(request):
    ab = tbl_course.objects.all()
    course = request.GET.get('course')
    data = []
    message = ""

    if course:
        data = tbl_student.objects.filter(course=course)
        if not data:
            message = "No students found for this course."

    return render(request, "superadmin/attendence.html", {
        'ab': ab,
        'data': data,
        'course': course,
        'message': message,
    })


@login_required
def Save_attendance(request):
    if request.method == "POST":
        _store_attendance(request)
    return redirect('attendance')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def show_attendance(request):
    ab = tbl_course.objects.all()
    course = request.GET.get('course', '')
    students = []

    if course:
        students = tbl_student.objects.filter(course=course)

    for i in students:

        i.total = Attendence.objects.filter(Enrollment_no=i.Enrollment_no).count()
        i.present = Attendence.objects.filter(Enrollment_no=i.Enrollment_no, status="Present").count()
        i.absent = Attendence.objects.filter(Enrollment_no=i.Enrollment_no, status="Absent").count()

        if i.total > 0:
            i.percent = round(i.present * 100 / i.total, 1)
        else:
            i.percent = 0

    return render(request, "superadmin/show_attendance.html", {
    'ab': ab,
    'course': course,
    'students': students,
})
    
@login_required
def online_test(request):

    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_test(request.POST)
        if error:
            messages.error(request, error)
        else:
            Test.objects.create(**data)
            messages.success(request,"Online test created successfully.")
            return redirect("online_test")
    return render(request,"superadmin/online_test.html",{"courses": courses,"subjects": subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def show_test(request):
    tests = Test.objects.all()
    return render(request,"superadmin/show_test.html",{"tests": tests})
    
@login_required
def add_question(request,id):

    test = get_object_or_404(Test, id=id)

    questions = Question_bank.objects.filter(test=test).order_by("-id")

    if request.method == "POST":
        data, error = validate_question(request.POST, test)
        if error:
            messages.error(request, error)
        else:
            Question_bank.objects.create(test=test, **data)
            messages.success(request, "Question added successfully.")
            return redirect("add_question", id=test.id)

    return render(
        request,
        "superadmin/add_question.html",
        {
            "test": test,
            "questions": questions
        }
    )

@login_required
def bulk_question(request,id):
    test=get_object_or_404(Test,id=id)

    if request.method == "POST":
        message, level = import_questions(test, request.FILES.get('csv_file'))
        getattr(messages, level)(request, message)
        if level == "success":
            return redirect("add_question", id=test.id)

    return render(request,'superadmin/bulk_question_upload.html',{'test':test})
 
    
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def announcement(request):

    announcements = Announcement.objects.all().order_by("-publish_date","-id")

    if request.method == "POST":
        data, error = validate_announcement(request.POST)
        if error:
            messages.error(request, error)
        else:
            Announcement.objects.create(**data)
            messages.success(request,"Announcement published successfully.")
            return redirect("announcement")

    return render(request,"superadmin/announcement.html",{"announcements": announcements})

@login_required
def all_submissions(request):

    submissions = TaskSubmit.objects.all().order_by("-id")

    return render(
        request,
        "superadmin/all_submissions.html",
        {
            "submissions": submissions
        }
    )


@login_required
def review_submission(request, id):

    submission = get_object_or_404(TaskSubmit, id=id)

    return render(
        request,
        "superadmin/review_submission.html",
        {
            "submission": submission
        }
    )


@login_required
def give_assignment_marks(request, id):

    submission = get_object_or_404(TaskSubmit, id=id)

    if request.method == "POST":

        marks = request.POST.get("marks")

        if not marks:
            messages.error(
                request,
                "Please enter marks."
            )

            return redirect(
                "review_submission",
                id=id
            )

        try:
            marks = int(marks)

        except ValueError:

            messages.error(
                request,
                "Please enter valid marks."
            )

            return redirect(
                "review_submission",
                id=id
            )

        if marks < 0:

            messages.error(
                request,
                "Marks cannot be negative."
            )

            return redirect(
                "review_submission",
                id=id
            )

        if marks > submission.task.total_marks:

            messages.error(
                request,
                "Marks cannot be greater than total marks."
            )

            return redirect(
                "review_submission",
                id=id
            )

        submission.marks = marks
        submission.status = "Evaluated"
        submission.save()

        messages.success(
            request,
            "Assignment marks updated successfully."
        )

        return redirect(
            "review_submission",
            id=id
        )

    return redirect(
        "review_submission",
        id=id
    )



@login_required
def tbase(request):
    teacher = request.user.Teacher
    return render(request,'teacher/base.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tdash(request):

    teacher = get_object_or_404(tbl_teacher, user=request.user)

    # Teacher ke subjects
    subjects = tbl_subject.objects.filter(
        teacher=teacher.name
    )

    # Teacher ke courses
    course_names = subjects.values_list(
        "course",
        flat=True
    ).distinct()

    courses = tbl_course.objects.filter(
        course_name__in=course_names
    )

    # Teacher ke study materials
    materials = tbl_StudyMaterial.objects.filter(
        create_by=request.user
    )

    # Teacher ki online classes
    upcoming_classes = GoogleMeeting.objects.filter(
        teacher=request.user,
        status="scheduled",
        class_date__gte=timezone.now().date()
    ).order_by(
        "class_date",
        "class_time"
    )[:5]

    online_classes = GoogleMeeting.objects.filter(
        teacher=request.user,
        status="scheduled",
        class_date__gte=timezone.now().date()
    ).count()

    # Students enrolled in teacher's courses
    students = tbl_student.objects.filter(
        course__in=course_names
    )

    # Latest announcements
    announcements = Announcement.objects.all().order_by(
        "-publish_date",
        "-id"
    )[:5]

    context = {
        "teacher": teacher,

        "courses": courses,
        "subjects": subjects,
        "materials": materials,
        "students": students,

        "total_courses": courses.count(),
        "total_subjects": subjects.count(),
        "total_materials": materials.count(),
        "total_students": students.count(),
        "online_classes": online_classes,

        "upcoming_classes": upcoming_classes,
        "announcements": announcements,

        # Jab Assignment/Test models milenge
        "total_assignments": 0,
        "total_submissions": 0,
        "total_tests": 0,
    }

    return render(
        request,
        "teacher/dashboard.html",
        context
    )

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def currentsession(request):
    sessions = tbl_session.objects.all()
    return render(request,"teacher/currentsession.html",{"sessions": sessions})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def mycourse(request):
    return render(request,'teacher/mycourse.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def mysubject(request):

    teacher = get_object_or_404(tbl_teacher, user=request.user)
    subjects = tbl_subject.objects.filter(teacher=teacher.name)

    return render(request,"teacher/mysubject.html",{"subjects": subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tuploadsm(request):
    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_material(request.POST, request.FILES)
        if error:
            messages.error(request, error)
        else:
            upload = data.pop("upload")
            tbl_StudyMaterial.objects.create(
                material_file=upload,
                create_by=request.user,
                **{**data, "external_url": data["external_url"] or None}
            )
            messages.success(request,"your study material successfully uploaded")
            return redirect("tuploadsm")
    return render(request,'teacher/uploadsm.html',{'courses':courses,'subjects':subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tviewsm(request):
    materials = tbl_StudyMaterial.objects.filter(create_by=request.user)
    return render(request,"teacher/viewsm.html",{'materials': materials})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def teditsm(request,id):

    material = get_object_or_404(tbl_StudyMaterial, id=id)

    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_material(
            request.POST, request.FILES, exclude_id=material.id,
            existing=material)
        if error:
            messages.error(request, error)
        else:
            upload = data.pop("upload")
            for key, value in data.items():
                setattr(material, key, value or None if key == "external_url" else value)
            if upload:
                material.material_file = upload
            material.save()
            messages.success(request, "StudyMaterial updated successfully.")
            return redirect("tviewsm")
    return render(request,"teacher/editsm.html",{"material": material,"courses": courses,"subjects": subjects})

@login_required
def tdeletesm(request, id):
    material = get_object_or_404(tbl_StudyMaterial, id=id)
    material.delete()
    messages.success(request, "StudyMaterial deleted successfully.")
    return redirect("tviewsm")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def taddtask(request):

    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_assignment(request.POST, request.FILES)
        if error:
            messages.error(request, error)
        else:
            upload = data.pop("upload")
            tbl_assignment.objects.create(
                attachment=upload,
                create_by=request.user,
                Dor=timezone.now(),
                **data
            )
            messages.success(request,"Assignment successfully created")
            return redirect("taddtask")
    return render(request,"teacher/addtask.html",{"courses": courses,"subjects": subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tviewtask(request):
    assignments = tbl_assignment.objects.filter(create_by=request.user)
    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()
    return render(request,"teacher/viewtask.html",{"assignments": assignments,"courses": courses,"subjects": subjects})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tedittask(request, id):

    task = get_object_or_404(tbl_assignment, id=id)

    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_assignment(
            request.POST, request.FILES, exclude_id=task.id)
        if error:
            messages.error(request, error)
        else:
            upload = data.pop("upload")
            for key, value in data.items():
                setattr(task, key, value)
            if upload:
                task.attachment = upload
            task.save()
            messages.success(request,"your task successfully updated")
            return redirect("tviewtask")

    return render(request,"teacher/edittask.html",{"task": task,"courses": courses,"subjects": subjects})

@login_required
def tdeletetask(request, id):

    task = get_object_or_404(tbl_assignment, id=id)
    task.delete()
    messages.success(request,"your task is deleted ")
    return redirect("tviewtask")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tattendance(request):
    ab = tbl_course.objects.all()
    course = request.GET.get('course')
    data = []
    message = ""

    if course:
        data = tbl_student.objects.filter(course=course)
        if not data:
            message = "No students found for this course."

    return render(request, "teacher/attendence.html", {
        'ab': ab,
        'data': data,
        'course': course,
        'message': message,
    })


@login_required
def tSave_attendance(request):
    if request.method == "POST":
        _store_attendance(request)
    return redirect('tattendance')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tshow_attendance(request):
    ab = tbl_course.objects.all()
    course = request.GET.get('course', '')
    students = []

    if course:
        students = tbl_student.objects.filter(course=course)

    for i in students:

        i.total = Attendence.objects.filter(Enrollment_no=i.Enrollment_no).count()
        i.present = Attendence.objects.filter(Enrollment_no=i.Enrollment_no, status="Present").count()
        i.absent = Attendence.objects.filter(Enrollment_no=i.Enrollment_no, status="Absent").count()

        if i.total > 0:
            i.percent = round(i.present * 100 / i.total, 1)
        else:
            i.percent = 0

    return render(request, "teacher/show_attendance.html", {
    'ab': ab,
    'course': course,
    'students': students,
})
    
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tonline_test(request):

    courses = tbl_course.objects.all()
    subjects = tbl_subject.objects.all()

    if request.method == "POST":
        data, error = validate_test(request.POST)
        if error:
            messages.error(request, error)
        else:
            Test.objects.create(**data)
            messages.success(request,"Online test created successfully.")
            return redirect("tonline_test")
    return render(request,"teacher/online_test.html",{"courses": courses,"subjects": subjects})
        
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tshow_test(request):
    tests = Test.objects.all()
    return render(request,"teacher/show_test.html",{"tests": tests})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)    
@login_required
def tadd_question(request,id):

    test = get_object_or_404(Test, id=id)

    questions = Question_bank.objects.filter(test=test).order_by("-id")

    if request.method == "POST":
        data, error = validate_question(request.POST, test)
        if error:
            messages.error(request, error)
        else:
            Question_bank.objects.create(test=test, **data)
            messages.success(request, "Question added successfully.")
            return redirect("tadd_question", id=test.id)

    return render(
        request,
        "teacher/add_question.html",
        {
            "test": test,
            "questions": questions
        }
    )

@login_required
def tbulk_question(request,id):
    test=get_object_or_404(Test,id=id)

    if request.method == "POST":
        message, level = import_questions(test, request.FILES.get('csv_file'))
        getattr(messages, level)(request, message)
        if level == "success":
            return redirect("tadd_question", id=test.id)

    return render(request,'teacher/bulk_question_upload.html',{'test':test})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def submission(request):
    return render(request,'teacher/submission.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def tannouncement(request):

    announcements = Announcement.objects.filter(
        audience__in=["Teachers", "All"])

    return render(
        request,
        "teacher/announcement.html",
        {
            "announcements": announcements
        }
    )


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def teacher_submissions(request):
    submissions = TaskSubmit.objects.filter(
        submit_to=request.user.username
    ).order_by("-id")

    return render(
        request,
        "teacher/submissions.html",
        {"submissions": submissions}
    )


@login_required
def teacher_review_submission(request, id):
    submission = get_object_or_404(TaskSubmit, id=id)

    return render(
        request,
        "teacher/review_submission.html",
        {"submission": submission}
    )


@login_required
def teacher_give_assignment_marks(request, id):
    submission = get_object_or_404(TaskSubmit, id=id)

    if request.method == "POST":

        marks = request.POST.get("marks")

        if not marks:
            messages.error(request, "Please enter marks.")
            return redirect("teacher_review_submission", id=id)

        try:
            marks = int(marks)
        except ValueError:
            messages.error(request, "Please enter valid marks.")
            return redirect("teacher_review_submission", id=id)

        if marks < 0:
            messages.error(request, "Marks cannot be negative.")
            return redirect("teacher_review_submission", id=id)

        if marks > submission.task.total_marks:
            messages.error(
                request,
                "Marks cannot be greater than total marks."
            )
            return redirect("teacher_review_submission", id=id)

        submission.marks = marks
        submission.status = "Evaluated"
        submission.save()

        messages.success(
            request,
            "Assignment marks updated successfully."
        )

        return redirect("teacher_review_submission", id=id)

    return redirect("teacher_review_submission", id=id)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def sbase(request):
    Student = request.user.Student
    return render(request, "student/base.html")

from django.db.models import Q
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def sdashboard(request):

    student = get_object_or_404(tbl_student, user=request.user)
    # -----------------------------------------
    # CURRENT SUBJECTS
    # -----------------------------------------
    subjects = tbl_subject.objects.filter(
        course=student.course,
        semester=student.sem
    )
    current_subjects = subjects.count()


    # -----------------------------------------
    # ASSIGNMENTS
    # -----------------------------------------

    assignments = tbl_assignment.objects.filter(
        course=student.course
    ).order_by("-id")

    assignments_count = assignments.count()


    # -----------------------------------------
    # ATTENDANCE
    # -----------------------------------------

    attendance_records = Attendence.objects.filter(
        Enrollment_no=student.Enrollment_no
    )

    total_attendance = attendance_records.count()

    present_attendance = attendance_records.filter(
        status="Present"
    ).count()

    attendance = 0

    if total_attendance > 0:
        attendance = round(
            (present_attendance / total_attendance) * 100,
            2
        )


    # -----------------------------------------
    # ONLINE CLASSES
    # -----------------------------------------

    today = timezone.now().date()

    online_classes = GoogleMeeting.objects.filter(
        course=student.course,
        status="scheduled",
        class_date__gte=today
    ).count()


    upcoming_classes = GoogleMeeting.objects.filter(
        course=student.course,
        status="scheduled",
        class_date__gte=today
    ).order_by(
        "class_date",
        "class_time"
    )[:5]


    # -----------------------------------------
    # ONLINE TESTS
    # -----------------------------------------

    online_tests = Test.objects.filter(
        course=student.course
    ).count()


    # -----------------------------------------
    # STUDY MATERIALS
    # -----------------------------------------

    study_materials = tbl_StudyMaterial.objects.filter(
        course=student.course,
        subject__in=subjects.values_list(
            "subject_name",
            flat=True
        )
    ).count()


    # -----------------------------------------
    # MY SUBMISSIONS
    # -----------------------------------------

    submissions = TaskSubmit.objects.filter(
        student=request.user
    ).count()


    # -----------------------------------------
    # TEST RESULTS
    # -----------------------------------------

    test_results = TestResult.objects.filter(
        student=request.user
    ).count()


    # -----------------------------------------
    # ANNOUNCEMENTS
    # -----------------------------------------

    announcements = Announcement.objects.filter(
        Q(audience__iexact="Student") |
        Q(audience__iexact="All")
    ).order_by(
        "-publish_date",
        "-id"
    )[:5]


    # -----------------------------------------
    # RECENT ASSIGNMENTS
    # -----------------------------------------

    recent_assignments = assignments[:5]


    # -----------------------------------------
    # CONTEXT
    # -----------------------------------------

    context = {

        "student": student,

        "current_subjects": current_subjects,

        "assignments_count": assignments_count,

        "attendance": attendance,

        "online_classes": online_classes,

        "upcoming_classes": upcoming_classes,

        "online_tests": online_tests,

        "study_materials": study_materials,

        "submissions": submissions,

        "test_results": test_results,

        "announcements": announcements,

        "recent_assignments": recent_assignments,

    }

    return render(
        request,
        "student/dashboard.html",
        context
    )

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def scurrentsession(request):
    student = get_object_or_404(tbl_student, user=request.user)
    session = get_object_or_404(tbl_session, session_name=student.session)
    return render(request,"student/currentsession.html",{"student": student,"session": session})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def smycourse(request):

    student = get_object_or_404(tbl_student, user=request.user)
    course = get_object_or_404(tbl_course, course_name=student.course)

    return render(request,"student/mycourse.html",{"student": student,"course": course})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def smysubject(request):

    student = get_object_or_404(tbl_student, user=request.user)
    subjects = tbl_subject.objects.filter(course=student.course)
    return render(request,"student/mysubject.html",{"student": student,"subjects": subjects})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def sm(request):
    
    student = get_object_or_404(tbl_student, user=request.user)
    materials = tbl_StudyMaterial.objects.filter(course=student.course)
    
    return render(request,"student/sm.html",{"materials": materials})

    
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def stu_submission(request):
    submissions = TaskSubmit.objects.filter(student=request.user)
    return render(request,"student/submission.html",{"submissions": submissions})



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def student_code_lab(request):
    context = {"languages": LANGUAGES, "starter_code": STARTER_CODE}
    return render(request, "student/code_lab.html", context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def stu_assignment(request):
    student = get_object_or_404(tbl_student, user=request.user)
    assignments = tbl_assignment.objects.filter(course=student.course)
    return render(request, "student/assignment.html",{'assignments':assignments})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def submit_assignment(request, id):

    assignment = get_object_or_404(tbl_assignment, id=id)
    student = get_object_or_404(tbl_student, user=request.user)

    if assignment.course != student.course:
        messages.error(request, "This assignment is not assigned to your course.")
        return redirect("stu_assignment")

    if request.method == "POST":
        submitted_file = request.FILES.get("submitted_file")
        error = validate_submission(assignment, request.user, submitted_file)
        if error:
            messages.error(request, error)
            return redirect("submit_assignment", id=assignment.id)

        TaskSubmit.objects.create(
            task=assignment,
            student=request.user,
            submitted_file=submitted_file,
            submit_to=assignment.create_by.username if assignment.create_by else "Teacher",
            status="Submitted",
            dos=date.today()
        )

        messages.success(request,"Assignment submitted successfully.")
        return redirect("stu_assignment")

    return render(request,"student/submit_assignment.html",{"assignment": assignment})

@login_required
def run_student_code(request):
    language = (request.POST.get("language") or "").strip()
    source_code = request.POST.get("source_code") or ""
    stdin = request.POST.get("stdin") or ""

    if len(source_code) > 50000:
        return JsonResponse({"ok": False, "error": "Maximum code size is 50,000 characters."}, status=400)

    if len(stdin) > 10000:
        return JsonResponse({"ok": False, "error": "Maximum input size is 10,000 characters."}, status=400)

    result, error = run_code(language, source_code, stdin)

    if error:
        return JsonResponse({"ok": False, "error": error}, status=502)

    return JsonResponse({"ok": True, **result})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def Stu_show_test(request):
    student = get_object_or_404(tbl_student, user=request.user)
    tests = Test.objects.filter(course=student.course)
    return render(request,'student/show_test.html',{'tests':tests})

@login_required
def start_test(request, id):

    test = get_object_or_404(Test, id=id)
    student = get_object_or_404(tbl_student, user=request.user)

    if test.course != student.course:
        messages.error(request, "This test is not assigned to your course.")
        return redirect("Stu_show_test")

    question = Question_bank.objects.filter(test=test)

    result = TestResult.objects.filter(
        student=request.user,
        test=test
    ).first()

    if result:
        return render(
            request,
            'student/test_result.html',
            {
                'test': test,
                'result': result,
                'already_submitted': True,
            }
        )

    if test.status in ("Draft", "Closed"):
        messages.error(request, f"This test is {test.status.lower()} and cannot be attempted.")
        return redirect("Stu_show_test")

    if not question.exists():
        messages.error(request, "No questions have been added to this test yet.")
        return redirect("Stu_show_test")

    if request.method == "POST":

        marks = 0

        for q in question:

            answer = request.POST.get("q" + str(q.id))

            if answer == q.correct_option:
                marks = marks + q.marks

        result, created = TestResult.objects.get_or_create(
            student=request.user,
            test=test,
            defaults={"obtained_marks": marks}
        )

        return render(
            request,
            'student/test_result.html',
            {
                'test': test,
                'result': result,
                'already_submitted': not created,
            }
        )

    return render(
        request,
        'student/start_test.html',
        {
            "question": question,
            "test": test
        }
    )

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required    
def show_result(request):

    results = TestResult.objects.filter(student=request.user)
    return render(request,"student/showresult.html",{"results": results})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def my_attendance(request):
    student = get_object_or_404(tbl_student, user=request.user)

    attendance = Attendence.objects.filter(
        Enrollment_no=student.Enrollment_no
    ).order_by("-Date")

    total = attendance.count()
    present = attendance.filter(status="Present").count()
    absent = attendance.filter(status="Absent").count()

    percentage = 0

    if total > 0:
        percentage = round((present / total) * 100, 2)

    return render(
        request,
        "student/my_attendance.html",
        {
            "student": student,
            "attendance": attendance,
            "total": total,
            "present": present,
            "absent": absent,
            "percentage": percentage
        }
    )

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def sannouncement(request):

    announcements = Announcement.objects.filter(
        audience__in=["Students", "All"])

    return render(
        request,
        "student/announcement.html",
        {
            "announcements": announcements
        }
    )

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required    
def all_test_results(request):

    results = TestResult.objects.select_related("student","test").order_by("-id")

    return render(request,"superadmin/all_test_results.html",{"results": results})