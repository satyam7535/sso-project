from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import Token

class Command(BaseCommand):
    help = 'Deletes expired tokens from the database'

    def handle(self, *args, **options):
        now = timezone.now()
        deleted_count, _ = Token.objects.filter(expires_at__lt=now).delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} expired token(s)'))
