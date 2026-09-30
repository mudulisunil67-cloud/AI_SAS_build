from django.urls import path

from . import views

app_name = "student"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("courses/", views.course_list, name="course_list"),
    path("courses/<int:pk>/enroll/", views.course_enroll, name="course_enroll"),
    path("courses/<int:pk>/leave/", views.course_leave, name="course_leave"),
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/<int:pk>/take/", views.exam_take, name="exam_take"),
    path("exams/<int:pk>/result/", views.exam_result, name="exam_result"),
    path("marks/", views.marks, name="marks"),
    path("attendance/", views.attendance, name="attendance"),
    path("classes/", views.classes, name="classes"),
    path("meetings/", views.meetings, name="meetings"),
]
