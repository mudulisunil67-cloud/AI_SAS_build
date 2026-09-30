from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("files/materials/<int:pk>/", views.material_download, name="material_download"),
]
