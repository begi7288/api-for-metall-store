import os
import socket
import dj_database_url
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from user.sync_service import export_full_backup

class Command(BaseCommand):
    help = "Syncs offline local SQLite data directly to remote Render PostgreSQL database"

    def handle(self, *args, **options):
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            self.stdout.write(self.style.ERROR("DATABASE_URL topilmadi. .env faylini tekshiring!"))
            return

        # Parse remote database configuration
        remote_config = dj_database_url.config(default=database_url, conn_max_age=600)
        if remote_config.get('ENGINE') == 'django.db.backends.postgresql':
            remote_config.setdefault('OPTIONS', {})['sslmode'] = 'require'

        host = remote_config.get('HOST')
        port = int(remote_config.get('PORT') or 5432)

        # Check connectivity to remote database
        try:
            s = socket.create_connection((host, port), timeout=5)
            s.close()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Serverga ulanib bo'lmadi (Internet yo'q): {e}"))
            return

        self.stdout.write(self.style.SUCCESS("[ONLINE] Server bilan aloqa o'rnatildi."))

        # 1. Export local SQLite data
        self.stdout.write("1. Lokal SQLite ma'lumotlari eksport qilinmoqda...")
        backup_data = export_full_backup()
        total = backup_data.get('total_records', 0)
        self.stdout.write(self.style.SUCCESS(f"   Eksport qilindi: {total} ta yozuv."))

        if total == 0:
            self.stdout.write(self.style.WARNING("Lokal bazada yuklanadigan ma'lumot yo'q."))
            return

        remote_config.update({
            'AUTOCOMMIT': True,
            'ATOMIC_REQUESTS': False,
            'TIME_ZONE': settings.TIME_ZONE,
            'CONN_MAX_AGE': 600,
            'CONN_HEALTH_CHECKS': False,
        })
        settings.DATABASES['remote_cloud'] = remote_config

        self.stdout.write("2. Remote Render databasega saqlanmoqda...")
        try:
            from user.sync_service import import_full_backup
            res = import_full_backup(backup_data, clear_existing=False, using='remote_cloud')
            self.stdout.write(self.style.SUCCESS(f"[YUKLANDI OK] Barcha {res.get('imported_records', 0)} ta ma'lumot Render PostgreSQL-ga muvaffaqiyatli yuklandi!"))
        except Exception as err:
            self.stdout.write(self.style.ERROR(f"Yuklashda xatolik yuz berdi: {err}"))

