"""Google OAuth and Google Meet integration kept outside views.py."""
import json
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.apps import meet_v2

from .models import GoogleCredential, GoogleMeeting, tbl_course, tbl_subject, tbl_teacher, tbl_student

CACHE_PREFIX = "google_oauth_verifier_"
CACHE_TIMEOUT = 600


def _flow(state=None):
    return Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=settings.GOOGLE_SCOPES,
        state=state,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        autogenerate_code_verifier=True,
    )


def google_login(request):
    flow = _flow()
    url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    # Cache is not dependent on the browser's session cookie surviving OAuth redirect.
    cache.set(CACHE_PREFIX + state, flow.code_verifier, CACHE_TIMEOUT)
    return redirect(url)


def google_callback(request):
    state = request.GET.get("state")
    if not state:
        return HttpResponse("Google state URL mein nahi mila. Dobara Connect Google karo.")
    verifier = cache.get(CACHE_PREFIX + state)
    if not verifier:
        return HttpResponse("Google login state expire ho gaya. Dobara Connect Google karo.")
    flow = _flow(state=state)
    flow.code_verifier = verifier
    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
    except Exception as exc:
        return HttpResponse("Google authentication failed: " + str(exc))
    credentials = flow.credentials
    cache.delete(CACHE_PREFIX + state)
    record = GoogleCredential.objects.first()
    if record:
        record.access_token = credentials.token
        if credentials.refresh_token:
            record.refresh_token = credentials.refresh_token
        record.connected = True
        record.save()
    else:
        GoogleCredential.objects.create(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            connected=True,
        )
    return render(request, "superadmin/google_connected.html")


def _meet_client():
    record = GoogleCredential.objects.filter(connected=True).first()
    if not record:
        raise ValueError("Pehle main Google account connect karo.")
    with open(settings.GOOGLE_CLIENT_SECRETS_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)
    web = config.get("web", {})
    if not web.get("client_id") or not web.get("client_secret"):
        raise ValueError("client_secret.json mein web client configuration nahi mila.")
    creds = Credentials(
        token=record.access_token,
        refresh_token=record.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=web["client_id"],
        client_secret=web["client_secret"],
        scopes=settings.GOOGLE_SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        record.access_token = creds.token
        record.save(update_fields=["access_token"])
    return meet_v2.SpacesServiceClient(credentials=creds)


def _can_manage(request, meeting=None):
    if request.user.is_superuser:
        return True
    if not hasattr(request.user, "Teacher"):
        return False
    return meeting is None or meeting.teacher_id == request.user.id


@login_required
def schedule_meeting(request):
    if not (request.user.is_superuser or hasattr(request.user, "Teacher")):
        return HttpResponseForbidden("Only teachers and superadmin can schedule classes.")
    if request.method != "POST":
        return redirect("superadmin_schedule_class" if request.user.is_superuser else "teacher_schedule_class")
    title = request.POST.get("class_title", "").strip()
    course = request.POST.get("course", "").strip()
    subject = request.POST.get("subject", "").strip()
    agenda = request.POST.get("agenda", "").strip()
    if request.user.is_superuser:
        teacher = get_object_or_404(User, pk=request.POST.get("teacher"))
    else:
        teacher = request.user
    teacher_profile = tbl_teacher.objects.filter(user=teacher).first()
    teacher_email = teacher.email or (teacher_profile.email if teacher_profile else "")
    if not teacher_email:
        return HttpResponse("Teacher ke account/profile mein Gmail/Google email add karo.")
    try:
        class_date = date.fromisoformat(request.POST.get("class_date", ""))
        class_time = request.POST.get("class_time")
        duration = int(request.POST.get("duration", "60"))
        if not title or not course or not subject or not class_time or duration < 1:
            raise ValueError("Required fields check karein.")
    except (TypeError, ValueError):
        return HttpResponse("Class details sahi se fill karein.", status=400)
    try:
        client = _meet_client()
        space = client.create_space(request=meet_v2.CreateSpaceRequest(
            space=meet_v2.Space(config=meet_v2.SpaceConfig(
                moderation=meet_v2.SpaceConfig.Moderation.ON
            ))
        ))
    except Exception as exc:
        return HttpResponse("Google Meet create nahi hua: " + str(exc), status=502)

    # Add only the assigned teacher as co-host. Students are deliberately NOT
    # pre-added, so moderation/knocking remains active and teacher admits them.
    cohost_added, cohost_error = False, ""
    try:
        client.create_member(parent=space.name, member=meet_v2.Member(
            email=teacher_email, role=meet_v2.Member.Role.COHOST
        ))
        cohost_added = True
    except Exception as exc:
        cohost_error = str(exc)

    meeting = GoogleMeeting.objects.create(
        class_title=title, course=course, subject=subject, teacher=teacher,
        class_date=class_date, class_time=class_time, duration=duration,
        agenda=agenda, meeting_url=space.meeting_uri,
        google_space_name=space.name, status="scheduled",
    )
    return redirect("superadmin_classes" if request.user.is_superuser else "teacher_classes")


@login_required
def teacher_meetings(request):
    if not (request.user.is_superuser or hasattr(request.user, "Teacher")):
        return HttpResponseForbidden("Only teachers and superadmin can view this page.")
    meetings = GoogleMeeting.objects.all() if request.user.is_superuser else GoogleMeeting.objects.filter(teacher=request.user)
    meetings = _refresh_meeting_statuses(meetings)
    template = "superadmin/meeting_list.html" if request.user.is_superuser else "teacher/meeting_list.html"
    return render(request, template, {"meetings": meetings.order_by("-class_date", "-class_time")})


@login_required
def superadmin_meetings(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only superadmin can view all classes.")
    meetings = _refresh_meeting_statuses(GoogleMeeting.objects.all())
    return render(request, "superadmin/meeting_list.html", {"meetings": meetings.order_by("-class_date", "-class_time")})


def _refresh_meeting_statuses(queryset):
    now = timezone.now()
    for meeting in queryset.filter(status="live"):
        start = meeting.created_at
        if not start:
            start = datetime.combine(meeting.class_date, meeting.class_time)
            if timezone.is_naive(start):
                start = timezone.make_aware(start, timezone.get_current_timezone())
        if now >= start + timedelta(minutes=meeting.duration):
            meeting.status = "closed"
            meeting.save(update_fields=["status"])
    return queryset


@login_required
def start_meeting(request, id):
    meeting = get_object_or_404(GoogleMeeting, id=id)
    if not _can_manage(request, meeting):
        return HttpResponseForbidden("You can start only your own class.")
    if request.method != "POST":
        return redirect("teacher_classes")
    meeting.status = "live"
    meeting.started_at = timezone.now()
    meeting.save(update_fields=["status", "created_at"])
    # Mark live first, then take teacher directly into the Meet room.
    return redirect(meeting.meeting_url)


@login_required
def student_classes(request):
    if not (request.user.is_superuser or hasattr(request.user, "Teacher") or hasattr(request.user, "Student")):
        return HttpResponseForbidden("Please log in to view classes.")
    meetings = _refresh_meeting_statuses(GoogleMeeting.objects.all())
    if hasattr(request.user, "Student"):
        meetings = meetings.filter(course=request.user.Student.course)
    meetings = meetings.order_by("class_date", "class_time")
    return render(request, "meeting/student_classes.html", {"meetings": meetings, "upcoming_meetings": meetings})


@login_required
def join_meeting(request, id):
    meeting = get_object_or_404(GoogleMeeting, id=id)
    _refresh_meeting_statuses(GoogleMeeting.objects.filter(pk=meeting.pk))
    meeting.refresh_from_db()
    if meeting.status != "live":
        return HttpResponse("Class abhi live nahi hai ya close ho chuki hai.", status=403)
    if hasattr(request.user, "Student"):
        try:
            student = request.user.Student
            if student.course != meeting.course:
                return HttpResponseForbidden("Yeh class aapke course ke liye nahi hai.")
        except Exception:
            return HttpResponseForbidden("Student profile nahi mila.")
    elif not (request.user.is_superuser or hasattr(request.user, "Teacher")):
        return HttpResponseForbidden("Please log in to join the class.")
    return redirect(meeting.meeting_url)
