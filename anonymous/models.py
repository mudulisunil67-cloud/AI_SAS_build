from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ADMIN = "admin"
    FACULTY = "faculty"
    STUDENT = "student"
    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (FACULTY, "Faculty"),
        (STUDENT, "Student"),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=STUDENT)
    phone = models.CharField(max_length=20, blank=True)
    # Students are approved automatically; new faculty wait for an admin.
    is_approved = models.BooleanField(default=True)

    class Meta:
        ordering = ["first_name", "username"]

    def save(self, *args, **kwargs):
        # Superusers created with `createsuperuser` always get the admin role.
        if self.is_superuser:
            self.role = self.ADMIN
            self.is_approved = True
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return self.display_name


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email
