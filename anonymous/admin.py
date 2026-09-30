from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Subscriber, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_approved", "is_active")
    list_filter = ("role", "is_approved", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Portal", {"fields": ("role", "phone", "is_approved")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Portal", {"fields": ("role", "phone", "is_approved")}),)


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "subscribed_at")
    list_filter = ("is_active",)
    search_fields = ("email",)
