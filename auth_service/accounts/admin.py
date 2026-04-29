from django.contrib import admin
from .models import User, Token


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'created_at')
    search_fields = ('username', 'email')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'token', 'user', 'created_at', 'expires_at')
    search_fields = ('token',)
    list_filter = ('created_at', 'expires_at')
