import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from AI_SAS.utils import paginate
from anonymous.decorators import faculty_required

from .forms import CourseForm, ExamForm, MaterialForm, MeetingForm, QuestionForm
from .models import Attendance, Course, Exam, Material, Meeting, Submission
from .utils import course_attendance_stats

User = get_user_model()


def _form_page(request, form, title, back_url, submit_label="Save", intro="", multipart=False):
    return render(
        request,
        "generic_form.html",
        {
            "form": form,
            "title": title,
            "back_url": back_url,
            "submit_label": submit_label,
            "intro": intro,
            "multipart": multipart,
        },
    )


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@faculty_required
def dashboard(request):
    now = timezone.now()
    today = timezone.localdate()
    teacher = request.user

    courses = list(
        Course.objects.filter(teacher=teacher).annotate(student_count=Count("students", distinct=True))
    )
    exams = Exam.objects.filter(course__teacher=teacher).select_related("course")
    upcoming_exams = [
        e
        for e in exams.filter(scheduled_at__gte=now - datetime.timedelta(days=1)).order_by("scheduled_at")
        if e.status != Exam.CLOSED
    ][:5]

    attendance_pending = [
        c for c in courses
        if c.student_count and not Attendance.objects.filter(course=c, date=today).exists()
    ]

    context = {
        "course_count": len(courses),
        "student_count": User.objects.filter(courses_enrolled__teacher=teacher).distinct().count(),
        "pending_reviews": Submission.objects.filter(
            exam__course__teacher=teacher, status=Submission.SUBMITTED
        ).count(),
        "exam_count": exams.count(),
        "upcoming_exams": upcoming_exams,
        "meetings": Meeting.objects.filter(course__teacher=teacher, scheduled_at__gte=now)
        .select_related("course")[:5],
        "attendance_pending": attendance_pending,
        "today": today,
    }
    return render(request, "faculty/dashboard.html", context)


# --------------------------------------------------------------------------
# Courses
# --------------------------------------------------------------------------
@faculty_required
def course_list(request):
    courses = Course.objects.filter(teacher=request.user).annotate(
        student_count=Count("students", distinct=True), exam_count=Count("exams", distinct=True)
    )
    return render(request, "faculty/course_list.html", {"courses": courses})


@faculty_required
def course_form(request, pk=None):
    course = get_object_or_404(Course, pk=pk, teacher=request.user) if pk else None
    form = CourseForm(request.POST or None, instance=course)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.teacher = request.user
        obj.save()
        messages.success(request, f"Course {obj.name} saved.")
        return redirect("faculty:course_detail", pk=obj.pk)
    return _form_page(
        request, form,
        "Edit course" if course else "New course",
        reverse("faculty:course_list"),
        intro="Students can find your course by name and enroll themselves.",
    )


@faculty_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    stats = course_attendance_stats(course)
    students = [
        {"user": s, "stats": stats.get(s.pk)}
        for s in course.students.order_by("first_name", "username")
    ]
    context = {
        "course": course,
        "students": students,
        "exams": course.exams.all()[:6],
        "materials": course.materials.all()[:5],
        "meetings": course.meetings.filter(scheduled_at__gte=timezone.now())[:5],
    }
    return render(request, "faculty/course_detail.html", context)


@faculty_required
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    name = course.name
    course.delete()
    messages.success(request, f"Course {name} and everything in it was deleted.")
    return redirect("faculty:course_list")


@faculty_required
@require_POST
def course_remove_student(request, pk, student_id):
    course = get_object_or_404(Course, pk=pk, teacher=request.user)
    student = get_object_or_404(course.students, pk=student_id)
    course.students.remove(student)
    messages.success(request, f"{student.display_name} was removed from {course.name}.")
    return redirect("faculty:course_detail", pk=course.pk)


# --------------------------------------------------------------------------
# Exams
# --------------------------------------------------------------------------
@faculty_required
def exam_list(request):
    exams = (
        Exam.objects.filter(course__teacher=request.user)
        .select_related("course")
        .annotate(submission_count=Count("submissions", distinct=True))
    )
    return render(request, "faculty/exam_list.html", {"exams": exams})


@faculty_required
def exam_form(request, pk=None):
    exam = get_object_or_404(Exam, pk=pk, course__teacher=request.user) if pk else None
    if not Course.objects.filter(teacher=request.user).exists():
        messages.info(request, "Create a course first, then schedule an exam for it.")
        return redirect("faculty:course_create")

    form = ExamForm(request.POST or None, instance=exam, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        exam = form.save()
        messages.success(request, "Exam saved. Add questions, then publish it so students can see it.")
        return redirect("faculty:exam_detail", pk=exam.pk)
    return _form_page(
        request, form,
        "Edit exam" if exam else "Schedule an exam",
        reverse("faculty:exam_list"),
        submit_label="Save exam",
        intro="Students can start the exam at the start time and must finish before it ends.",
    )


@faculty_required
def exam_detail(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("course"), pk=pk, course__teacher=request.user)
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        question = form.save(commit=False)
        question.exam = exam
        question.save()
        messages.success(request, "Question added.")
        return redirect("faculty:exam_detail", pk=exam.pk)

    context = {
        "exam": exam,
        "questions": exam.questions.all(),
        "form": form,
        "submission_count": exam.submissions.count(),
        "pending_count": exam.submissions.filter(status=Submission.SUBMITTED).count(),
    }
    return render(request, "faculty/exam_detail.html", context)


@faculty_required
@require_POST
def exam_toggle_publish(request, pk):
    exam = get_object_or_404(Exam, pk=pk, course__teacher=request.user)
    if not exam.is_published and not exam.questions.exists():
        messages.error(request, "Add at least one question before publishing.")
    else:
        exam.is_published = not exam.is_published
        exam.save(update_fields=["is_published"])
        messages.success(
            request,
            "Published. Students in the course can now see this exam."
            if exam.is_published else "Unpublished. Students can no longer see this exam.",
        )
    return redirect("faculty:exam_detail", pk=exam.pk)


@faculty_required
@require_POST
def exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk, course__teacher=request.user)
    exam.delete()
    messages.success(request, "Exam deleted.")
    return redirect("faculty:exam_list")


@faculty_required
@require_POST
def question_delete(request, pk, question_id):
    exam = get_object_or_404(Exam, pk=pk, course__teacher=request.user)
    get_object_or_404(exam.questions, pk=question_id).delete()
    messages.success(request, "Question deleted.")
    return redirect("faculty:exam_detail", pk=exam.pk)


@faculty_required
def exam_submissions(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("course"), pk=pk, course__teacher=request.user)
    submissions = exam.submissions.select_related("student").order_by("student__first_name", "student__username")
    submitted_ids = [s.student_id for s in submissions]
    context = {
        "exam": exam,
        "submissions": submissions,
        "not_submitted": exam.course.students.exclude(pk__in=submitted_ids),
        "average": exam.submissions.aggregate(avg=Avg("score"))["avg"],
    }
    return render(request, "faculty/exam_submissions.html", context)


@faculty_required
def submission_review(request, pk):
    submission = get_object_or_404(
        Submission.objects.select_related("exam__course", "student"),
        pk=pk, exam__course__teacher=request.user,
    )
    answers = list(submission.answers.select_related("question"))

    if request.method == "POST":
        new_marks, errors = {}, []
        for number, answer in enumerate(answers, start=1):
            raw = request.POST.get(f"marks_{answer.pk}", "").strip()
            try:
                value = Decimal(raw)
            except InvalidOperation:
                errors.append(f"Question {number}: enter a number.")
                continue
            if not value.is_finite():
                errors.append(f"Question {number}: enter a number.")
                continue
            if value < 0 or value > answer.question.marks:
                errors.append(f"Question {number}: marks must be between 0 and {answer.question.marks}.")
                continue
            new_marks[answer.pk] = value.quantize(Decimal("0.01"))

        if errors:
            for message in errors:
                messages.error(request, message)
        else:
            with transaction.atomic():
                for answer in answers:
                    answer.marks_awarded = new_marks[answer.pk]
                    answer.is_graded = True
                    answer.save(update_fields=["marks_awarded", "is_graded"])
                submission.score = sum(new_marks.values(), Decimal("0"))
                submission.feedback = request.POST.get("feedback", "").strip()
                submission.status = Submission.GRADED
                submission.save(update_fields=["score", "feedback", "status"])
            messages.success(request, f"Marks saved for {submission.student.display_name}.")
            return redirect("faculty:exam_submissions", pk=submission.exam_id)

    return render(request, "faculty/submission_review.html", {"submission": submission, "answers": answers})


# --------------------------------------------------------------------------
# Attendance
# --------------------------------------------------------------------------
@faculty_required
def attendance_mark(request):
    courses = Course.objects.filter(teacher=request.user)
    source = request.POST if request.method == "POST" else request.GET
    today = timezone.localdate()

    try:
        att_date = datetime.date.fromisoformat(source.get("date") or "")
    except ValueError:
        att_date = today
    if att_date > today:
        messages.error(request, "You can't take attendance for a future date. Showing today instead.")
        att_date = today

    course = None
    course_id = source.get("course", "")
    if course_id.isdigit():
        course = courses.filter(pk=course_id).first()

    rows, already_marked = [], False
    if course:
        students = course.students.order_by("first_name", "username")
        if request.method == "POST":
            valid = {value for value, _ in Attendance.STATUS_CHOICES}
            with transaction.atomic():
                for student in students:
                    status = request.POST.get(f"status_{student.pk}")
                    if status in valid:
                        Attendance.objects.update_or_create(
                            course=course, student=student, date=att_date,
                            defaults={"status": status, "marked_by": request.user},
                        )
            messages.success(request, f"Attendance saved for {course.name} on {att_date:%d %b %Y}.")
            return redirect(
                f"{reverse('faculty:attendance_mark')}?course={course.pk}&date={att_date.isoformat()}"
            )

        existing = dict(
            Attendance.objects.filter(course=course, date=att_date).values_list("student_id", "status")
        )
        already_marked = bool(existing)
        rows = [
            {"student": s, "status": existing.get(s.pk, Attendance.PRESENT)} for s in students
        ]

    context = {
        "courses": courses,
        "course": course,
        "att_date": att_date,
        "today": today,
        "rows": rows,
        "already_marked": already_marked,
    }
    return render(request, "faculty/attendance_mark.html", context)


@faculty_required
def attendance_report(request, course_id):
    course = get_object_or_404(Course, pk=course_id, teacher=request.user)
    all_dates = list(
        Attendance.objects.filter(course=course).order_by("date").values_list("date", flat=True).distinct()
    )
    dates = all_dates[-15:]
    lookup = {
        (a.student_id, a.date): a.status
        for a in Attendance.objects.filter(course=course, date__in=dates)
    }
    stats = course_attendance_stats(course)
    rows = [
        {
            "student": s,
            "cells": [lookup.get((s.pk, d)) for d in dates],
            "stats": stats.get(s.pk),
        }
        for s in course.students.order_by("first_name", "username")
    ]
    context = {
        "course": course,
        "dates": dates,
        "rows": rows,
        "total_days": len(all_dates),
    }
    return render(request, "faculty/attendance_report.html", context)


# --------------------------------------------------------------------------
# Daily classes (materials)
# --------------------------------------------------------------------------
@faculty_required
def material_list(request):
    materials = Material.objects.filter(course__teacher=request.user).select_related("course")
    course_id = request.GET.get("course", "")
    if course_id.isdigit():
        materials = materials.filter(course_id=course_id)
    page_obj, querystring = paginate(request, materials, 10)
    return render(
        request,
        "faculty/material_list.html",
        {
            "page_obj": page_obj,
            "querystring": querystring,
            "courses": Course.objects.filter(teacher=request.user),
            "selected_course": course_id,
        },
    )


@faculty_required
def material_create(request):
    if not Course.objects.filter(teacher=request.user).exists():
        messages.info(request, "Create a course first, then add daily classes to it.")
        return redirect("faculty:course_create")

    form = MaterialForm(request.POST or None, request.FILES or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        material = form.save(commit=False)
        material.uploaded_by = request.user
        material.save()
        messages.success(request, "Class entry added. Enrolled students can see it now.")
        return redirect("faculty:material_list")
    return _form_page(
        request, form, "Add a daily class", reverse("faculty:material_list"),
        submit_label="Add class", multipart=True,
        intro="Upload notes, slides or a recording link for today's class.",
    )


@faculty_required
@require_POST
def material_delete(request, pk):
    material = get_object_or_404(Material, pk=pk, course__teacher=request.user)
    if material.file:
        material.file.delete(save=False)
    material.delete()
    messages.success(request, "Class entry deleted.")
    return redirect("faculty:material_list")


# --------------------------------------------------------------------------
# Meetings
# --------------------------------------------------------------------------
@faculty_required
def meeting_list(request):
    now = timezone.now()
    meetings = Meeting.objects.filter(course__teacher=request.user).select_related("course")
    context = {
        "upcoming": meetings.filter(scheduled_at__gte=now),
        "past": meetings.filter(scheduled_at__lt=now).order_by("-scheduled_at")[:10],
    }
    return render(request, "faculty/meeting_list.html", context)


@faculty_required
def meeting_create(request):
    if not Course.objects.filter(teacher=request.user).exists():
        messages.info(request, "Create a course first, then schedule a meeting with its students.")
        return redirect("faculty:course_create")

    form = MeetingForm(request.POST or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        meeting = form.save(commit=False)
        meeting.created_by = request.user
        meeting.save()
        messages.success(request, "Meeting scheduled. All students in the course can see it.")
        return redirect("faculty:meeting_list")
    return _form_page(
        request, form, "Schedule a meeting", reverse("faculty:meeting_list"),
        submit_label="Schedule meeting",
        intro="Every student enrolled in the selected course will see this meeting.",
    )


@faculty_required
@require_POST
def meeting_delete(request, pk):
    get_object_or_404(Meeting, pk=pk, course__teacher=request.user).delete()
    messages.success(request, "Meeting deleted.")
    return redirect("faculty:meeting_list")
