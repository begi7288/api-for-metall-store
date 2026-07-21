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
    import sys
    if 'test' in sys.argv:
        return True

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


def notify_sale(sale):
    try:
        xodim = sale.xodim.ism if sale.xodim else "Noma'lum"
        msg = (
            f"<b>🛒 Yangi Sotuv #{sale.id}:</b>\n"
            f"👤 Xodim: {xodim}\n"
            f"💰 Jami Summa: <code>{sale.yakuniy_summa:,.2f}</code> so'm\n"
            f"💳 To'lov usuli: {sale.tolov_usuli}\n"
        )
        if sale.mijoz:
            msg += f"🤝 Mijoz: {sale.mijoz.ism}\n"
        send_telegram_message(msg)
    except Exception as e:
        logger.error(f"Failed to build sale notification: {e}")


def notify_transfer(transfer):
    try:
        dokondan = transfer.dokondan.nomi if transfer.dokondan else "Noma'lum"
        dokonga = transfer.dokonga.nomi if transfer.dokonga else "Noma'lum"
        msg = (
            f"<b>🚚 Do'konlararo Transfer #{transfer.id}:</b>\n"
            f"📤 Qayerdan: {dokondan}\n"
            f"📥 Qayerga: {dokonga}\n"
            f"📦 Nom: {transfer.nomi}\n"
            f"🔢 Miqdori: {transfer.miqdori}\n"
        )
        send_telegram_message(msg)
    except Exception as e:
        logger.error(f"Failed to build transfer notification: {e}")


def notify_write_off(write_off):
    try:
        xodim = write_off.yaratgan_xodim.ism if write_off.yaratgan_xodim else "Noma'lum"
        msg = (
            f"<b>⚠️ Hisobdan Chiqarish #{write_off.id}:</b>\n"
            f"👤 Xodim: {xodim}\n"
            f"📝 Sabab: {write_off.sababi}\n"
            f"💰 Jami Summa: <code>{write_off.sotish_summasi:,.2f}</code> so'm\n"
        )
        send_telegram_message(msg)
    except Exception as e:
        logger.error(f"Failed to build write_off notification: {e}")


def notify_import(import_obj):
    try:
        msg = (
            f"<b>📥 Yangi Kirim (Import) #{import_obj.id}:</b>\n"
            f"📦 Mahsulot: {import_obj.mahsulot_nomi}\n"
            f"🔢 Miqdori: {import_obj.miqdori}\n"
            f"💵 Kelish Narxi: <code>{import_obj.kelish_narxi:,.2f}</code> so'm\n"
        )
        send_telegram_message(msg)
    except Exception as e:
        logger.error(f"Failed to build import notification: {e}")
