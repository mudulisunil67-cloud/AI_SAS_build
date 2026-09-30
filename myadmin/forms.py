from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from AI_SAS.mixins import BootstrapFormMixin

User = get_user_model()


class AdminUserForm(BootstrapFormMixin, forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        help_text="Required for new users. Leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "username", "email", "phone",
            "role", "is_approved", "is_active",
        ]
        labels = {
            "is_approved": "Approved to log in",
            "is_active": "Account is active",
        }

    def clean_username(self):
        return self.cleaned_data["username"].strip()

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("password"):
            self.add_error("password", "Set a password for the new user.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if not user.is_superuser:
            user.is_staff = user.role == User.ADMIN
        if commit:
            user.save()
        return user
