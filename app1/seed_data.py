"""
Startup seed script — run once after migrations.
Sets the correct Site domain and creates the Google SocialApp entry
so allauth can use Google OAuth without manual DB intervention.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings

# 1. Fix the Site domain
site_domain = os.environ.get('SITE_DOMAIN', '127.0.0.1:8001')
site = Site.objects.get(id=1)
site.domain = site_domain
site.name = site_domain
site.save()
print(f"[seed] Site domain set to: {site_domain}")

# 2. Seed Google SocialApp (delete-first to prevent duplicates)
client_id = settings.GOOGLE_CLIENT_ID
secret = settings.GOOGLE_CLIENT_SECRET

if client_id and secret:
    # Wipe any existing Google entries to avoid MultipleObjectsReturned
    SocialApp.objects.filter(provider='google').delete()
    app = SocialApp.objects.create(
        provider='google',
        name='Google',
        client_id=client_id,
        secret=secret,
    )
    app.sites.add(site)
    print(f"[seed] Google SocialApp created: {client_id[:30]}...")
else:
    print("[seed] WARNING: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set.")
