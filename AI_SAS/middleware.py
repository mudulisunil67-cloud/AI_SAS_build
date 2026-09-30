"""
Route protection for the whole project.

1. Only the routes listed in PUBLIC_VIEW_NAMES can be opened without logging in.
   Everything else (including unknown URLs) sends anonymous visitors to the login page.
2. URLs under /faculty/, /student/ and /myadmin/ require the matching role.
3. Accounts that are not approved yet (new faculty sign-ups) are logged out.

Views also carry role decorators, so protection does not depend on this file alone.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse
from django.utils.http import urlencode

PUBLIC_VIEW_NAMES = {"home", "login", "register", "subscribe"}

ROLE_PREFIXES = (
    ("/faculty/", "faculty"),
    ("/student/", "student"),
    ("/myadmin/", "admin"),
)


class AccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        if path.startswith(settings.STATIC_URL):
            return self.get_response(request)

        try:
            match = resolve(path)
        except Resolver404:
            match = None

        if match is not None and not match.namespaces and match.url_name in PUBLIC_VIEW_NAMES:
            return self.get_response(request)

        user = request.user
        if not user.is_authenticated:
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{reverse('login')}?{query}")

        if not user.is_approved:
            logout(request)
            messages.warning(request, "Your account is waiting for admin approval.")
            return redirect("login")

        for prefix, role in ROLE_PREFIXES:
            if path.startswith(prefix) and user.role != role:
                raise PermissionDenied

        return self.get_response(request)
