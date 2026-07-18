import os
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'temirdokon_v1.settings')
django.setup()

try:
    print("Making migrations...")
    call_command('makemigrations')
    print("Migrating...")
    call_command('migrate')
    print("Migrations successfully completed!")
except Exception as e:
    import traceback
    traceback.print_exc()
