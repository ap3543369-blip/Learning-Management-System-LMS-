
from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
  path('',home,name="home"),
  path('superadmindash',superadmindash,name="superadmindash"),  
  
  path('addsession',addsession,name="addsession"),
  path('showsession',showsession,name="showsession"),
  path('editsession/<int:id>',editsession,name="editsession"),
  path('deletesession/<int:id>',deletesession,name="deletesession"),
  
  path('addcourse',addcourse,name="addcourse"),
  path("viewcourse",viewcourse, name="viewcourse"),
  path("editcourse/<int:id>",editcourse, name="editcourse"),
  path("deletecourse/<int:id>",deletecourse, name="deletecourse"),
  
  path("addteacher",addteacher, name="addteacher"),
  path("bulkteacher",bulkteacher, name="bulkteacher"),
  path("viewteacher",viewteacher, name="viewteacher"),
  path("editteacher/<int:employee_id>/",editteacher, name="editteacher"),
  path("deleteteacher/<int:employee_id>/",deleteteacher, name="deleteteacher"),
  
  path("addsubject",addsubject, name="addsubject"),
  path("viewsubject",viewsubject, name="viewsubject"),
  path("editsubject/<int:id>",editsubject, name="editsubject"),
  path("deletesubject/<int:id>",deletesubject, name="deletesubject"),
  
  path("addstudent",addstudent, name="addstudent"),
  path("viewstudent",viewstudent,name="viewstudent"),
  path("editstudent/<str:Enrollment_no>/",editstudent,name="editstudent"),
  path("deletestudent/<str:Enrollment_no>/",deletestudent,name="deletestudent"),
  
  path("uploadsm",uploadsm,name="uploadsm"),
  path("viewsm",viewsm,name="viewsm"),
  path("editsm/<int:id>",editsm,name="editsm"),
  path("deletesm/<int:id>",deletesm,name="deletesm"),
  
  path("addtask",addtask,name="addtask"),
  path("viewtask",viewtask,name="viewtask"),
  path("edittask/<int:id>",edittask,name="edittask"),
  path("deletetask/<int:id>",deletetask,name="deletetask"),
  
  path("online_test",online_test, name="online_test"),
  path("show_test",show_test, name="show_test"),
  path("bulk_question_upload/<int:id>",bulk_question, name="bulk_question_upload"),
  path("add_question/<int:id>",add_question, name="add_question"),
  path("all_test_results",all_test_results, name="all_test_results"),
  path("onlineclass",online_class, name="onlineclass"),
  
  
  path("superadmin/all-submissions/",all_submissions,name="all_submissions"),
  path("superadmin/review-submission/<int:id>/",review_submission,name="review_submission"),
  path("superadmin/give-assignment-marks/<int:id>/",give_assignment_marks,name="give_assignment_marks"),
  
  path("superadmin/online-classes/schedule/",superadmin_schedule_class,name="superadmin_schedule_class"),
  path("teacher/online-classes/schedule/",teacher_schedule_class,name="teacher_schedule_class"),

  
  # =================================================
  # GOOGLE CONNECT
  # =================================================
  
  path("google/login/", google_login, name="google_login"),
  path("google/callback/", google_callback, name="google_callback"),

  # =================================================
  # SCHEDULE MEETING
  # =================================================

  path("schedule-meeting/", schedule_meeting, name="schedule_meeting"),

  # =================================================
  # START CLASS
  # =================================================

  path("meeting/<int:id>/start/", start_meeting, name="start_meeting"),

  # =================================================
  # TEACHER / SUPERADMIN / STUDENT CLASSES
  # =================================================

  path("teacher/classes/", teacher_meetings, name="teacher_classes"),
  path("superadmin/classes/", superadmin_meetings, name="superadmin_classes"),
  path("student/classes/", student_classes, name="student_classes"),

  # =================================================
  # JOIN MEETING
  # =================================================

  path("meeting/<int:id>/join/", join_meeting, name="join_meeting"),

  path("attendance",attendance,name="attendance"),
  path('save_attendance/',Save_attendance, name="save_attendance"),
  path('show_attendance/', show_attendance, name='show_attendance'),
  path("announcement",announcement,name="announcement"),
  
  # TEACHER
  path("tdash",tdash, name="tdash"),
  path("currentsession",currentsession, name="currentsession"),
  path("mycourse",mycourse, name="mycourse"),
  path("mysubject",mysubject, name="mysubject"),
  
  path("tuploadsm",tuploadsm, name="tuploadsm"),
  path("tviewsm",tviewsm, name="tviewsm"),
  path("teditsm/<int:id>",teditsm,name="teditsm"),
  path("tdeletesm/<int:id>",tdeletesm,name="tdeletesm"),
  
  path("taddtask",taddtask,name="taddtask"),
  path("tviewtask",tviewtask,name="tviewtask"),
  path("tedittask/<int:id>",tedittask,name="tedittask"),
  path("tdeletetask/<int:id>",tdeletetask,name="tdeletetask"),
  
  
  
  path("tattendance",tattendance,name="tattendance"),
  path('tsave_attendance/',tSave_attendance, name="tsave_attendance"),
  path('tshow_attendance/',tshow_attendance, name='tshow_attendance'),
  path("tonline_test",tonline_test, name="tonline_test"),
  path("tshow_test",tshow_test, name="tshow_test"),
  path("tbulk_question_upload/<int:id>",tbulk_question, name="tbulk_question_upload"),
  path("tadd_question/<int:id>",tadd_question, name="tadd_question"),
  path("submission",submission, name="submission"),
  path("tannouncement",tannouncement, name="tannouncement"),
  
  path("teacher/submissions/", teacher_submissions, name="teacher_submissions"),
  path("teacher/review-submission/<int:id>/",teacher_review_submission, name="teacher_review_submission"),
  path("teacher/give-assignment-marks/<int:id>/",teacher_give_assignment_marks, name="teacher_give_assignment_marks"),
  
  # Student 
  
  path("sdashboard",sdashboard, name="sdashboard"),
  path("scurrentsession",scurrentsession, name="scurrentsession"),
  path("smycourse",smycourse, name="smycourse"),
  path("smysubject",smysubject, name="smysubject"),
  path("sm",sm, name="sm"),
  path("stu_submission",stu_submission, name="stu_submission"),
  path("stu_assignment",stu_assignment, name="stu_assignment"),
  path("submit_assignment/<int:id>",submit_assignment, name="submit_assignment"),
  path("Stu_show_test",Stu_show_test, name="Stu_show_test"),
  path("start_test/<int:id>",start_test, name="start_test"),
  path("show_result",show_result, name="show_result"),
  #path("start_result/<int:id>",start_result, name="start_result"),
  # Run Code
  path('run-code/',run_student_code,name='run_student_code'),
  path('code-lab/',student_code_lab,name='student_code_lab'),
  path('my_attendance',my_attendance,name='my_attendance'),
  path('sannouncement',sannouncement,name='sannouncement'),

  path("logout/", logout_view, name="logout"),
]



if settings.DEBUG:
  urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
  )