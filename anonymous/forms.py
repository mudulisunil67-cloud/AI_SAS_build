from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from AI_SAS.mixins import BootstrapFormMixin

from .models import User


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_approved:
            raise forms.ValidationError(
                "Your account is waiting for admin approval. You can log in once it is approved.",
                code="pending_approval",
            )


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    ROLE_CHOICES = [(User.STUDENT, "Student"), (User.FACULTY, "Faculty")]
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="I am a")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email", "phone", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "email"):
            self.fields[name].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.is_approved = user.role == User.STUDENT
        if commit:
            user.save()
        return user


class SubscribeForm(forms.Form):
    email = forms.EmailField()
