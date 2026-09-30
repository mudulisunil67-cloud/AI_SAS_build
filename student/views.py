import datetime

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from AI_SAS.utils import paginate
from anonymous.decorators import student_required
from faculty.models import Answer, Attendance, Course, Exam, Material, Meeting, Question, Submission
from faculty.utils import LOW_ATTENDANCE, percent, student_attendance_stats

SUBMIT_GRACE = datetime.timedelta(seconds=90)  # allows for the auto-submit at time-up


def _enrolled(user):
    return user.courses_enrolled.all()


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@student_required
def dashboard(request):
    user, now = request.user, timezone.now()
    courses = _enrolled(user)

    submitted_ids = set(Submission.objects.filter(student=user).values_list("exam_id", flat=True))
    upcoming_exams = [
        e
        for e in Exam.objects.filter(
            course__in=courses, is_published=True, scheduled_at__gte=now - datetime.timedelta(days=1)
        )
        .select_related("course")
        .order_by("scheduled_at")
        if e.status != Exam.CLOSED and e.pk not in submitted_ids
    ][:4]

    summary = student_attendance_stats(user, courses)
    total = sum(row["total"] for row in summary)
    attended = sum(row["attended"] for row in summary)

    context = {
        "course_count": courses.count(),
        "overall_attendance": percent(attended, total),
        "low_attendance": LOW_ATTENDANCE,
        "upcoming_exams": upcoming_exams,
        "recent_marks": Submission.objects.filter(student=user).select_related("exam__course")[:4],
        "meetings": Meeting.objects.filter(course__in=courses, scheduled_at__gte=now)
        .select_related("course")[:4],
        "materials": Material.objects.filter(course__in=courses).select_related("course")[:4],
        "pending_exam_count": len(upcoming_exams),
    }
    return render(request, "student/dashboard.html", context)


# --------------------------------------------------------------------------
# Courses
# --------------------------------------------------------------------------
@student_required
def course_list(request):
    user = request.user
    context = {
        "enrolled": _enrolled(user).select_related("teacher"),
        "available": Course.objects.exclude(students=user).select_related("teacher"),
    }
    return render(request, "student/course_list.html", context)


@student_required
@require_POST
def course_enroll(request, pk):
    course = get_object_or_404(Course, pk=pk)
    course.students.add(request.user)
    messages.success(request, f"You're enrolled in {course.name}.")
    return redirect("student:course_list")


@student_required
@require_POST
def course_leave(request, pk):
    course = get_object_or_404(Course, pk=pk)
    course.students.remove(request.user)
    messages.success(request, f"You left {course.name}.")
    return redirect("student:course_list")


# --------------------------------------------------------------------------
# Exams
# --------------------------------------------------------------------------
@student_required
def exam_list(request):
    user = request.user
    exams = (
        Exam.objects.filter(course__in=_enrolled(user), is_published=True)
        .select_related("course")
        .order_by("-scheduled_at")
    )
    submissions = {s.exam_id: s for s in Submission.objects.filter(student=user)}
    items = [{"exam": e, "submission": submissions.get(e.pk)} for e in exams]
    return render(request, "student/exam_list.html", {"items": items})


@student_required
def exam_take(request, pk):
    exam = get_object_or_404(
        Exam.objects.select_related("course"),
        pk=pk, is_published=True, course__students=request.user,
    )
    if Submission.objects.filter(exam=exam, student=request.user).exists():
        messages.info(request, "You have already submitted this exam.")
        return redirect("student:exam_result", pk=exam.pk)

    now = timezone.now()
    if now < exam.scheduled_at:
        messages.info(request, "This exam hasn't started yet.")
        return redirect("student:exam_list")
    limit = exam.end_time + (SUBMIT_GRACE if request.method == "POST" else datetime.timedelta())
    if now > limit:
        messages.error(request, "This exam has closed and can no longer be taken.")
        return redirect("student:exam_list")

    questions = list(exam.questions.all())

    if request.method == "POST":
        try:
            with transaction.atomic():
                submission = Submission.objects.create(exam=exam, student=request.user)
                answers, score, needs_review = [], 0, False
                for question in questions:
                    raw = request.POST.get(f"q_{question.pk}", "").strip()
                    if question.question_type == Question.MCQ:
                        selected = raw.upper()[:1] if raw.upper()[:1] in ("A", "B", "C", "D") else ""
                        marks = question.marks if selected and selected == question.correct_option else 0
                        answers.append(Answer(
                            submission=submission, question=question, selected_option=selected,
                            marks_awarded=marks, is_graded=True,
                        ))
                        score += marks
                    else:
                        # Written answers wait for the teacher; blank ones score 0 straight away.
                        needs_review = needs_review or bool(raw)
                        answers.append(Answer(
                            submission=submission, question=question, text_answer=raw,
                            marks_awarded=0, is_graded=not raw,
                        ))
                Answer.objects.bulk_create(answers)
                submission.score = score
                submission.status = Submission.SUBMITTED if needs_review else Submission.GRADED
                submission.save(update_fields=["score", "status"])
        except IntegrityError:
            messages.info(request, "Your exam was already submitted.")
            return redirect("student:exam_result", pk=exam.pk)

        messages.success(request, "Exam submitted.")
        return redirect("student:exam_result", pk=exam.pk)

    context = {
        "exam": exam,
        "questions": questions,
        "seconds_left": max(int((exam.end_time - now).total_seconds()), 0),
    }
    return render(request, "student/exam_take.html", context)


@student_required
def exam_result(request, pk):
    exam = get_object_or_404(
        Exam.objects.select_related("course"),
        pk=pk, is_published=True, course__students=request.user,
    )
    submission = get_object_or_404(Submission, exam=exam, student=request.user)
    context = {
        "exam": exam,
        "submission": submission,
        "answers": submission.answers.select_related("question"),
        # Correct answers stay hidden until the exam window closes for everyone.
        "reveal": exam.status == Exam.CLOSED,
    }
    return render(request, "student/exam_result.html", context)


@student_required
def marks(request):
    submissions = list(
        Submission.objects.filter(student=request.user).select_related("exam__course")
    )
    graded = [s for s in submissions if s.status == Submission.GRADED and s.exam.total_marks]
    average = round(sum(s.percentage for s in graded) / len(graded), 1) if graded else None
    return render(request, "student/marks.html", {"submissions": submissions, "average": average})


# --------------------------------------------------------------------------
# Attendance
# --------------------------------------------------------------------------
@student_required
def attendance(request):
    user = request.user
    courses = _enrolled(user)
    summary = student_attendance_stats(user, courses)

    records = Attendance.objects.filter(student=user).select_related("course").order_by("-date")
    course_id = request.GET.get("course", "")
    if course_id.isdigit():
        records = records.filter(course_id=course_id)
    page_obj, querystring = paginate(request, records, 15)

    context = {
        "summary": summary,
        "page_obj": page_obj,
        "querystring": querystring,
        "courses": courses,
        "selected_course": course_id,
        "low_attendance": LOW_ATTENDANCE,
    }
    return render(request, "student/attendance.html", context)


# --------------------------------------------------------------------------
# Daily classes and meetings
# --------------------------------------------------------------------------
@student_required
def classes(request):
    courses = _enrolled(request.user)
    materials = Material.objects.filter(course__in=courses).select_related("course", "uploaded_by")
    course_id = request.GET.get("course", "")
    if course_id.isdigit():
        materials = materials.filter(course_id=course_id)
    page_obj, querystring = paginate(request, materials, 10)
    return render(
        request,
        "student/classes.html",
        {"page_obj": page_obj, "querystring": querystring, "courses": courses, "selected_course": course_id},
    )


@student_required
def meetings(request):
    now = timezone.now()
    all_meetings = Meeting.objects.filter(course__in=_enrolled(request.user)).select_related("course")
    context = {
        "upcoming": all_meetings.filter(scheduled_at__gte=now),
        "past": all_meetings.filter(scheduled_at__lt=now).order_by("-scheduled_at")[:10],
    }
    return render(request, "student/meetings.html", context)
