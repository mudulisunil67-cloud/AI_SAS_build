from django.db.models import Count, Q

from .models import Attendance

ATTENDED = (Attendance.PRESENT, Attendance.LATE)
LOW_ATTENDANCE = 75  # percent


def percent(attended, total):
    return round(attended * 100 / total) if total else None


def course_attendance_stats(course):
    """{student_id: {'total', 'attended', 'percent'}} for one course.
    Late counts as attended."""
    rows = (
        Attendance.objects.filter(course=course)
        .values("student_id")
        .annotate(total=Count("id"), attended=Count("id", filter=Q(status__in=ATTENDED)))
        .order_by()
    )
    return {
        r["student_id"]: {
            "total": r["total"],
            "attended": r["attended"],
            "percent": percent(r["attended"], r["total"]),
        }
        for r in rows
    }


def student_attendance_stats(student, courses):
    """One summary dict per course for a student (zeros if nothing recorded yet)."""
    rows = {
        r["course_id"]: r
        for r in Attendance.objects.filter(student=student)
        .values("course_id")
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status=Attendance.PRESENT)),
            absent=Count("id", filter=Q(status=Attendance.ABSENT)),
            late=Count("id", filter=Q(status=Attendance.LATE)),
        )
        .order_by()
    }
    summary = []
    for course in courses:
        row = rows.get(course.pk, {})
        present, absent, late = row.get("present", 0), row.get("absent", 0), row.get("late", 0)
        total = row.get("total", 0)
        attended = present + late
        summary.append(
            {
                "course": course,
                "total": total,
                "present": present,
                "absent": absent,
                "late": late,
                "attended": attended,
                "percent": percent(attended, total),
            }
        )
    return summary
