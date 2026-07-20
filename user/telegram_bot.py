import random
import string
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger(__name__)

def generate_random_password(length=6):
    """
    Generates a 6-digit numeric verification code.
    """
    return "".join(random.choice("0123456789") for _ in range(6))


def send_telegram_message(text: str):
    """
    Sends a message to the configured Telegram bot.
    Does not crash the request in case of failure.
    """
    from django.conf import settings
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
    if not token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID not configured.")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = response.read().decode('utf-8')
            logger.info(f"Telegram message sent successfully: {res_data}")
            return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False
