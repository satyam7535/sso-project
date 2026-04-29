import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class User(models.Model):
    """
    Users Table
    id | username | email | password (hashed) | created_at
    """
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # stored hashed
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        """Hash and set the password."""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verify the password against the stored hash."""
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'users'


class Token(models.Model):
    """
    Tokens Table
    id | token (random string) | user_id | created_at | expires_at
    """
    token = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @staticmethod
    def generate_token():
        """Generate a unique random token string."""
        return uuid.uuid4().hex + uuid.uuid4().hex  # 64-char token

    def __str__(self):
        return f"Token for {self.user.username} (expires {self.expires_at})"

    class Meta:
        db_table = 'tokens'
