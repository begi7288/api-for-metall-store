import time
import requests
import logging
from django.core.management.base import BaseCommand
from user.sync_service import export_full_backup, import_full_backup

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Auto-sync local database with Render Cloud Server when internet connection is active."

    def add_arguments(self, parser):
        parser.add_argument('--server-url', type=str, default='https://superb-daffodil-52f855.netlify.app', help='Cloud server URL')
        parser.add_argument('--token', type=str, required=False, help='Auth Token for cloud API')
        parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')

    def handle(self, *args, **options):
        server_url = options['server-url'].rstrip('/')
        token = options.get('token', '')
        interval = options['interval']

        self.stdout.write(self.style.SUCCESS(f"Auto Sync Daemon boshlandi: {server_url} (Interval: {interval}s)"))

        headers = {'Authorization': f'Token {token}'} if token else {}

        while True:
            try:
                # 1. Ping cloud status
                status_resp = requests.get(f"{server_url}/users/sync/status/", headers=headers, timeout=5)
                if status_resp.status_code == 200:
                    self.stdout.write(self.style.SUCCESS("[ONLINE] Server bilan aloqa bor. Sinxronizatsiya qilinmoqda..."))

                    # 2. Push local data to cloud
                    local_backup = export_full_backup()
                    push_resp = requests.post(f"{server_url}/users/sync/push/", json=local_backup, headers=headers, timeout=30)
                    if push_resp.status_code == 200:
                        self.stdout.write(self.style.SUCCESS("[PUSH OK] Lokal ma'lumotlar serverga saqlandi."))

                    # 3. Pull latest cloud data
                    pull_resp = requests.get(f"{server_url}/users/sync/pull/", headers=headers, timeout=30)
                    if pull_resp.status_code == 200:
                        cloud_data = pull_resp.json()
                        import_full_backup(cloud_data, clear_existing=False)
                        self.stdout.write(self.style.SUCCESS("[PULL OK] Serverdagi ma'lumotlar lokal bazaga tiklandi."))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[OFFLINE] Internet aloqasi yo'q yoki server band: {e}"))

            time.sleep(interval)
