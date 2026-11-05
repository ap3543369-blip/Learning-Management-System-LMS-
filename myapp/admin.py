from django.contrib import admin
from .models import*

# Register your models here.
admin.site.register(tbl_session)
admin.site.register(tbl_course)
admin.site.register(tbl_subject)
admin.site.register(tbl_teacher)
admin.site.register(tbl_student)
admin.site.register(tbl_StudyMaterial)
admin.site.register(tbl_assignment)
admin.site.register(Attendence)
admin.site.register(Announcement)
admin.site.register(Test)
admin.site.register(Question_bank)
admin.site.register(TestResult)
admin.site.register(TaskSubmit)
admin.site.register(GoogleMeeting)
admin.site.register(GoogleCredential)
