from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class tbl_session(models.Model):
    id=models.IntegerField(primary_key=True,auto_created=True)
    session_name=models.CharField(max_length=100)
    status=models.CharField(max_length=100)
    strt_date=models.DateField()
    end_date=models.DateField()
    Dor=models.DateTimeField()
    
class tbl_course(models.Model):

    id = models.IntegerField(primary_key=True, auto_created=True)
    session = models.CharField(max_length=100)
    course_code = models.CharField(max_length=100)
    course_name = models.CharField(max_length=200)
    level = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    description = models.TextField()
    Dor = models.DateTimeField()
    
class tbl_subject(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
    course = models.CharField(max_length=200)
    subject_code = models.CharField(max_length=100)
    subject_name = models.CharField(max_length=200)
    semester = models.CharField(max_length=100)
    credits = models.IntegerField()
    teacher = models.CharField(max_length=200)
    status = models.CharField(max_length=100)
    description = models.TextField()
    Dor = models.DateTimeField()
    
class tbl_teacher(models.Model):
    user=models.OneToOneField(User,
        on_delete=models.CASCADE,
        related_name="Teacher"
    )
    
    employee_id = models.IntegerField(primary_key=True, auto_created=True)
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    mobile = models.CharField(max_length=20)
    department = models.CharField(max_length=200)
    designation = models.CharField(max_length=200)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    Dor = models.DateTimeField()
    
class tbl_student(models.Model):
    user=models.OneToOneField(
            User,on_delete=models.CASCADE,
            related_name="Student"
        )
    Enrollment_no=models.CharField(primary_key=True)
    name=models.EmailField(max_length=225)
    email=models.CharField(max_length=200)
    mobile=models.CharField(max_length=15)
    course=models.CharField(max_length=100)
    session=models.CharField(max_length=50)
    sem=models.CharField(max_length=200)
    username=models.CharField(max_length=50)
    password=models.CharField(max_length=16)
    status = models.CharField(max_length=100)
    
    
class tbl_StudyMaterial(models.Model):
    id=models.IntegerField(primary_key=True,auto_created=True)
    title = models.CharField(max_length=200)
    material_type = models.CharField(max_length=50)
    course = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    material_file = models.FileField(
        upload_to='study_material/',
        null=True,
        blank=True
    )
    external_url = models.URLField(null=True,blank=True)
    status = models.CharField(max_length=20,default='Published')
    description = models.TextField( null=True,blank=True)
    create_by=models.ForeignKey(
        User,
        on_delete=models.SET_NULL,null=True
    )

    def _str_(self):
        return self.title
    
class tbl_assignment(models.Model):
    id = models.IntegerField(primary_key=True,auto_created=True)
    title = models.CharField(max_length=200)
    due_date = models.DateField()
    course = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    total_marks = models.IntegerField(default=20)
    attachment = models.FileField(upload_to='assignments/',null=True,blank=True)
    status = models.CharField(max_length=20)
    instructions = models.TextField(null=True,blank=True)
    create_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    Dor = models.DateTimeField()

    def __str__(self):
        return self.title
    
    
class GoogleCredential(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField(null=True,blank=True)
    connected = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return "Main Google Account"


class GoogleMeeting(models.Model):

    class_title = models.CharField(max_length=200)
    course = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    teacher = models.ForeignKey(User,on_delete=models.CASCADE)
    class_date = models.DateField()
    class_time = models.TimeField()
    duration = models.IntegerField()
    agenda = models.TextField(blank=True,null=True)
    meeting_url = models.URLField(blank=True,null=True)
    google_space_name = models.CharField(max_length=255,blank=True,null=True)
    status = models.CharField(max_length=20,default="scheduled")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.class_title
    
class Attendence(models.Model):
    id = models.IntegerField(primary_key=True,auto_created=True)
    Enrollment_no=models.CharField(max_length=50)
    name=models.CharField(max_length=225)
    course=models.CharField(max_length=100)
    mobile=models.CharField(max_length=15)
    Date=models.DateTimeField(null=True)
    teacher_name=models.CharField(max_length=100)
    status=models.CharField(max_length=50)
    
from django.db import models


class Announcement(models.Model):

    title = models.CharField(max_length=200)
    audience = models.CharField(max_length=50)
    priority = models.CharField(max_length=50)
    publish_date = models.DateField()
    expiry_date = models.DateField(blank=True,null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    
class Test(models.Model):
    id=models.IntegerField(primary_key=True,auto_created=True)
    test_title=models.CharField(max_length=200)
    test_date=models.DateField()
    course=models.CharField(max_length=200)
    subject=models.CharField(max_length=200)
    state_time=models.TimeField()
    duration=models.IntegerField()
    total_marks=models.IntegerField()
    status=models.CharField(max_length=100)
    
    
    
class Question_bank(models.Model):
    test=models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="questions"
    ) 
    question=models.CharField(max)
    option_a=models.CharField(max_length=200)
    option_b=models.CharField(max_length=200)
    option_c=models.CharField(max_length=200)
    option_d=models.CharField(max_length=200)
    correct_option=models.CharField(max_length=2)
    marks=models.IntegerField(max_length=2)
    
class TestResult(models.Model):

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    obtained_marks = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('student', 'test')

class TaskSubmit(models.Model):
    task=models.ForeignKey(
        tbl_assignment,
        on_delete=models.CASCADE
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    submitted_file=models.FileField(upload_to='submission/')
    submit_to=models.CharField(max_length=50)
    status=models.CharField(max_length=50)
    marks = models.PositiveIntegerField(default=0)
    dos=models.DateField()