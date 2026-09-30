from django.urls import path

from . import views

app_name = "faculty"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # courses
    path("courses/", views.course_list, name="course_list"),
    path("courses/new/", views.course_form, name="course_create"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    path("courses/<int:pk>/edit/", views.course_form, name="course_edit"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
    path("courses/<int:pk>/students/<int:student_id>/remove/", views.course_remove_student, name="course_remove_student"),
    # exams
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/new/", views.exam_form, name="exam_create"),
    path("exams/<int:pk>/", views.exam_detail, name="exam_detail"),
    path("exams/<int:pk>/edit/", views.exam_form, name="exam_edit"),
    path("exams/<int:pk>/delete/", views.exam_delete, name="exam_delete"),
    path("exams/<int:pk>/publish/", views.exam_toggle_publish, name="exam_toggle_publish"),
    path("exams/<int:pk>/questions/<int:question_id>/delete/", views.question_delete, name="question_delete"),
    path("exams/<int:pk>/submissions/", views.exam_submissions, name="exam_submissions"),
    path("submissions/<int:pk>/", views.submission_review, name="submission_review"),
    # attendance
    path("attendance/", views.attendance_mark, name="attendance_mark"),
    path("attendance/report/<int:course_id>/", views.attendance_report, name="attendance_report"),
    # daily classes
    path("classes/", views.material_list, name="material_list"),
    path("classes/new/", views.material_create, name="material_create"),
    path("classes/<int:pk>/delete/", views.material_delete, name="material_delete"),
    # meetings
    path("meetings/", views.meeting_list, name="meeting_list"),
    path("meetings/new/", views.meeting_create, name="meeting_create"),
    path("meetings/<int:pk>/delete/", views.meeting_delete, name="meeting_delete"),
]
