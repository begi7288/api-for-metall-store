import random
import string
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger(__name__)

def generate_random_password(length=12):
    """
    Generates a secure random password that satisfies validate_password_strength.
    Requires at least one uppercase, lowercase, digit, and special character.
    """
    uppers = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lowers = "abcdefghijklmnopqrstuvwxyz"
    digits = "0123456789"
    specials = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~ʻ"
    
    password_chars = [
        random.choice(uppers),
        random.choice(lowers),
        random.choice(digits),
        random.choice(specials),
    ]
    
    all_pool = uppers + lowers + digits + specials
    password_chars += [random.choice(all_pool) for _ in range(length - 4)]
    
    random.shuffle(password_chars)
    return "".join(password_chars)

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
