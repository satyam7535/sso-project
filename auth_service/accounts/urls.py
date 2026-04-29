from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register, name='auth-register'),
    path('login', views.login, name='auth-login'),
    path('validate', views.validate, name='auth-validate'),
    path('logout', views.logout, name='auth-logout'),
    path('sso-login', views.sso_login, name='auth-sso-login'),
]
