import requests
from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse

class SSOMiddleware:
    """
    Middleware to intercept every request and validate the SSO cookie.
    If valid, it attaches user info to the request.
    If invalid or missing, it redirects to the App 1 login page.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # We don't want to redirect if they are already trying to go to login,
        # but App 2 doesn't have a login page. Still, good practice to have an exempt list.
        self.exempt_paths = [
            '/static/',
            '/favicon.ico',
        ]

    def __call__(self, request):
        path = request.path_info

        # Skip exempt paths
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return self.get_response(request)

        token = request.COOKIES.get(settings.SSO_COOKIE_NAME)

        # No cookie → redirect to App 1 login
        if not token:
            return redirect(settings.APP1_LOGIN_URL)

        # Validate token with Auth Service
        try:
            resp = requests.post(
                f"{settings.AUTH_SERVICE_URL}/auth/validate",
                json={'token': token},
                timeout=5,
            )
            data = resp.json()
        except Exception:
            return redirect(settings.APP1_LOGIN_URL)

        if not data.get('valid', False):
            # Token invalid or expired → redirect to App 1 login
            return redirect(settings.APP1_LOGIN_URL)

        # Token is valid. Attach user info to request so views can use it.
        request.sso_user = {
            'username': data.get('username', 'User'),
            'email': data.get('email', ''),
            'id': data.get('user_id'),
        }

        response = self.get_response(request)
        return response
