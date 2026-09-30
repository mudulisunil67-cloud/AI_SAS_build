from django.urls import path

from . import views

app_name = "myadmin"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_form, name="user_create"),
    path("users/<int:pk>/edit/", views.user_form, name="user_edit"),
    path("users/<int:pk>/approve/", views.user_approve, name="user_approve"),
    path("users/<int:pk>/toggle-active/", views.user_toggle_active, name="user_toggle_active"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
    path("subscribers/", views.subscriber_list, name="subscriber_list"),
    path("subscribers/export/", views.subscriber_export, name="subscriber_export"),
    path("subscribers/<int:pk>/toggle/", views.subscriber_toggle, name="subscriber_toggle"),
    path("subscribers/<int:pk>/delete/", views.subscriber_delete, name="subscriber_delete"),
    path("courses/", views.course_list, name="course_list"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
]
