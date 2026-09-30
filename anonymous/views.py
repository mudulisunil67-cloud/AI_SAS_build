import os

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from faculty.models import Material

from .forms import LoginForm, RegisterForm, SubscribeForm
from .models import Subscriber, User


def home(request):
    return render(request, "anonymous/home.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(request, data=request.POST or None)
    next_url = request.POST.get("next") or request.GET.get("next", "")

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect("dashboard")

    return render(request, "anonymous/login.html", {"form": form, "next": next_url})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if user.is_approved:
            messages.success(request, "Account created. You can log in now.")
        else:
            messages.info(
                request,
                "Account created. An admin needs to approve faculty accounts before you can log in.",
            )
        return redirect("login")

    return render(request, "anonymous/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def dashboard(request):
    """Send each role to its own dashboard."""
    role = request.user.role
    if role == User.ADMIN:
        return redirect("myadmin:dashboard")
    if role == User.FACULTY:
        return redirect("faculty:dashboard")
    return redirect("student:dashboard")


@require_POST
def subscribe(request):
    form = SubscribeForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"].lower()
        subscriber, created = Subscriber.objects.get_or_create(email=email)
        if created:
            messages.success(request, f"You're subscribed. Updates will go to {email}.")
        elif not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save(update_fields=["is_active"])
            messages.success(request, "Welcome back. Your subscription is active again.")
        else:
            messages.info(request, "That email is already subscribed.")
    else:
        messages.error(request, "Enter a valid email address to subscribe.")
    return redirect(f"{reverse('home')}#subscribe")


@login_required
def material_download(request, pk):
    """Serve an uploaded class file only to the teacher, enrolled students and admins."""
    material = get_object_or_404(Material.objects.select_related("course"), pk=pk)
    user = request.user
    allowed = (
        user.role == User.ADMIN
        or (user.role == User.FACULTY and material.course.teacher_id == user.pk)
        or (user.role == User.STUDENT and material.course.students.filter(pk=user.pk).exists())
    )
    if not allowed:
        raise PermissionDenied
    if not material.file:
        raise Http404("This class entry has no file.")
    try:
        handle = material.file.open("rb")
    except FileNotFoundError:
        raise Http404("The file is missing from storage.")
    return FileResponse(
        handle,
        as_attachment=bool(request.GET.get("dl")),
        filename=os.path.basename(material.file.name),
    )
