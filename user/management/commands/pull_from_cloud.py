import os
import socket
import dj_database_url
from django.core.management.base import BaseCommand
from django.conf import settings
from user.sync_service import export_full_backup, import_full_backup

class Command(BaseCommand):
    help = "Downloads/Pulls all data from Render PostgreSQL database into local SQLite database"

    def handle(self, *args, **options):
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            self.stdout.write(self.style.ERROR("DATABASE_URL topilmadi. .env faylini tekshiring!"))
            return

        remote_config = dj_database_url.config(default=database_url, conn_max_age=600)
        if remote_config.get('ENGINE') == 'django.db.backends.postgresql':
            remote_config.setdefault('OPTIONS', {})['sslmode'] = 'require'

        host = remote_config.get('HOST')
        port = int(remote_config.get('PORT') or 5432)

        try:
            s = socket.create_connection((host, port), timeout=5)
            s.close()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Render serveriga ulanib bo'lmadi: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("[ONLINE] Render serveriga ulanish o'rnatildi."))

        remote_config.update({
            'AUTOCOMMIT': True,
            'ATOMIC_REQUESTS': False,
            'TIME_ZONE': settings.TIME_ZONE,
            'CONN_MAX_AGE': 600,
            'CONN_HEALTH_CHECKS': False,
        })
        settings.DATABASES['remote_cloud'] = remote_config

        self.stdout.write("1. Render serveridan ma'lumotlar yuklab olinmoqda...")
        cloud_backup = export_full_backup(using='remote_cloud')
        total = cloud_backup.get('total_records', 0)
        self.stdout.write(self.style.SUCCESS(f"   Yuklab olindi: {total} ta yozuv."))

        if total == 0:
            self.stdout.write(self.style.WARNING("Serverda yuklanadigan ma'lumot yo'q."))
            return

        self.stdout.write("2. Lokal SQLite bazasiga saqlanmoqda...")
        res = import_full_backup(cloud_backup, clear_existing=False)

        self.stdout.write(self.style.SUCCESS(f"[KOTARILDI OK] {res.get('imported_records', 0)} ta yozuv local SQLite bazaga saqlandi!"))
