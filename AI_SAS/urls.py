from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),  # raw database admin (staff only)
    path("faculty/", include("faculty.urls")),
    path("student/", include("student.urls")),
    path("myadmin/", include("myadmin.urls")),
    path("", include("anonymous.urls")),
]
