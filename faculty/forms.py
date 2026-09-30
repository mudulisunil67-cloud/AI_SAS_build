import os

from django import forms

from AI_SAS.mixins import BootstrapFormMixin, DateInput, DateTimeLocalInput
from django.utils import timezone

from .models import Course, Exam, Material, Meeting, Question

MAX_UPLOAD_MB = 20
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".csv",
    ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mp3", ".zip",
}


class TeacherScopedForm(BootstrapFormMixin, forms.ModelForm):
    """Limits the `course` dropdown to the logged-in teacher's own courses."""

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None and "course" in self.fields:
            self.fields["course"].queryset = Course.objects.filter(teacher=teacher)


class CourseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "code", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()


class ExamForm(TeacherScopedForm):
    class Meta:
        model = Exam
        fields = ["course", "title", "instructions", "scheduled_at", "duration_minutes"]
        widgets = {
            "scheduled_at": DateTimeLocalInput(),
            "instructions": forms.Textarea(attrs={"rows": 3}),
        }


class QuestionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            "question_type", "text", "option_a", "option_b", "option_c", "option_d",
            "correct_option", "marks",
        ]
        widgets = {"text": forms.Textarea(attrs={"rows": 3})}


class MaterialForm(TeacherScopedForm):
    class Meta:
        model = Material
        fields = ["course", "title", "class_date", "description", "file", "link"]
        widgets = {
            "class_date": DateInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_file(self):
        upload = self.cleaned_data.get("file")
        if upload and hasattr(upload, "size"):
            if os.path.splitext(upload.name)[1].lower() not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    "This file type is not allowed. Use PDF, Office documents, images, audio, video or ZIP."
                )
            if upload.size > MAX_UPLOAD_MB * 1024 * 1024:
                raise forms.ValidationError(f"Files can be up to {MAX_UPLOAD_MB} MB.")
        return upload

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("file") and not cleaned.get("link") and not self.errors:
            raise forms.ValidationError("Attach a file or add a link so students have something to open.")
        return cleaned


class MeetingForm(TeacherScopedForm):
    class Meta:
        model = Meeting
        fields = ["course", "title", "agenda", "scheduled_at", "duration_minutes", "link", "location"]
        widgets = {
            "scheduled_at": DateTimeLocalInput(),
            "agenda": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_scheduled_at(self):
        when = self.cleaned_data["scheduled_at"]
        if not self.instance.pk and when < timezone.now():
            raise forms.ValidationError("Choose a time in the future.")
        return when
