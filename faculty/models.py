"""Academic models shared by the faculty and student apps."""
import os
from datetime import timedelta
from functools import cached_property

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Course(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="courses_taught",
        limit_choices_to={"role": "faculty"},
    )
    students = models.ManyToManyField(
        User, related_name="courses_enrolled", blank=True,
        limit_choices_to={"role": "student"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Exam(models.Model):
    UPCOMING, LIVE, CLOSED = "upcoming", "live", "closed"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="exams")
    title = models.CharField(max_length=160)
    instructions = models.TextField(blank=True)
    scheduled_at = models.DateTimeField("Starts at")
    duration_minutes = models.PositiveIntegerField(
        "Duration (minutes)", default=30,
        validators=[MinValueValidator(1), MaxValueValidator(600)],
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self):
        return self.title

    @property
    def end_time(self):
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)

    @cached_property
    def total_marks(self):
        return self.questions.aggregate(total=Sum("marks"))["total"] or 0

    @property
    def status(self):
        now = timezone.now()
        if now < self.scheduled_at:
            return self.UPCOMING
        if now <= self.end_time:
            return self.LIVE
        return self.CLOSED


class Question(models.Model):
    MCQ, TEXT = "mcq", "text"
    TYPE_CHOICES = [(MCQ, "Multiple choice"), (TEXT, "Written answer")]
    OPTION_CHOICES = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=4, choices=TYPE_CHOICES, default=MCQ)
    text = models.TextField("Question")
    option_a = models.CharField("Option A", max_length=255, blank=True)
    option_b = models.CharField("Option B", max_length=255, blank=True)
    option_c = models.CharField("Option C", max_length=255, blank=True)
    option_d = models.CharField("Option D", max_length=255, blank=True)
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES, blank=True)
    marks = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.text[:60]

    def option_text(self, letter):
        return getattr(self, f"option_{letter.lower()}", "") if letter else ""

    @property
    def correct_text(self):
        return self.option_text(self.correct_option)

    @property
    def choices(self):
        """[(letter, text), ...] for the options that were filled in."""
        pairs = [(letter, self.option_text(letter)) for letter in "ABCD"]
        return [(letter, text) for letter, text in pairs if text]

    def clean(self):
        if self.question_type == self.MCQ:
            filled = [letter for letter, _ in self.choices]
            if len(filled) < 2:
                raise ValidationError("A multiple-choice question needs at least two options.")
            if self.correct_option not in filled:
                raise ValidationError("Pick a correct option that has text.")
        else:
            self.correct_option = ""


class Submission(models.Model):
    SUBMITTED, GRADED = "submitted", "graded"
    STATUS_CHOICES = [(SUBMITTED, "Awaiting review"), (GRADED, "Graded")]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=SUBMITTED)
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ("exam", "student")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.exam}"

    @property
    def percentage(self):
        total = self.exam.total_marks
        return round(float(self.score) * 100 / total, 1) if total else 0


class Answer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    selected_option = models.CharField(max_length=1, blank=True)
    text_answer = models.TextField(blank=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_graded = models.BooleanField(default=False)

    class Meta:
        unique_together = ("submission", "question")
        ordering = ["question_id"]

    @property
    def selected_text(self):
        return self.question.option_text(self.selected_option)

    @property
    def is_correct(self):
        return (
            self.question.question_type == Question.MCQ
            and bool(self.selected_option)
            and self.selected_option == self.question.correct_option
        )


class Attendance(models.Model):
    PRESENT, ABSENT, LATE = "present", "absent", "late"
    STATUS_CHOICES = [(PRESENT, "Present"), (ABSENT, "Absent"), (LATE, "Late")]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_records")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default=PRESENT)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("course", "student", "date")
        ordering = ["-date", "student__first_name"]

    def __str__(self):
        return f"{self.student} {self.date} {self.status}"


def material_upload_path(instance, filename):
    return f"materials/course_{instance.course_id}/{filename}"


class Material(models.Model):
    """A daily class entry: notes, slides, a recording link, etc."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    class_date = models.DateField(default=timezone.localdate)
    file = models.FileField(upload_to=material_upload_path, blank=True)
    link = models.URLField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-class_date", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def filename(self):
        return os.path.basename(self.file.name) if self.file else ""


class Meeting(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="meetings")
    title = models.CharField(max_length=160)
    agenda = models.TextField(blank=True)
    scheduled_at = models.DateTimeField("Starts at")
    duration_minutes = models.PositiveIntegerField(
        "Duration (minutes)", default=45, validators=[MinValueValidator(5)]
    )
    link = models.URLField("Meeting link", blank=True)
    location = models.CharField(max_length=160, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return self.title
