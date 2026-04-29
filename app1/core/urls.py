from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('auth/google/callback/', views.google_callback, name='google-callback'),
]
