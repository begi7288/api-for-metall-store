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
import re

logger = logging.getLogger(__name__)


def clean_name(name_str):
    if not name_str:
        return ""
    cleaned = re.sub(r'\b(foydalanuvchi|user)\b', '', name_str, flags=re.IGNORECASE)
    return ' '.join(cleaned.split())


def get_customer_total_debt(mijoz):
    from user.models import MijozQarzi
    from django.db.models import Sum
    from decimal import Decimal
    return MijozQarzi.objects.filter(mijoz=mijoz).exclude(holat='tolangan').aggregate(total=Sum('qoldiq_summa'))['total'] or Decimal('0.00')


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


def send_business_telegram_notification(biznes, text: str, allowed_roles=None):
    """
    Sends a notification to all active Telegram users/sessions linked to the given business.
    Falls back to global TELEGRAM_CHAT_ID if no active linked user is found.
    """
    if not biznes:
        send_telegram_message(text)
        return

    from user.models import Xodim, TelegramSession

    sent_chats = set()

    # 1. Check authenticated TelegramSessions for this business
    active_sessions = TelegramSession.objects.filter(
        xodim__biznes=biznes,
        xodim__is_active=True,
        xodim__telegram_notifications_enabled=True,
        state='AUTHENTICATED'
    )
    if allowed_roles:
        active_sessions = active_sessions.filter(xodim__rol__in=allowed_roles)
    active_sessions = active_sessions.select_related('xodim')

    for sess in active_sessions:
        cid = str(sess.chat_id).strip()
        if cid:
            sent_chats.add(cid)

    # 2. Check Xodim.telegram_chat_id for this business
    xodims = Xodim.objects.filter(
        biznes=biznes,
        is_active=True,
        telegram_notifications_enabled=True
    ).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
    if allowed_roles:
        xodims = xodims.filter(rol__in=allowed_roles)

    for x in xodims:
        cid = str(x.telegram_chat_id).strip()
        if cid:
            sent_chats.add(cid)

    # Send to all gathered user chat IDs
    if sent_chats:
        for cid in sent_chats:
            send_telegram_message(text, chat_id=cid)
    else:
        # Fallback to default configured chat ID if no user session is found
        if not allowed_roles or 'admin' in allowed_roles:
            send_telegram_message(text)


def notify_sale(sale):
    try:
        from sales.models import Sale

        x_ism = sale.xodim.ism if sale.xodim else "Noma'lum"
        x_fam = sale.xodim.familiya if sale.xodim and sale.xodim.familiya else ""
        xodim_ism = clean_name(f"{x_ism} {x_fam}".strip()) if sale.xodim else "Noma'lum"
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

        naqd = Decimal('0.00')
        karta = Decimal('0.00')
        nasiya = Decimal('0.00')

        if sale.tolov_usuli == 'aralash' and sale.eslatma:
            import re
            cleaned_eslatma = re.sub(r'\s+', '', sale.eslatma)
            naqd_match = re.search(r'(?:Naqd|Cash)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
            karta_match = re.search(r'(?:Plastikkarta|Plastik|Karta|Card|Uzcard|Humo)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
            nasiya_match = re.search(r'(?:Nasiya|Qarz|Credit)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
            
            if naqd_match:
                naqd = Decimal(naqd_match.group(1))
            if karta_match:
                karta = Decimal(karta_match.group(1))
            if nasiya_match:
                nasiya = Decimal(nasiya_match.group(1))

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

        # Notify the customer if linked to Telegram
        if sale.mijoz and sale.mijoz.telegram_chat_id and sale.mijoz.telegram_notifications_enabled:
            from user.models import MijozQarzi
            from django.db.models import Sum
            
            total_qarz = MijozQarzi.objects.filter(mijoz=sale.mijoz).exclude(holat='tolangan').aggregate(total=Sum('qoldiq_summa'))['total'] or Decimal('0.00')
            b_nomi = sale.biznes.nomi if sale.biznes else "Do'kon"
            
            cust_items = []
            for item_idx, item in enumerate(sale.elementlar.select_related('mahsulot', 'mahsulot__olchov_birligi').all(), 1):
                m_nomi = item.mahsulot.nomi if item.mahsulot else "Mahsulot"
                unit = item.mahsulot.olchov_birligi.nomi if (item.mahsulot and item.mahsulot.olchov_birligi) else "dona"
                cust_items.append(f"   {item_idx}. {m_nomi} ({item.miqdori} {unit}) - <code>{item.jami_summa:,.0f}</code> so'm")
            
            cust_items_text = "\n".join(cust_items) if cust_items else "Mahsulotlar ko'rsatilmadi"
            
            cust_msg = (
                f"🛍 <b>Yangi xarid muvaffaqiyatli amalga oshirildi!</b>\n\n"
                f"🏪 <b>Do'kon:</b> {b_nomi}\n"
                f"📅 <b>Sana:</b> {vaqt_str}\n\n"
                f"📦 <b>Sotib olingan mahsulotlar:</b>\n{cust_items_text}\n\n"
                f"💰 <b>Jami summa:</b> <code>{sale.yakuniy_summa:,.0f}</code> so'm\n"
            )
            if tolov_turlari_lines:
                cust_msg += "💳 <b>To'lov turlari va summalari:</b>\n"
                for line in tolov_turlari_lines:
                    cust_msg += f"   └ {line}\n"
                cust_msg += "\n"

            if total_qarz > 0:
                cust_msg += f"💳 <b>Hisobdagi qarz qoldig'ingiz:</b> <code>{total_qarz:,.0f}</code> so'm\n\n"
            else:
                cust_msg += f"🎉 <b>Hisobingiz to'liq yopildi.</b> Qarz qoldig'ingiz yo'q! 😊\n\n"
                
            cust_msg += "Xaridingiz uchun tashakkur! Biz sizni qadrlaymiz! 😊"
            
            try:
                send_telegram_message(cust_msg, chat_id=str(sale.mijoz.telegram_chat_id).strip())
            except Exception as ex:
                logger.error(f"Failed to send sale notification to customer: {ex}")

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
        x_ism = write_off.yaratgan_xodim.ism if getattr(write_off, 'yaratgan_xodim', None) else "Noma'lum"
        x_fam = write_off.yaratgan_xodim.familiya if getattr(write_off, 'yaratgan_xodim', None) and write_off.yaratgan_xodim.familiya else ""
        xodim = clean_name(f"{x_ism} {x_fam}".strip()) if getattr(write_off, 'yaratgan_xodim', None) else "Noma'lum"
        biznes = getattr(write_off, 'biznes', None) or (write_off.dokon.biznes if getattr(write_off, 'dokon', None) else None)
        msg = (
            f"<b>⚠️ Hisobdan Chiqarish #{write_off.id}:</b>\n"
            f"👤 Xodim: {xodim}\n"
            f"📝 Sabab: {write_off.sababi}\n"
            f"💰 Jami Summa: <code>{write_off.sotish_summasi:,.2f}</code> so'm\n"
        )
        send_business_telegram_notification(biznes, msg, allowed_roles=['admin'])
    except Exception as e:
        logger.error(f"Failed to build write_off notification: {e}")


def notify_import(import_obj):
    try:
        x_ism = import_obj.yaratgan_xodim.ism if import_obj.yaratgan_xodim else "Noma'lum"
        x_fam = import_obj.yaratgan_xodim.familiya if import_obj.yaratgan_xodim and import_obj.yaratgan_xodim.familiya else ""
        xodim = clean_name(f"{x_ism} {x_fam}".strip()) if import_obj.yaratgan_xodim else "Noma'lum"
        dokon = import_obj.dokon.nomi if import_obj.dokon else "Noma'lum"
        taminotchi = import_obj.taminotchi.nomi if import_obj.taminotchi else "Noma'lum"
        
        items_lines = []
        elementlar = import_obj.elementlar or []
        for i, item in enumerate(elementlar[:10], 1):
            nomi = item.get('nomi') or item.get('mahsulot_nomi') or "Mahsulot"
            qty = item.get('miqdori') or item.get('quantity') or 0
            price = item.get('kelish_narxi') or item.get('price') or 0
            try:
                price_val = float(price)
            except Exception:
                price_val = 0.0
            items_lines.append(f"   {i}. {nomi} - <code>{qty}</code> dona x <code>{price_val:,.0f}</code> so'm")
        if len(elementlar) > 10:
            items_lines.append(f"   ... va yana {len(elementlar) - 10} ta mahsulot")
        items_text = "\n".join(items_lines) if items_lines else "Mahsulotlar mavjud emas"

        turi_disp = import_obj.get_import_turi_display() if hasattr(import_obj, 'get_import_turi_display') else import_obj.import_turi
        tolov_disp = import_obj.get_tolov_turi_display() if hasattr(import_obj, 'get_tolov_turi_display') else import_obj.tolov_turi

        msg = (
            f"<b>📥 YANGI KIRIM ({turi_disp.upper()}) #{import_obj.id}</b>\n"
            f"🏪 <b>Do'kon:</b> {dokon}\n"
            f"👤 <b>Xodim:</b> {xodim}\n"
            f"🤝 <b>Yetkazib beruvchi:</b> {taminotchi}\n"
            f"💵 <b>To'lov turi:</b> {tolov_disp}\n"
            f"\n📦 <b>Mahsulotlar:</b>\n{items_text}\n\n"
            f"💰 <b>Jami kelish summasi:</b> <code>{import_obj.kelish_summasi:,.0f}</code> so'm\n"
        )
        send_business_telegram_notification(import_obj.biznes, msg)
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


def get_main_keyboard(xodim=None):
    buttons = [
        [{"text": "📊 Bugungi hisobot"}, {"text": "🛒 So'nggi sotuvlar"}],
        [{"text": "⚠️ Hisobdan chiqarishlar"}, {"text": "📦 Kam qolgan mahsulotlar"}],
        [{"text": "⚙️ Sozlamalar"}]
    ]
    if xodim and xodim.rol == 'admin':
        buttons.insert(2, [{"text": "📢 Xabar yuborish"}])
    return {
        "keyboard": buttons,
        "resize_keyboard": True
    }


def get_broadcast_keyboard():
    return {
        "keyboard": [
            [{"text": "👥 Qarz eslatmasi (Barchaga)"}],
            [{"text": "👤 Qarz eslatmasi (Tanlangan mijozga)"}],
            [{"text": "📝 Oddiy reklama yuborish"}],
            [{"text": "🔙 Asosiy menyu"}]
        ],
        "resize_keyboard": True
    }


def get_confirm_keyboard():
    return {
        "keyboard": [
            [{"text": "✅ Tasdiqlash"}, {"text": "❌ Bekor qilish"}]
        ],
        "resize_keyboard": True
    }


def get_ad_recipient_keyboard():
    return {
        "keyboard": [
            [{"text": "👥 Barcha mijozlarga"}, {"text": "👥 Faqat qarzdorlarga"}],
            [{"text": "❌ Bekor qilish"}]
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
        x_ism = clean_name(s.xodim.ism) if s.xodim else "Noma'lum"
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
                f"👋 Salom, <b>{clean_name(xodim.ism + ' ' + (xodim.familiya or ''))}</b>!\n"
                f"🏢 Biznes: <b>{b_nomi}</b>\n\n"
                f"Tizimga ulangan ekansiz. Kerakli bo'limni tanlang:"
            )
            send_telegram_message(msg, chat_id=chat_id, reply_markup=get_main_keyboard(xodim))
        elif session.state == 'AUTHENTICATED_MIJOZ' and session.mijoz:
            from django.db.models import Sum
            from user.models import MijozQarzi
            from decimal import Decimal
            mijoz = session.mijoz
            qarz = MijozQarzi.objects.filter(mijoz=mijoz).exclude(holat='tolangan').aggregate(total=Sum('qoldiq_summa'))['total'] or Decimal('0.00')
            b_nomi = mijoz.biznes.nomi if mijoz.biznes else 'Mavjud emas'
            
            if qarz > 0:
                msg = (
                    f"👋 Salom, hurmatli <b>{mijoz.ism} {mijoz.familiya or ''}</b>!\n"
                    f"🏢 Do'kon: <b>{b_nomi}</b>\n\n"
                    f"💳 <b>Hisob holati:</b> Joriy qarz qoldig'ingiz <code>{qarz:,.0f}</code> so'm.\n\n"
                    f"🔔 Botimiz orqali har dushanba kuni hisobingiz holati haqida ma'lumot berib boriladi. Bizni tanlaganingiz uchun tashakkur!"
                )
            else:
                msg = (
                    f"👋 Salom, hurmatli <b>{mijoz.ism} {mijoz.familiya or ''}</b>!\n"
                    f"🏢 Do'kon: <b>{b_nomi}</b>\n\n"
                    f"🎉 <b>Sizning qarz qoldig'ingiz yo'q!</b> Do'konimizdan xarid qilganingiz uchun tashakkur! 😊"
                )
            send_telegram_message(msg, chat_id=chat_id)
        else:
            session.state = 'AWAITING_PHONE'
            session.xodim = None
            session.mijoz = None
            session.save()
            msg = (
                "👋 Assalomu alaykum! <b>TemirDo'kon</b> botiga xush kelibsiz.\n\n"
                "Tizimdan foydalanish uchun 📱 <b>Telefon raqamingizni yuboring</b>."
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

        if found_xodim:
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

        # Match Mijoz by normalized phone
        from user.models import Mijoz
        all_mijozlar = Mijoz.objects.all()
        found_mijoz = None
        for m in all_mijozlar:
            if m.telefon_raqam_1 and normalize_phone(m.telefon_raqam_1) == norm_phone:
                found_mijoz = m
                break
            if m.telefon_raqam_2 and normalize_phone(m.telefon_raqam_2) == norm_phone:
                found_mijoz = m
                break

        if found_mijoz:
            found_mijoz.telegram_chat_id = str(chat_id)
            found_mijoz.save()

            session.mijoz = found_mijoz
            session.state = 'AUTHENTICATED_MIJOZ'
            session.save()

            from django.db.models import Sum
            from user.models import MijozQarzi
            from decimal import Decimal
            qarz = MijozQarzi.objects.filter(mijoz=found_mijoz).exclude(holat='tolangan').aggregate(total=Sum('qoldiq_summa'))['total'] or Decimal('0.00')
            b_nomi = found_mijoz.biznes.nomi if found_mijoz.biznes else 'Mavjud emas'
            if qarz > 0:
                msg = (
                    f"✅ <b>Muvaffaqiyatli tizimga ulandingiz!</b>\n\n"
                    f"👤 Mijoz: <b>{found_mijoz.ism} {found_mijoz.familiya or ''}</b>\n"
                    f"🏢 Do'kon: <b>{b_nomi}</b>\n\n"
                    f"💳 <b>Hisob holati:</b> Joriy qarz qoldig'ingiz <code>{qarz:,.0f}</code> so'm.\n\n"
                    f"🔔 Botimiz orqali har dushanba kuni hisobingiz holati haqida ma'lumot berib boriladi."
                )
            else:
                msg = (
                    f"✅ <b>Muvaffaqiyatli tizimga ulandingiz!</b>\n\n"
                    f"👤 Mijoz: <b>{found_mijoz.ism} {found_mijoz.familiya or ''}</b>\n"
                    f"🏢 Do'kon: <b>{b_nomi}</b>\n\n"
                    f"🎉 <b>Qarz qoldig'ingiz yo'q!</b> Do'konimizdan xarid qilganingiz uchun tashakkur! 😊"
                )
            send_telegram_message(msg, chat_id=chat_id, reply_markup={"remove_keyboard": True})
            return True

        msg = (
            f"❌ Telefon raqam (<code>{phone_raw}</code>) bo'yicha tizimda foydalanuvchi yoki mijoz topilmadi.\n\n"
            "Iltimos, tizimda ro'yxatdan o'tgan telefon raqamingizni yuboring."
        )
        send_telegram_message(msg, chat_id=chat_id, reply_markup=get_phone_keyboard())
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
                f"👤 Xodim: <b>{clean_name(xodim.ism + ' ' + (xodim.familiya or ''))}</b>\n"
                f"🏢 Biznes: <b>{b_nomi}</b>\n\n"
                f"🔔 Endi ushbu biznesga oid sotuvlar va bildirishnomalar ushbu chatga yuboriladi."
            )
            send_telegram_message(msg, chat_id=chat_id, reply_markup=get_main_keyboard(xodim))
        else:
            send_telegram_message("❌ <b>Parol noto'g'ri.</b> Qayta kiriting:", chat_id=chat_id)
        return True

    # State: AWAITING_BROADCAST_TYPE
    if session.state == 'AWAITING_BROADCAST_TYPE' and session.xodim and session.xodim.rol == 'admin':
        if text == "🔙 Asosiy menyu":
            session.state = 'AUTHENTICATED'
            session.save()
            send_telegram_message("📱 Asosiy menyu:", chat_id=chat_id, reply_markup=get_main_keyboard(session.xodim))
            return True
        elif text == "👥 Qarz eslatmasi (Barchaga)":
            session.state = 'AWAITING_CONFIRM_ALL_DEBTORS'
            session.save()
            send_telegram_message("❓ Haqiqatan ham barcha qarzi bor mijozlarga Telegram orqali eslatma yuborilsinmi?", chat_id=chat_id, reply_markup=get_confirm_keyboard())
            return True
        elif text == "👤 Qarz eslatmasi (Tanlangan mijozga)":
            from user.models import Mijoz
            mijozlar = Mijoz.objects.filter(biznes=session.xodim.biznes).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
            debtors = []
            for m in mijozlar:
                qarz = get_customer_total_debt(m)
                if qarz > 0:
                    debtors.append(m)
            
            if not debtors:
                send_telegram_message("ℹ️ Telegramga ulangan qarzdor mijozlar mavjud emas.", chat_id=chat_id, reply_markup=get_broadcast_keyboard())
                return True
            
            keyboard_buttons = []
            for d in debtors[:15]:
                q = get_customer_total_debt(d)
                keyboard_buttons.append([{"text": f"Mijoz: {d.ism} ({q:,.0f} UZS)"}])
            keyboard_buttons.append([{"text": "❌ Bekor qilish"}])
            
            session.state = 'AWAITING_DEBTOR_SELECTION'
            session.save()
            send_telegram_message("👤 Eslatma yubormoqchi bo'lgan mijozingizni tanlang:", chat_id=chat_id, reply_markup={"keyboard": keyboard_buttons, "resize_keyboard": True})
            return True
        elif text == "📝 Oddiy reklama yuborish":
            session.state = 'AWAITING_AD_TEXT'
            session.save()
            send_telegram_message("📝 Reklama matnini kiriting:", chat_id=chat_id, reply_markup={"keyboard": [[{"text": "❌ Bekor qilish"}]], "resize_keyboard": True})
            return True

    # State: AWAITING_CONFIRM_ALL_DEBTORS
    if session.state == 'AWAITING_CONFIRM_ALL_DEBTORS' and session.xodim and session.xodim.rol == 'admin':
        if text == "✅ Tasdiqlash":
            from user.models import MijozQarzi
            from django.db.models import Sum
            from decimal import Decimal
            
            unpaid_debts = MijozQarzi.objects.exclude(holat='tolangan').filter(
                mijoz__biznes=session.xodim.biznes,
                mijoz__telegram_chat_id__isnull=False
            ).exclude(mijoz__telegram_chat_id="")
            
            customers_debts = {}
            for dq in unpaid_debts:
                mijoz = dq.mijoz
                if mijoz.telegram_notifications_enabled:
                    customers_debts[mijoz] = customers_debts.get(mijoz, Decimal('0.00')) + dq.qoldiq_summa
            
            sent_count = 0
            b_nomi = session.xodim.biznes.nomi if session.xodim.biznes else "Do'kon"
            for mijoz, total_qarz in customers_debts.items():
                if total_qarz > 0:
                    msg = (
                        f"Assalomu alaykum, <b>{mijoz.ism} {mijoz.familiya or ''}</b>!\n\n"
                        f"⚠️ Sizning <b>{b_nomi}</b> do'konimizdan <code>{total_qarz:,.0f}</code> so'm qarz qoldig'ingiz bor.\n"
                        f"Iltimos, o'z vaqtida to'lov qilishni unutmang. Rahmat!"
                    )
                    try:
                        send_telegram_message(msg, chat_id=str(mijoz.telegram_chat_id).strip())
                        sent_count += 1
                    except Exception:
                        pass
            
            session.state = 'AUTHENTICATED'
            session.save()
            send_telegram_message(f"✅ Barcha qarzdorlarga eslatma yuborildi. Muvaffaqiyatli jo'natildi: {sent_count} ta.", chat_id=chat_id, reply_markup=get_main_keyboard(session.xodim))
            return True
        else:
            session.state = 'AWAITING_BROADCAST_TYPE'
            session.save()
            send_telegram_message("❌ Bekor qilindi.", chat_id=chat_id, reply_markup=get_broadcast_keyboard())
            return True

    # State: AWAITING_DEBTOR_SELECTION
    if session.state == 'AWAITING_DEBTOR_SELECTION' and session.xodim and session.xodim.rol == 'admin':
        if text == "❌ Bekor qilish" or text.startswith("❌"):
            session.state = 'AWAITING_BROADCAST_TYPE'
            session.save()
            send_telegram_message("❌ Bekor qilindi.", chat_id=chat_id, reply_markup=get_broadcast_keyboard())
            return True
        
        if text.startswith("Mijoz:"):
            try:
                name_part = text.split("Mijoz:")[1].split("(")[0].strip()
                from user.models import Mijoz
                mijoz = Mijoz.objects.filter(biznes=session.xodim.biznes, ism=name_part).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="").first()
                if mijoz:
                    q = get_customer_total_debt(mijoz)
                    b_nomi = session.xodim.biznes.nomi if session.xodim.biznes else "Do'kon"
                    msg = (
                        f"Assalomu alaykum, <b>{mijoz.ism} {mijoz.familiya or ''}</b>!\n\n"
                        f"⚠️ Sizning <b>{b_nomi}</b> do'konimizdan <code>{q:,.0f}</code> so'm qarz qoldig'ingiz bor.\n"
                        f"Iltimos, o'z vaqtida to'lov qilishni unutmang. Rahmat!"
                    )
                    try:
                        send_telegram_message(msg, chat_id=str(mijoz.telegram_chat_id).strip())
                        send_telegram_message(f"✅ Mijoz {mijoz.ism}ga eslatma yuborildi.", chat_id=chat_id, reply_markup=get_main_keyboard(session.xodim))
                    except Exception as ex:
                        send_telegram_message(f"❌ Xabarni yuborishda xatolik yuz berdi: {ex}", chat_id=chat_id, reply_markup=get_main_keyboard(session.xodim))
                    
                    session.state = 'AUTHENTICATED'
                    session.save()
                    return True
            except Exception:
                pass
        
        send_telegram_message("❌ Noto'g'ri tanlov. Qaytadan tanlang:", chat_id=chat_id)
        return True

    # State: AWAITING_AD_TEXT
    if session.state == 'AWAITING_AD_TEXT' and session.xodim and session.xodim.rol == 'admin':
        if text == "❌ Bekor qilish":
            session.state = 'AWAITING_BROADCAST_TYPE'
            session.save()
            send_telegram_message("❌ Bekor qilindi.", chat_id=chat_id, reply_markup=get_broadcast_keyboard())
            return True
        
        if not text:
            send_telegram_message("❌ Iltimos, reklama matnini matn ko'rinishida yuboring:", chat_id=chat_id)
            return True
        
        session.temp_phone = text
        session.state = 'AWAITING_AD_RECIPIENT_TYPE'
        session.save()
        send_telegram_message("👥 Reklamani kimlarga yubormoqchisiz?", chat_id=chat_id, reply_markup=get_ad_recipient_keyboard())
        return True

    # State: AWAITING_AD_RECIPIENT_TYPE
    if session.state == 'AWAITING_AD_RECIPIENT_TYPE' and session.xodim and session.xodim.rol == 'admin':
        if text == "❌ Bekor qilish":
            session.state = 'AWAITING_BROADCAST_TYPE'
            session.save()
            send_telegram_message("❌ Bekor qilindi.", chat_id=chat_id, reply_markup=get_broadcast_keyboard())
            return True
        
        ad_text = session.temp_phone
        from user.models import Mijoz
        
        if text == "👥 Barcha mijozlarga":
            mijozlar = Mijoz.objects.filter(biznes=session.xodim.biznes).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
        elif text == "👥 Faqat qarzdorlarga":
            all_mijozlar = Mijoz.objects.filter(biznes=session.xodim.biznes).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
            mijozlar = []
            for m in all_mijozlar:
                if get_customer_total_debt(m) > 0:
                    mijozlar.append(m)
        else:
            send_telegram_message("❌ Noto'g'ri tanlov. Qaytadan tanlang:", chat_id=chat_id)
            return True
            
        if not mijozlar:
            send_telegram_message("ℹ️ Ko'rsatilgan guruhda Telegramga ulangan mijozlar topilmadi.", chat_id=chat_id, reply_markup=get_broadcast_keyboard())
            session.state = 'AWAITING_BROADCAST_TYPE'
            session.save()
            return True
            
        sent_count = 0
        for m in mijozlar:
            try:
                send_telegram_message(ad_text, chat_id=str(m.telegram_chat_id).strip())
                sent_count += 1
            except Exception:
                pass
                
        session.state = 'AUTHENTICATED'
        session.save()
        send_telegram_message(f"✅ Reklama yuborildi. Muvaffaqiyatli jo'natildi: {sent_count} ta.", chat_id=chat_id, reply_markup=get_main_keyboard(session.xodim))
        return True

    # State: AUTHENTICATED commands
    if session.state == 'AUTHENTICATED' and session.xodim:
        xodim = session.xodim
        biznes = xodim.biznes

        if text == "📊 Bugungi hisobot":
            res = get_today_summary_for_biznes(biznes)
            send_telegram_message(res, chat_id=chat_id, reply_markup=get_main_keyboard(xodim))
        elif text == "🛒 So'nggi sotuvlar":
            res = get_recent_sales_for_biznes(biznes)
            send_telegram_message(res, chat_id=chat_id, reply_markup=get_main_keyboard(xodim))
        elif text == "⚠️ Hisobdan chiqarishlar":
            res = get_recent_write_offs_for_biznes(biznes)
            send_telegram_message(res, chat_id=chat_id, reply_markup=get_main_keyboard(xodim))
        elif text == "📦 Kam qolgan mahsulotlar":
            res = get_low_stock_for_biznes(biznes)
            send_telegram_message(res, chat_id=chat_id, reply_markup=get_main_keyboard(xodim))
        elif text == "⚙️ Sozlamalar":
            msg = (
                f"<b>⚙️ SOZLAMALAR</b>\n\n"
                f"👤 Xodim: {clean_name(xodim.ism + ' ' + (xodim.familiya or ''))}\n"
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
            send_telegram_message("📱 Asosiy menyu:", chat_id=chat_id, reply_markup=get_main_keyboard(xodim))
        elif text == "📢 Xabar yuborish" and xodim.rol == 'admin':
            session.state = 'AWAITING_BROADCAST_TYPE'
            session.save()
            send_telegram_message("📢 Xabar yuborish bo'limi. Kerakli turni tanlang:", chat_id=chat_id, reply_markup=get_broadcast_keyboard())
        else:
            send_telegram_message("ℹ️ Kerakli bo'limni pastdagi tugmalar orqali tanlang:", chat_id=chat_id, reply_markup=get_main_keyboard(xodim))
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


def send_weekly_debt_reminders():
    """
    Sends automated debt reminders to all customers having positive debt balance
    and a registered Telegram chat ID.
    """
    try:
        from user.models import MijozQarzi
        from django.db.models import Sum
        from decimal import Decimal

        unpaid_debts = MijozQarzi.objects.exclude(holat='tolangan').filter(
            mijoz__telegram_chat_id__isnull=False
        ).exclude(mijoz__telegram_chat_id="")

        customers_debts = {}
        for dq in unpaid_debts:
            mijoz = dq.mijoz
            if mijoz.telegram_notifications_enabled:
                customers_debts[mijoz] = customers_debts.get(mijoz, Decimal('0.00')) + dq.qoldiq_summa

        for mijoz, total_qarz in customers_debts.items():
            if total_qarz > 0:
                b_nomi = mijoz.biznes.nomi if mijoz.biznes else "Do'kon"
                msg = (
                    f"Assalomu alaykum, <b>{mijoz.ism} {mijoz.familiya or ''}</b>!\n\n"
                    f"⚠️ Sizning <b>{b_nomi}</b> do'konimizdan <code>{total_qarz:,.0f}</code> so'm qarz qoldig'ingiz bor.\n"
                    f"Iltimos, o'z vaqtida to'lov qilishni unutmang. Rahmat!"
                )
                try:
                    send_telegram_message(msg, chat_id=str(mijoz.telegram_chat_id).strip())
                except Exception as ex:
                    logger.error(f"Failed to send weekly debt reminder to customer {mijoz.id}: {ex}")
    except Exception as e:
        logger.error(f"Failed to process weekly debt reminders: {e}")
