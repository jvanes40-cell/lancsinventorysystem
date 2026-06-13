import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_system.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = 'admin_lancs'
email = 'admin@lancs.com'
password = 'PasswordLancs123' # Ganti sesuka lo

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Sukses! Akun {username} berhasil dibuat.")
else:
    print(f"Akun {username} sudah ada.")