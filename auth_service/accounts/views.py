import json
import random
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import User, Token


@csrf_exempt
@require_POST
def register(request):
    """
    POST /auth/register
    Body: { username, email, password }
    Creates a new user with hashed password.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    # Validation
    if not username or not email or not password:
        return JsonResponse({'error': 'username, email, and password are required'}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username already exists'}, status=409)

    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Email already exists'}, status=409)

    # Create user with hashed password
    user = User(username=username, email=email)
    user.set_password(password)
    user.save()

    return JsonResponse({
        'message': 'User registered successfully',
        'user_id': user.id,
        'username': user.username,
    }, status=201)


@csrf_exempt
@require_POST
def login(request):
    """
    POST /auth/login
    Body: { username, password }
    Verifies password → generates token → saves in DB → returns token.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return JsonResponse({'error': 'username and password are required'}, status=400)

    # Find user
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid username or password'}, status=401)

    # Verify password
    if not user.check_password(password):
        return JsonResponse({'error': 'Invalid username or password'}, status=401)

    # Generate token and save with expiry
    expiry_minutes = getattr(settings, 'TOKEN_EXPIRY_MINUTES', 30)
    token_str = Token.generate_token()
    token = Token.objects.create(
        token=token_str,
        user=user,
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
    )

    return JsonResponse({
        'token': token.token,
        'username': user.username,
        'expires_at': token.expires_at.isoformat(),
    }, status=200)


@csrf_exempt
@require_POST
def validate(request):
    """
    POST /auth/validate
    Body: { token }
    Checks if token exists and is not expired.
    Returns { valid: true/false, username }.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    token_str = data.get('token', '').strip()

    if not token_str:
        return JsonResponse({'valid': False, 'error': 'Token is required'}, status=400)

    try:
        token = Token.objects.select_related('user').get(token=token_str)
    except Token.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Token not found'}, status=200)

    # Check expiry
    if token.expires_at < timezone.now():
        # Token expired — delete it
        token.delete()
        return JsonResponse({'valid': False, 'error': 'Token expired'}, status=200)

    # Lazy Cleanup: 10% of the time, delete all expired tokens
    if random.random() < 0.1:
        Token.objects.filter(expires_at__lt=timezone.now()).delete()

    return JsonResponse({
        'valid': True,
        'username': token.user.username,
        'email': token.user.email,
        'user_id': token.user.id,
    }, status=200)

@csrf_exempt
@require_POST
def sso_login(request):
    """
    POST /auth/sso-login
    Body: { email, secret_internal_key }
    Validates secret key → gets or creates user → generates standard token.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    email = data.get('email', '').strip()
    secret_key = data.get('secret_internal_key', '')

    if not email or not secret_key:
        return JsonResponse({'error': 'email and secret_internal_key are required'}, status=400)

    # Validate Internal Key
    if secret_key != settings.INTERNAL_SSO_KEY:
        return JsonResponse({'error': 'Invalid internal SSO key'}, status=403)

    # Find or Create User (Google OAuth provides email, we generate username if needed)
    username = email.split('@')[0]
    
    # Try to find by email first
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Create new user for Google SSO
        user = User.objects.create(username=username, email=email)
        # Set a random unusable password since they login via Google
        user.set_password(Token.generate_token())
        user.save()

    # Generate token
    expiry_minutes = getattr(settings, 'TOKEN_EXPIRY_MINUTES', 30)
    token_str = Token.generate_token()
    token = Token.objects.create(
        token=token_str,
        user=user,
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
    )

    return JsonResponse({
        'token': token.token,
        'username': user.username,
        'expires_at': token.expires_at.isoformat(),
    }, status=200)


@csrf_exempt
@require_POST
def logout(request):
    """
    POST /auth/logout
    Body: { token }
    Deletes the token from DB.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    token_str = data.get('token', '').strip()

    if not token_str:
        return JsonResponse({'error': 'Token is required'}, status=400)

    deleted_count, _ = Token.objects.filter(token=token_str).delete()

    if deleted_count > 0:
        return JsonResponse({'message': 'Logged out successfully'}, status=200)
    else:
        return JsonResponse({'message': 'Token not found (already logged out)'}, status=200)
