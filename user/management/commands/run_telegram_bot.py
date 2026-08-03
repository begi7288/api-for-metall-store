import time
import json
import logging
import urllib.request
import urllib.parse
from django.core.management.base import BaseCommand
from django.conf import settings
from user.telegram_bot import process_telegram_update

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs Telegram Bot long polling engine for multi-tenant notifications and bot management."

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Long polling timeout in seconds.'
        )

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN environment variable or setting is not configured!"))
            return

        self.stdout.write(self.style.SUCCESS("🤖 TemirDo'kon Telegram Bot Long Polling started successfully..."))

        offset = 0
        timeout = options.get('timeout', 30)

        while True:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout={timeout}"
                req = urllib.request.Request(url, headers={"User-Agent": "TemirDokonBot/1.0"})
                with urllib.request.urlopen(req, timeout=timeout + 10) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    if res_data.get("ok"):
                        updates = res_data.get("result", [])
                        for update in updates:
                            update_id = update.get("update_id")
                            offset = update_id + 1
                            try:
                                process_telegram_update(update)
                            except Exception as e:
                                logger.error(f"Error processing update {update_id}: {e}")
                                self.stderr.write(self.style.ERROR(f"Error processing update {update_id}: {e}"))
            except Exception as e:
                logger.error(f"Telegram polling loop exception: {e}")
                self.stderr.write(self.style.WARNING(f"Polling loop exception: {e}. Retrying in 5 seconds..."))
                time.sleep(5)
