import os
import time
import json
import threading
import logging
import urllib.request
from django.conf import settings

logger = logging.getLogger(__name__)


def _telegram_polling_loop():
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        logger.warning("[TELEGRAM BOT] TOKEN not configured. Background bot loop skipped.")
        return

    offset = 0
    timeout = 10

    logger.info("🤖 [TELEGRAM BOT] Auto background polling started.")

    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout={timeout}"
            req = urllib.request.Request(url, headers={"User-Agent": "TemirDokonBot/1.0"})
            with urllib.request.urlopen(req, timeout=timeout + 5) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                if res_data.get("ok"):
                    updates = res_data.get("result", [])
                    if updates:
                        from user.telegram_bot import process_telegram_update
                        for update in updates:
                            update_id = update.get("update_id")
                            offset = update_id + 1
                            try:
                                process_telegram_update(update)
                            except Exception as e:
                                logger.error(f"[TELEGRAM BOT] Error processing update {update_id}: {e}")
        except Exception as e:
            logger.debug(f"[TELEGRAM BOT] Polling loop exception: {e}")
            time.sleep(5)


_bot_thread_started = False


def start_telegram_bot_background():
    global _bot_thread_started
    if _bot_thread_started:
        return
    _bot_thread_started = True

    t = threading.Thread(target=_telegram_polling_loop, daemon=True)
    t.start()
