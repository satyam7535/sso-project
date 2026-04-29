import requests
from django.shortcuts import redirect
from django.conf import settings
from django.shortcuts import render


def home(request):
    """
    Home page. 
    SSOMiddleware already ensures the user is logged in before they reach here.
    """
    # The middleware attached the validated user info to request.sso_user
    user_info = getattr(request, 'sso_user', {})
    
    return render(request, 'home.html', {
        'username': user_info.get('username', 'User'),
        'email': user_info.get('email', ''),
        'app1_url': settings.APP1_LOGIN_URL.replace('/login/', ''),
    })
