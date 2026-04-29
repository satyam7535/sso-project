import json
import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse


def _get_auth_url(path):
    """Build full Auth Service URL."""
    return f"{settings.AUTH_SERVICE_URL}/auth/{path}"


def _set_sso_cookie(response, token):
    """Set the SSO token cookie on the response."""
    response.set_cookie(
        key=settings.SSO_COOKIE_NAME,
        value=token,
        max_age=settings.SSO_COOKIE_AGE,
        httponly=True,
        samesite='Lax',
        path='/',
        domain=settings.SSO_COOKIE_DOMAIN,
    )
    return response


def _clear_sso_cookie(response):
    """Clear the SSO token cookie."""
    response.delete_cookie(
        key=settings.SSO_COOKIE_NAME,
        path='/',
        domain=settings.SSO_COOKIE_DOMAIN,
    )
    return response


def _validate_token(token):
    """Validate token with Auth Service. Returns (valid, data)."""
    try:
        resp = requests.post(
            _get_auth_url('validate'),
            json={'token': token},
            timeout=5,
        )
        data = resp.json()
        return data.get('valid', False), data
    except Exception:
        return False, {}


def index(request):
    """Root URL — redirect to home if logged in, else to login."""
    token = request.COOKIES.get(settings.SSO_COOKIE_NAME)
    if token:
        valid, _ = _validate_token(token)
        if valid:
            return redirect('home')
    return redirect('login')


def login_page(request):
    """
    GET  → show login form
    POST → authenticate via Auth Service → set cookie → redirect to home
    """
    if request.method == 'GET':
        # If already logged in, redirect to home
        token = request.COOKIES.get(settings.SSO_COOKIE_NAME)
        if token:
            valid, _ = _validate_token(token)
            if valid:
                return redirect('home')
        return render(request, 'login.html', {
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        })

    # POST — handle login
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')

    if not username or not password:
        return render(request, 'login.html', {
            'error': 'Username and password are required.',
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        })

    try:
        resp = requests.post(
            _get_auth_url('login'),
            json={'username': username, 'password': password},
            timeout=5,
        )
        data = resp.json()
    except Exception as e:
        return render(request, 'login.html', {
            'error': f'Auth Service unavailable: {e}',
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        })

    if resp.status_code == 200 and 'token' in data:
        # Success — set cookie and redirect to home
        response = redirect('home')
        _set_sso_cookie(response, data['token'])
        return response
    else:
        return render(request, 'login.html', {
            'error': data.get('error', 'Login failed.'),
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        })


def register_page(request):
    """
    GET  → show registration form
    POST → register via Auth Service → auto login → redirect to home
    """
    if request.method == 'GET':
        return render(request, 'register.html')

    # POST — handle registration
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')

    if not username or not email or not password:
        return render(request, 'register.html', {
            'error': 'All fields are required.',
        })

    if password != confirm_password:
        return render(request, 'register.html', {
            'error': 'Passwords do not match.',
        })

    # Register with Auth Service
    try:
        resp = requests.post(
            _get_auth_url('register'),
            json={'username': username, 'email': email, 'password': password},
            timeout=5,
        )
        data = resp.json()
    except Exception as e:
        return render(request, 'register.html', {
            'error': f'Auth Service unavailable: {e}',
        })

    if resp.status_code == 201:
        # Auto-login after registration
        try:
            login_resp = requests.post(
                _get_auth_url('login'),
                json={'username': username, 'password': password},
                timeout=5,
            )
            login_data = login_resp.json()
            if login_resp.status_code == 200 and 'token' in login_data:
                response = redirect('home')
                _set_sso_cookie(response, login_data['token'])
                return response
        except Exception:
            pass
        # Fallback: redirect to login page
        return redirect('login')
    else:
        return render(request, 'register.html', {
            'error': data.get('error', 'Registration failed.'),
        })


def home(request):
    """
    Dashboard page — requires valid SSO token.
    """
    token = request.COOKIES.get(settings.SSO_COOKIE_NAME)

    if not token:
        return redirect('login')

    valid, data = _validate_token(token)
    if not valid:
        response = redirect('login')
        _clear_sso_cookie(response)
        return response

    return render(request, 'home.html', {
        'username': data.get('username', 'User'),
        'email': data.get('email', ''),
        'app2_url': settings.APP2_URL,
    })


def logout_view(request):
    """
    Logout — delete token from Auth Service → clear cookie → redirect to login.
    """
    token = request.COOKIES.get(settings.SSO_COOKIE_NAME)

    if token:
        try:
            requests.post(
                _get_auth_url('logout'),
                json={'token': token},
                timeout=5,
            )
        except Exception:
            pass  # Best effort

    response = redirect('login')
    _clear_sso_cookie(response)
    return response


def google_callback(request):
    """
    Google OAuth callback handler.
    After Google login via allauth, this view:
    1. Gets the logged-in Django user (created by allauth)
    2. Logs in with Auth Service using INTERNAL_SSO_KEY
    3. Sets SSO cookie
    4. Redirects to home
    """
    if not request.user.is_authenticated:
        return render(request, 'login.html', {
            'error': "Google authentication failed. User is not authenticated in Django.",
        })

    user = request.user
    email = user.email

    # Login to Auth Service to get token using secret internal key
    try:
        resp = requests.post(
            _get_auth_url('sso-login'),
            json={
                'email': email,
                'secret_internal_key': settings.INTERNAL_SSO_KEY,
            },
            timeout=5,
        )
        data = resp.json()
        if resp.status_code == 200 and 'token' in data:
            response = redirect('home')
            _set_sso_cookie(response, data['token'])
            return response
        else:
            return render(request, 'login.html', {
                'error': f"Auth Service Error: {data}",
                'google_client_id': settings.GOOGLE_CLIENT_ID,
            })
    except Exception as e:
        return render(request, 'login.html', {
            'error': f"Exception connecting to Auth Service: {e}",
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        })
