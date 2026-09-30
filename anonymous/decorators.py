from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Allow only logged-in, approved users whose role is in `roles`."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles or not request.user.is_approved:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


admin_required = role_required("admin")
faculty_required = role_required("faculty")
student_required = role_required("student")
