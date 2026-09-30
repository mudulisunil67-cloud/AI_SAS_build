import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from AI_SAS.utils import paginate
from anonymous.decorators import admin_required
from anonymous.models import Subscriber
from faculty.models import Course, Exam, Submission

from .forms import AdminUserForm

User = get_user_model()


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@admin_required
def dashboard(request):
    role_counts = dict(User.objects.values_list("role").annotate(n=Count("id")).order_by())
    top_courses = Course.objects.annotate(n=Count("students")).order_by("-n", "name")[:6]

    chart_data = {
        "roles": {
            "labels": ["Students", "Faculty", "Admins"],
            "values": [
                role_counts.get(User.STUDENT, 0),
                role_counts.get(User.FACULTY, 0),
                role_counts.get(User.ADMIN, 0),
            ],
        },
        "enrollments": {
            "labels": [c.code for c in top_courses],
            "values": [c.n for c in top_courses],
        },
    }
    context = {
        "student_count": role_counts.get(User.STUDENT, 0),
        "faculty_count": role_counts.get(User.FACULTY, 0),
        "pending_faculty": User.objects.filter(is_approved=False).order_by("-date_joined"),
        "subscriber_count": Subscriber.objects.filter(is_active=True).count(),
        "course_count": Course.objects.count(),
        "exam_count": Exam.objects.count(),
        "submission_count": Submission.objects.count(),
        "recent_users": User.objects.order_by("-date_joined")[:6],
        "recent_subscribers": Subscriber.objects.all()[:5],
        "chart_data": chart_data,
    }
    return render(request, "admin/panel_dashboard.html", context)


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------
@admin_required
def user_list(request):
    users = User.objects.order_by("-date_joined")
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    status = request.GET.get("status", "")

    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q)
            | Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    if role in dict(User.ROLE_CHOICES):
        users = users.filter(role=role)
    if status == "pending":
        users = users.filter(is_approved=False)
    elif status == "inactive":
        users = users.filter(is_active=False)

    page_obj, querystring = paginate(request, users, 12)
    context = {
        "page_obj": page_obj,
        "querystring": querystring,
        "q": q,
        "role": role,
        "status": status,
        "roles": User.ROLE_CHOICES,
    }
    return render(request, "admin/panel_users.html", context)


@admin_required
def user_form(request, pk=None):
    target = get_object_or_404(User, pk=pk) if pk else None
    form = AdminUserForm(request.POST or None, instance=target)

    if request.method == "POST" and form.is_valid():
        editing_self = target is not None and target.pk == request.user.pk
        if editing_self and (form.cleaned_data["role"] != User.ADMIN or not form.cleaned_data["is_active"]):
            form.add_error(None, "You can't remove your own admin access or deactivate your own account.")
        else:
            saved = form.save()
            messages.success(request, f"{saved.display_name} was saved.")
            return redirect("myadmin:user_list")

    return render(
        request,
        "generic_form.html",
        {
            "form": form,
            "title": "Edit user" if target else "Add a user",
            "back_url": reverse("myadmin:user_list"),
            "submit_label": "Save user",
            "intro": "Faculty accounts need 'Approved to log in' switched on before they can sign in.",
            "multipart": False,
        },
    )


@admin_required
@require_POST
def user_approve(request, pk):
    target = get_object_or_404(User, pk=pk)
    target.is_approved = True
    target.save(update_fields=["is_approved"])
    messages.success(request, f"{target.display_name} was approved and can log in now.")
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("myadmin:user_list")


@admin_required
@require_POST
def user_toggle_active(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "You can't deactivate your own account.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        state = "activated" if target.is_active else "deactivated"
        messages.success(request, f"{target.display_name} was {state}.")
    return redirect("myadmin:user_list")


@admin_required
@require_POST
def user_delete(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "You can't delete your own account.")
    else:
        name = target.display_name
        target.delete()
        messages.success(request, f"{name} was deleted.")
    return redirect("myadmin:user_list")


# --------------------------------------------------------------------------
# Subscribers
# --------------------------------------------------------------------------
@admin_required
def subscriber_list(request):
    subscribers = Subscriber.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        subscribers = subscribers.filter(email__icontains=q)
    page_obj, querystring = paginate(request, subscribers, 15)
    context = {
        "page_obj": page_obj,
        "querystring": querystring,
        "q": q,
        "active_count": Subscriber.objects.filter(is_active=True).count(),
        "total_count": Subscriber.objects.count(),
    }
    return render(request, "admin/panel_subscribers.html", context)


@admin_required
@require_POST
def subscriber_toggle(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    subscriber.is_active = not subscriber.is_active
    subscriber.save(update_fields=["is_active"])
    messages.success(
        request, f"{subscriber.email} is now {'active' if subscriber.is_active else 'unsubscribed'}."
    )
    return redirect("myadmin:subscriber_list")


@admin_required
@require_POST
def subscriber_delete(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    email = subscriber.email
    subscriber.delete()
    messages.success(request, f"{email} was removed.")
    return redirect("myadmin:subscriber_list")


@admin_required
def subscriber_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="subscribers-{timezone.localdate().isoformat()}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(["email", "status", "subscribed_at"])
    for s in Subscriber.objects.all():
        writer.writerow([
            s.email,
            "active" if s.is_active else "unsubscribed",
            timezone.localtime(s.subscribed_at).strftime("%Y-%m-%d %H:%M"),
        ])
    return response


# --------------------------------------------------------------------------
# Courses overview
# --------------------------------------------------------------------------
@admin_required
def course_list(request):
    courses = Course.objects.select_related("teacher").annotate(
        student_count=Count("students", distinct=True), exam_count=Count("exams", distinct=True)
    )
    return render(request, "admin/panel_courses.html", {"courses": courses})


@admin_required
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    name = course.name
    course.delete()
    messages.success(request, f"Course {name} was deleted.")
    return redirect("myadmin:course_list")
