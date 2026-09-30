from django.contrib import admin

from .models import Answer, Attendance, Course, Exam, Material, Meeting, Question, Submission


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "teacher")
    search_fields = ("code", "name")
    filter_horizontal = ("students",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "scheduled_at", "duration_minutes", "is_published")
    list_filter = ("is_published", "course")
    inlines = [QuestionInline]


admin.site.register(Submission)
admin.site.register(Answer)
admin.site.register(Attendance)
admin.site.register(Material)
admin.site.register(Meeting)
