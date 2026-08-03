import random
import string
import urllib.request
import urllib.parse
import json
import logging
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db import models

logger = logging.getLogger(__name__)


def generate_random_password(length=6):
    """
    Generates a 6-digit numeric verification code.
    """
    return "".join(random.choice("0123456789") for _ in range(6))


def normalize_phone(phone_str: str) -> str:
    """
    Normalizes phone number to standard digits string for reliable matching.
    """
    if not phone_str:
        return ""
    digits = "".join(c for c in str(phone_str) if c.isdigit())
    if len(digits) == 9:
        return "998" + digits
    return digits


def verify_xodim_password(xodim, raw_password: str) -> bool:
    """
    Verifies raw password against Xodim user account or hashed parol field.
    """
    if not xodim or not raw_password:
        return False
    if xodim.user and xodim.user.check_password(raw_password):
        return True
    if xodim.parol:
        if check_password(raw_password, xodim.parol):
            return True
        if xodim.parol == raw_password:
            return True
    return False


def send_telegram_message(text: str, chat_id=None, reply_markup=None):
    """
    Sends a message to a specific Telegram chat_id or default TELEGRAM_CHAT_ID.
    Does not crash the request in case of failure.
    """
    import sys
    if 'test' in sys.argv and not getattr(settings, 'TEST_TELEGRAM_BOT_HTTP', False):
        return True

    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    target_chat_id = chat_id or getattr(settings, 'TELEGRAM_CHAT_ID', None)
    if not token or not target_chat_id:
        logger.warning("Telegram Bot Token or Target Chat ID not configured.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": str(target_chat_id),
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

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
            logger.info(f"Telegram message sent successfully to {target_chat_id}: {res_data}")
            return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message to {target_chat_id}: {e}")
        return False


def send_business_telegram_notification(biznes, text: str):
    """
    Sends a notification to all active Telegram users linked to the given business.
    Falls back to global TELEGRAM_CHAT_ID if no active linked user is found.
    """
    if not biznes:
        send_telegram_message(text)
        return

    from user.models import Xodim
    # Priority 1: Send to business admins
    admins = Xodim.objects.filter(
        biznes=biznes,
        is_active=True,
        rol='admin',
        telegram_notifications_enabled=True
    ).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")

    target_xodims = admins if admins.exists() else Xodim.objects.filter(
        biznes=biznes,
        is_active=True,
        telegram_notifications_enabled=True
    ).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")

    sent_any = False
    sent_chats = set()
    for xodim in target_xodims:
        cid = str(xodim.telegram_chat_id).strip()
        if cid and cid not in sent_chats:
            sent_chats.add(cid)
            send_telegram_message(text, chat_id=cid)
            sent_any = True

    if not sent_any:
        # Fallback to default configured chat ID if available
        send_telegram_message(text)


def notify_sale(sale):
    try:
        from sales.models import Sale

        xodim_ism = f"{sale.xodim.ism} {sale.xodim.familiya}".strip() if sale.xodim else "Noma'lum"
        dokon_nomi = sale.dokon.nomi if sale.dokon else "Noma'lum"
        mijoz_nomi = f"{sale.mijoz.ism} {sale.mijoz.familiya}".strip() if sale.mijoz else "Anonim Mijoz"
        vaqt_str = sale.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M") if sale.yaratilgan_vaqt else ""

        sale_date = sale.yaratilgan_vaqt.date() if sale.yaratilgan_vaqt else timezone.now().date()
        daily_count = Sale.objects.filter(
            biznes=sale.biznes,
            yaratilgan_vaqt__date=sale_date,
            holat='yakunlangan',
            id__lte=sale.id
        ).count()
        if daily_count == 0:
            daily_count = 1

        items_lines = []
        for idx, item in enumerate(sale.elementlar.select_related('mahsulot', 'mahsulot__olchov_birligi').all(), 1):
            m_nomi = item.mahsulot.nomi if item.mahsulot else "Mahsulot"
            unit = item.mahsulot.olchov_birligi.nomi if (item.mahsulot and item.mahsulot.olchov_birligi) else "dona"
            items_lines.append(
                f"{idx}. <b>{m_nomi}</b>\n"
                f"   └ {item.miqdori} {unit} × {item.sotish_narxi:,.0f} = <code>{item.jami_summa:,.0f}</code> so'm"
            )

        items_text = "\n".join(items_lines) if items_lines else "<i>Mahsulotlar ko'rsatilmadi</i>"

        naqd = getattr(sale, 'naqd_summa', Decimal('0.00')) or Decimal('0.00')
        karta = getattr(sale, 'karta_summa', Decimal('0.00')) or Decimal('0.00')
        nasiya = getattr(sale, 'nasiya_summa', Decimal('0.00')) or Decimal('0.00')

        if naqd == Decimal('0.00') and karta == Decimal('0.00') and nasiya == Decimal('0.00'):
            if sale.tolov_usuli == 'naqd':
                naqd = sale.yakuniy_summa
            elif sale.tolov_usuli == 'karta':
                karta = sale.yakuniy_summa
            elif sale.tolov_usuli == 'nasiya':
                nasiya = sale.yakuniy_summa
            elif sale.tolov_usuli == 'aralash':
                naqd = getattr(sale, 'tolangan_summa', Decimal('0.00'))
                nasiya = getattr(sale, 'nasiya_summa', Decimal('0.00'))

        tolov_turlari_lines = []
        if naqd > Decimal('0.00'):
            tolov_turlari_lines.append(f"💵 <b>Naqd:</b> <code>{naqd:,.0f}</code> so'm")
        if karta > Decimal('0.00'):
            tolov_turlari_lines.append(f"💳 <b>Karta:</b> <code>{karta:,.0f}</code> so'm")
        if nasiya > Decimal('0.00'):
            tolov_turlari_lines.append(f"⚠️ <b>Nasiya (Qarz):</b> <code>{nasiya:,.0f}</code> so'm")

        if not tolov_turlari_lines:
            tolov_usuli_disp = sale.get_tolov_usuli_display() if hasattr(sale, 'get_tolov_usuli_display') else sale.tolov_usuli
            tolov_turlari_lines.append(f"💳 <b>{tolov_usuli_disp}:</b> <code>{sale.yakuniy_summa:,.0f}</code> so'm")

        msg_parts = [
            f"<b>🛒 SOTUV #{daily_count}</b>",
            f"📅 <b>Sana:</b> {vaqt_str}",
            f"🏪 <b>Do'kon:</b> {dokon_nomi}",
            f"👤 <b>Xodim:</b> {xodim_ism}",
            f"🤝 <b>Mijoz:</b> {mijoz_nomi}",
        ]
        if sale.mijoz:
            tel = getattr(sale.mijoz, 'telefon_raqam_1', None) or getattr(sale.mijoz, 'telefon_raqam', None)
            if tel:
                msg_parts.append(f"📞 <b>Tel:</b> {tel}")

        msg_parts.append(f"\n📦 <b>Mahsulotlar:</b>\n{items_text}\n")

        if sale.chegirma_summasi > 0:
            ch_turi = "%" if sale.chegirma_turi == 'foiz' else "so'm"
            msg_parts.append(f"🏷 <b>Chegirma ({sale.chegirma_qiymati} {ch_turi}):</b> <code>-{sale.chegirma_summasi:,.0f}</code> so'm")

        msg_parts.append(f"💰 <b>Yakuniy summa:</b> <code>{sale.yakuniy_summa:,.0f}</code> so'm")
        msg_parts.append("💳 <b>To'lov turlari va summalari:</b>")
        for line in tolov_turlari_lines:
            msg_parts.append(f"   └ {line}")

        send_business_telegram_notification(sale.biznes, "\n".join(msg_parts))
    except Exception as e:
        logger.error(f"Failed to build sale notification: {e}")


def notify_transfer(transfer):
    try:
        dokondan = transfer.dokondan.nomi if transfer.dokondan else "Noma'lum"
        dokonga = transfer.dokonga.nomi if transfer.dokonga else "Noma'lum"
        biznes = transfer.dokondan.biznes if transfer.dokondan else None
        msg = (
            f"<b>🚚 Do'konlararo Transfer #{transfer.id}:</b>\n"
            f"📤 Qayerdan: {dokondan}\n"
            f"📥 Qayerga: {dokonga}\n"
            f"📦 Nom: {transfer.nomi}\n"
            f"🔢 Miqdori: {transfer.miqdori}\n"
        )
        send_business_telegram_notification(biznes, msg)
    except Exception as e:
        logger.error(f"Failed to build transfer notification: {e}")


def notify_write_off(write_off):
    try:
        xodim = write_off.yaratgan_xodim.ism if getattr(write_off, 'yaratgan_xodim', None) else "Noma'lum"
        biznes = getattr(write_off, 'biznes', None) or (write_off.dokon.biznes if getattr(write_off, 'dokon', None) else None)
        msg = (
            f"<b>⚠️ Hisobdan Chiqarish #{write_off.id}:</b>\n"
            f"👤 Xodim: {xodim}\n"
            f"📝 Sabab: {write_off.sababi}\n"
            f"💰 Jami Summa: <code>{write_off.sotish_summasi:,.2f}</code> so'm\n"
        )
        send_business_telegram_notification(biznes, msg)
    except Exception as e:
        logger.error(f"Failed to build write_off notification: {e}")


def notify_import(import_obj):
    try:
        biznes = getattr(import_obj, 'biznes', None)
        msg = (
            f"<b>📥 Yangi Kirim (Import) #{import_obj.id}:</b>\n"
            f"📦 Mahsulot: {import_obj.mahsulot_nomi}\n"
            f"🔢 Miqdori: {import_obj.miqdori}\n"
            f"💵 Kelish Narxi: <code>{import_obj.kelish_narxi:,.2f}</code> so'm\n"
        )
        send_business_telegram_notification(biznes, msg)
    except Exception as e:
        logger.error(f"Failed to build import notification: {e}")


def get_phone_keyboard():
    return {
        "keyboard": [
            [{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }


def get_main_keyboard():
    return {
        "keyboard": [
            [{"text": "📊 Bugungi hisobot"}, {"text": "🛒 So'nggi sotuvlar"}],
            [{"text": "⚠️ Hisobdan chiqarishlar"}, {"text": "📦 Kam qolgan mahsulotlar"}],
            [{"text": "⚙️ Sozlamalar"}]
        ],
        "resize_keyboard": True
    }


def get_settings_keyboard(is_enabled: bool):
    status_text = " Yoqilgan 🟢" if is_enabled else " O'chirilgan 🔴"
    return {
        "keyboard": [
            [{"text": f"🔔 Bildirishnomalar:{status_text}"}],
            [{"text": "🚪 Tizimdan chiqish"}, {"text": "🔙 Asosiy menyu"}]
        ],
        "resize_keyboard": True
    }


def get_today_summary_for_biznes(biznes):
    if not biznes:
        return "<i>Biznes ma'lumoti topilmadi</i>"

    today = timezone.now().date()
    from sales.models import Sale, SaleItem
    from products.models import WriteOff, Mahsulot

    sales_today = Sale.objects.filter(biznes=biznes, yaratilgan_vaqt__date=today, holat='yakunlangan')
    count_today = sales_today.count()
    revenue_today = sales_today.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')

    naqd = sales_today.filter(tolov_usuli='naqd').aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
    karta = sales_today.filter(tolov_usuli='karta').aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
    nasiya = sales_today.filter(tolov_usuli='nasiya').aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')

    writeoffs_today = WriteOff.objects.filter(biznes=biznes, yaratilgan_vaqt__date=today)
    writeoff_count = writeoffs_today.count()
    writeoff_sum = writeoffs_today.aggregate(t=models.Sum('sotish_summasi'))['t'] or Decimal('0.00')

    msg = (
        f"<b>📊 BUGUNGI HISOBOT ({today.strftime('%d.%m.%Y')})</b>\n"
        f"🏢 Biznes: <b>{biznes.nomi}</b>\n\n"
        f"🛒 <b>Sotuvlar soni:</b> {count_today} ta\n"
        f"💰 <b>Jami tushum:</b> <code>{revenue_today:,.0f}</code> so'm\n\n"
        f"💵 Naqd: <code>{naqd:,.0f}</code> so'm\n"
        f"💳 Karta: <code>{karta:,.0f}</code> so'm\n"
        f"⚠️ Nasiya: <code>{nasiya:,.0f}</code> so'm\n\n"
        f"⚠️ <b>Hisobdan chiqarishlar:</b> {writeoff_count} ta (<code>{writeoff_sum:,.0f}</code> so'm)"
    )
    return msg


def get_recent_sales_for_biznes(biznes, limit=5):
    if not biznes:
        return "<i>Biznes ma'lumoti topilmadi</i>"

    from sales.models import Sale
    sales = Sale.objects.filter(biznes=biznes).order_by('-yaratilgan_vaqt')[:limit]
    if not sales:
        return "ℹ️ Hali sotuvlar mavjud emas."

    lines = [f"<b>🛒 SO'NGGI SOTUVLAR ({biznes.nomi}):</b>\n"]
    for s in sales:
        v_str = s.yaratilgan_vaqt.strftime("%d.%m %H:%M") if s.yaratilgan_vaqt else ""
        x_ism = s.xodim.ism if s.xodim else "Noma'lum"
        lines.append(
            f"🔹 <b>#{s.kod} ({v_str})</b>\n"
            f"   👤 Xodim: {x_ism} | 💳 To'lov: {s.get_tolov_usuli_display()}\n"
            f"   💰 Summa: <code>{s.yakuniy_summa:,.0f}</code> so'm\n"
        )
    return "\n".join(lines)


def get_recent_write_offs_for_biznes(biznes, limit=5):
    if not biznes:
        return "<i>Biznes ma'lumoti topilmadi</i>"

    from products.models import WriteOff
    items = WriteOff.objects.filter(biznes=biznes).order_by('-yaratilgan_vaqt')[:limit]
    if not items:
        return "ℹ️ Hali hisobdan chiqarishlar mavjud emas."

    lines = [f"<b>⚠️ HISOBDAN CHIQA RISHLAR ({biznes.nomi}):</b>\n"]
    for w in items:
        v_str = w.yaratilgan_vaqt.strftime("%d.%m %H:%M") if w.yaratilgan_vaqt else ""
        lines.append(
            f"🔸 <b>#{w.id} ({v_str})</b>\n"
            f"   📝 Sabab: {w.sababi}\n"
            f"   💰 Summa: <code>{w.sotish_summasi:,.0f}</code> so'm\n"
        )
    return "\n".join(lines)


def get_low_stock_for_biznes(biznes, limit=10):
    if not biznes:
        return "<i>Biznes ma'lumoti topilmadi</i>"

    from products.models import Mahsulot
    products = Mahsulot.objects.filter(biznes=biznes, is_active=True).extra(
        where=["miqdori <= ogohlantirish"]
    )[:limit]

    if not products:
        return "✅ Ombor xavfsiz holatda. Kam qolgan mahsulotlar yo'q."

    lines = [f"<b>📦 KAM QOLGAN MAHSULOTLAR ({biznes.nomi}):</b>\n"]
    for p in products:
        unit = p.olchov_birligi.nomi if p.olchov_birligi else "dona"
        lines.append(f"⚠️ <b>{p.nomi}</b>: <code>{p.miqdori} {unit}</code> (Min: {p.ogohlantirish})")

    return "\n".join(lines)


def process_telegram_update(update: dict):
    """
    Core engine that processes Telegram Update JSON payload.
    Supports user contact login, password verification, per-business notification toggling,
    and business monitoring commands.
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        return True

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    if not chat_id:
        return True

    text = message.get("text", "").strip() if message.get("text") else ""
    contact = message.get("contact")

    from user.models import TelegramSession, Xodim

    session, _ = TelegramSession.objects.get_or_create(chat_id=str(chat_id))

    # Command: /start or /login
    if text.startswith("/start") or text.startswith("/login"):
        if session.state == 'AUTHENTICATED' and session.xodim and session.xodim.is_active:
            xodim = session.xodim
            b_nomi = xodim.biznes.nomi if xodim.biznes else 'Mavjud emas'
            msg = (
                f"👋 Salom, <b>{xodim.ism} {xodim.familiya}</b>!\n"
                f"🏢 Biznes: <b>{b_nomi}</b>\n\n"
                f"Tizimga ulangan ekansiz. Kerakli bo'limni tanlang:"
            )
            send_telegram_message(msg, chat_id=chat_id, reply_markup=get_main_keyboard())
        else:
            session.state = 'AWAITING_PHONE'
            session.xodim = None
            session.save()
            msg = (
                "👋 Assalomu alaykum! <b>TemirDo'kon</b> botiga xush kelibsiz.\n\n"
                "Biznesingiz bildirishnomalarini olish va tizimni boshqarish uchun 📱 <b>Telefon raqamingizni yuboring</b>."
            )
            send_telegram_message(msg, chat_id=chat_id, reply_markup=get_phone_keyboard())
        return True

    # User provided contact via button or typed phone number in AWAITING_PHONE state
    if contact or (session.state == 'AWAITING_PHONE' and text):
        phone_raw = contact.get("phone_number") if contact else text
        norm_phone = normalize_phone(phone_raw)

        # Match Xodim by normalized phone
        all_xodims = Xodim.objects.filter(is_active=True)
        found_xodim = None
        for x in all_xodims:
            if normalize_phone(x.telefon_raqam) == norm_phone:
                found_xodim = x
                break

        if not found_xodim:
            msg = (
                f"❌ Telefon raqam (<code>{phone_raw}</code>) bo'yicha tizimda foydalanuvchi topilmadi.\n\n"
                "Iltimos, dasturga kirish uchun ro'yxatdan o'tgan telefon raqamingizni yuboring."
            )
            send_telegram_message(msg, chat_id=chat_id, reply_markup=get_phone_keyboard())
            return True

        session.temp_phone = norm_phone
        session.xodim = found_xodim
        session.state = 'AWAITING_PASSWORD'
        session.save()

        b_nomi = found_xodim.biznes.nomi if found_xodim.biznes else 'Mavjud emas'
        msg = (
            f"👤 Foydalanuvchi topildi: <b>{found_xodim.ism} {found_xodim.familiya}</b>\n"
            f"🏢 Biznes: <b>{b_nomi}</b>\n\n"
            "🔑 Davom etish uchun <b>parolingizni kiriting</b>:"
        )
        send_telegram_message(msg, chat_id=chat_id, reply_markup={"remove_keyboard": True})
        return True

    # State: AWAITING_PASSWORD
    if session.state == 'AWAITING_PASSWORD':
        if not session.xodim:
            session.state = 'AWAITING_PHONE'
            session.save()
            send_telegram_message("❌ Sessiya xatosi. Iltimos, /start bosib qaytadan urinib ko'ring.", chat_id=chat_id, reply_markup=get_phone_keyboard())
            return True

        if verify_xodim_password(session.xodim, text):
            xodim = session.xodim
            xodim.telegram_chat_id = str(chat_id)
            xodim.telegram_notifications_enabled = True
            xodim.save()

            session.state = 'AUTHENTICATED'
            session.save()

            b_nomi = xodim.biznes.nomi if xodim.biznes else 'Mavjud emas'
            msg = (
                f"✅ <b>Muvaffaqiyatli tizimga ulandingiz!</b>\n\n"
                f"👤 Xodim: <b>{xodim.ism} {xodim.familiya}</b>\n"
                f"🏢 Biznes: <b>{b_nomi}</b>\n\n"
                f"🔔 Endi ushbu biznesga oid sotuvlar va bildirishnomalar ushbu chatga yuboriladi."
            )
            send_telegram_message(msg, chat_id=chat_id, reply_markup=get_main_keyboard())
        else:
            send_telegram_message("❌ <b>Parol noto'g'ri.</b> Qayta kiriting:", chat_id=chat_id)
        return True

    # State: AUTHENTICATED commands
    if session.state == 'AUTHENTICATED' and session.xodim:
        xodim = session.xodim
        biznes = xodim.biznes

        if text == "📊 Bugungi hisobot":
            res = get_today_summary_for_biznes(biznes)
            send_telegram_message(res, chat_id=chat_id, reply_markup=get_main_keyboard())
        elif text == "🛒 So'nggi sotuvlar":
            res = get_recent_sales_for_biznes(biznes)
            send_telegram_message(res, chat_id=chat_id, reply_markup=get_main_keyboard())
        elif text == "⚠️ Hisobdan chiqarishlar":
            res = get_recent_write_offs_for_biznes(biznes)
            send_telegram_message(res, chat_id=chat_id, reply_markup=get_main_keyboard())
        elif text == "📦 Kam qolgan mahsulotlar":
            res = get_low_stock_for_biznes(biznes)
            send_telegram_message(res, chat_id=chat_id, reply_markup=get_main_keyboard())
        elif text == "⚙️ Sozlamalar":
            msg = (
                f"<b>⚙️ SOZLAMALAR</b>\n\n"
                f"👤 Xodim: {xodim.ism} {xodim.familiya}\n"
                f"📞 Telefon: {xodim.telefon_raqam}\n"
                f"🏢 Biznes: {biznes.nomi if biznes else 'Mavjud emas'}\n"
                f"🔔 Bildirishnomalar: {'<b>Yoqilgan 🟢</b>' if xodim.telegram_notifications_enabled else '<b>O\'chirilgan 🔴</b>'}"
            )
            send_telegram_message(msg, chat_id=chat_id, reply_markup=get_settings_keyboard(xodim.telegram_notifications_enabled))
        elif text.startswith("🔔 Bildirishnomalar:"):
            xodim.telegram_notifications_enabled = not xodim.telegram_notifications_enabled
            xodim.save()
            st = "Yoqildi 🟢" if xodim.telegram_notifications_enabled else "O'chirildi 🔴"
            send_telegram_message(f"🔔 Bildirishnomalar holati: <b>{st}</b>", chat_id=chat_id, reply_markup=get_settings_keyboard(xodim.telegram_notifications_enabled))
        elif text == "🚪 Tizimdan chiqish":
            xodim.telegram_chat_id = None
            xodim.save()
            session.state = 'AWAITING_PHONE'
            session.xodim = None
            session.save()
            send_telegram_message("🚪 Tizimdan muvaffaqiyatli chiqdingiz. Qayta ulanish uchun telefon raqam yuboring.", chat_id=chat_id, reply_markup=get_phone_keyboard())
        elif text == "🔙 Asosiy menyu":
            send_telegram_message("📱 Asosiy menyu:", chat_id=chat_id, reply_markup=get_main_keyboard())
        else:
            send_telegram_message("ℹ️ Kerakli bo'limni pastdagi tugmalar orqali tanlang:", chat_id=chat_id, reply_markup=get_main_keyboard())
        return True

    # Default fallback
    session.state = 'AWAITING_PHONE'
    session.save()
    send_telegram_message("👋 Assalomu alaykum! Tizimdan foydalanish uchun 📱 <b>Telefon raqamingizni yuboring</b>.", chat_id=chat_id, reply_markup=get_phone_keyboard())
    return True


def send_daily_report(target_date=None, biznes=None):
    """
    Sends daily summary report to Telegram users of the specified business (or all businesses).
    """
    try:
        from datetime import timedelta
        from sales.models import Sale, SaleItem
        from products.models import Dokon, WriteOff
        from orders.models import SupplierOrderPayment
        from user.models import Mijoz, MijozQarzi, MijozTolovi, Xodim, Biznes

        if not target_date:
            target_date = timezone.now().date() - timedelta(days=1)

        prev_date = target_date - timedelta(days=1)
        date_str = target_date.strftime("%Y-%m-%d")

        target_bizneses = [biznes] if biznes else Biznes.objects.all()

        for biz in target_bizneses:
            sales_today = Sale.objects.filter(biznes=biz, yaratilgan_vaqt__date=target_date, holat='yakunlangan')
            sales_prev = Sale.objects.filter(biznes=biz, yaratilgan_vaqt__date=prev_date, holat='yakunlangan')

            dokonlar = Dokon.objects.filter(biznes=biz)

            jami_tushum_today = sales_today.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            jami_tushum_prev = sales_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')

            sp_exp_today = SupplierOrderPayment.objects.filter(buyurtma__biznes=biz, yaratilgan_vaqt__date=target_date).aggregate(t=models.Sum('tolangan_summa'))['t'] or Decimal('0.00')
            wo_exp_today = WriteOff.objects.filter(biznes=biz, holat='yakunlangan', yaratilgan_vaqt__date=target_date).aggregate(t=models.Sum('kelish_summasi'))['t'] or Decimal('0.00')
            xarajat_today = sp_exp_today + wo_exp_today

            sof_tushum_today = max(Decimal('0.00'), jami_tushum_today - xarajat_today)

            msg = (
                f"<b>📊 {biz.nomi} - {date_str} KUNLIK HISOBOT</b>\n\n"
                f"💰 <b>Jami tushum:</b> <code>{jami_tushum_today:,.0f}</code> UZS\n"
                f"💸 <b>Xarajatlar:</b> <code>{xarajat_today:,.0f}</code> UZS\n"
                f"📈 <b>Sof tushum:</b> <code>{sof_tushum_today:,.0f}</code> UZS\n"
                f"🛒 <b>Sotuvlar soni:</b> {sales_today.count()} ta\n"
            )
            send_business_telegram_notification(biz, msg)
    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")
