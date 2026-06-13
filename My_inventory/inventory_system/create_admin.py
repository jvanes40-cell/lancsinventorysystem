import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_system.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# FIX: Credentials are now read from environment variables instead of being
# hardcoded in source. Set these before running:
#
#   export DJANGO_ADMIN_USERNAME="admin_lancs"
#   export DJANGO_ADMIN_EMAIL="admin@lancs.com"
#   export DJANGO_ADMIN_PASSWORD="your-strong-password-here"
#   python create_admin.py
#
# If DJANGO_ADMIN_PASSWORD is not set, the script will refuse to run rather
# than fall back to an insecure default.

username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin_lancs')
email = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@lancs.com')
password = os.environ.get('DJANGO_ADMIN_PASSWORD')

if not password:
    raise SystemExit(
        "ERROR: DJANGO_ADMIN_PASSWORD environment variable is not set.\n"
        "Refusing to create a superuser with a default/hardcoded password.\n"
        "Set DJANGO_ADMIN_PASSWORD (and optionally DJANGO_ADMIN_USERNAME / "
        "DJANGO_ADMIN_EMAIL) and run this script again."
    )

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Sukses! Akun {username} berhasil dibuat.")
else:
    print(f"Akun {username} sudah ada.")