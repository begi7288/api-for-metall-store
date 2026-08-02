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
        from sales.models import Sale
        from decimal import Decimal
        from django.utils import timezone

        xodim_ism = f"{sale.xodim.ism} {sale.xodim.familiya}".strip() if sale.xodim else "Noma'lum"
        dokon_nomi = sale.dokon.nomi if sale.dokon else "Noma'lum"
        mijoz_nomi = f"{sale.mijoz.ism} {sale.mijoz.familiya}".strip() if sale.mijoz else "Anonim Mijoz"
        vaqt_str = sale.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M") if sale.yaratilgan_vaqt else ""

        # Calculate daily sale sequence number
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

        # Payment methods breakdown
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

        send_telegram_message("\n".join(msg_parts))
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


def send_daily_report(target_date=None):
    """
    Sends a comprehensive daily summary report to Telegram matching the requested template.
    If target_date is None, defaults to yesterday's date.
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        from decimal import Decimal
        from django.db import models
        from sales.models import Sale, SaleItem
        from products.models import Dokon, WriteOff
        from orders.models import SupplierOrderPayment
        from user.models import Mijoz, MijozQarzi, MijozTolovi, Xodim

        if not target_date:
            target_date = timezone.now().date() - timedelta(days=1)

        prev_date = target_date - timedelta(days=1)
        date_str = target_date.strftime("%Y-%m-%d")

        dokonlar = Dokon.objects.all()

        def fmt_val_pct(curr, prev, unit="UZS"):
            if unit == "UZS":
                curr_str = f"{curr:,.0f} UZS"
            else:
                curr_str = f"{curr} {unit}"
            if not prev or prev == 0:
                pct_str = "0%"
            else:
                pct = round(float((curr - prev) / prev * 100), 1)
                pct_str = f"{'+' if pct > 0 else ''}{pct}%"
            return f"{curr_str} ({pct_str})"

        sales_today = Sale.objects.filter(yaratilgan_vaqt__date=target_date, holat='yakunlangan')
        sales_prev = Sale.objects.filter(yaratilgan_vaqt__date=prev_date, holat='yakunlangan')

        # 1. Tushum
        jami_tushum_today = sales_today.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
        jami_tushum_prev = sales_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')

        # 2. Xarajatlar
        sp_exp_today = SupplierOrderPayment.objects.filter(yaratilgan_vaqt__date=target_date).aggregate(t=models.Sum('tolangan_summa'))['t'] or Decimal('0.00')
        wo_exp_today = WriteOff.objects.filter(holat='yakunlangan', yaratilgan_vaqt__date=target_date).aggregate(t=models.Sum('kelish_summasi'))['t'] or Decimal('0.00')
        xarajat_today = sp_exp_today + wo_exp_today

        sp_exp_prev = SupplierOrderPayment.objects.filter(yaratilgan_vaqt__date=prev_date).aggregate(t=models.Sum('tolangan_summa'))['t'] or Decimal('0.00')
        wo_exp_prev = WriteOff.objects.filter(holat='yakunlangan', yaratilgan_vaqt__date=prev_date).aggregate(t=models.Sum('kelish_summasi'))['t'] or Decimal('0.00')
        xarajat_prev = sp_exp_prev + wo_exp_prev

        # 3. Sof tushum
        sof_tushum_today = max(Decimal('0.00'), jami_tushum_today - xarajat_today)
        sof_tushum_prev = max(Decimal('0.00'), jami_tushum_prev - xarajat_prev)

        # 4. Sof foyda
        items_today = SaleItem.objects.filter(sotuv__in=sales_today)
        cost_today = sum((item.kelish_narxi * Decimal(item.miqdori)) for item in items_today)
        chegirma_today = sales_today.aggregate(t=models.Sum('chegirma_summasi'))['t'] or Decimal('0.00')
        sof_foyda_today = max(Decimal('0.00'), (jami_tushum_today - cost_today - xarajat_today))

        items_prev = SaleItem.objects.filter(sotuv__in=sales_prev)
        cost_prev = sum((item.kelish_narxi * Decimal(item.miqdori)) for item in items_prev)
        sof_foyda_prev = max(Decimal('0.00'), (jami_tushum_prev - cost_prev - xarajat_prev))

        # 5. Sotilgan mahsulotlar
        sotilgan_soni_today = items_today.aggregate(t=models.Sum('miqdori'))['t'] or 0
        sotilgan_soni_prev = items_prev.aggregate(t=models.Sum('miqdori'))['t'] or 0

        # 6. Mijozlar
        mijozlar_today = sales_today.filter(mijoz__isnull=False).values_list('mijoz_id', flat=True).distinct()
        jami_mijozlar_today = len(mijozlar_today)
        
        mijozlar_prev = sales_prev.filter(mijoz__isnull=False).values_list('mijoz_id', flat=True).distinct()
        jami_mijozlar_prev = len(mijozlar_prev)

        yangi_mijozlar_cnt = 0
        qayta_mijozlar_cnt = 0
        for m_id in mijozlar_today:
            prev_sales_exist = Sale.objects.filter(mijoz_id=m_id, yaratilgan_vaqt__date__lt=target_date).exists()
            if prev_sales_exist:
                qayta_mijozlar_cnt += 1
            else:
                yangi_mijozlar_cnt += 1

        # 7. Asosiy ko'rsatkichlar
        cheklar_cnt_today = sales_today.count()
        cheklar_cnt_prev = sales_prev.count()

        ortacha_chek_today = (jami_tushum_today / cheklar_cnt_today) if cheklar_cnt_today > 0 else Decimal('0.00')
        ortacha_chek_prev = (jami_tushum_prev / cheklar_cnt_prev) if cheklar_cnt_prev > 0 else Decimal('0.00')

        ortacha_tovar_chek_today = round(sotilgan_soni_today / cheklar_cnt_today, 1) if cheklar_cnt_today > 0 else 0.0
        ortacha_tovar_chek_prev = round(sotilgan_soni_prev / cheklar_cnt_prev, 1) if cheklar_cnt_prev > 0 else 0.0

        ortacha_tovar_narxi_today = (jami_tushum_today / sotilgan_soni_today) if sotilgan_soni_today > 0 else Decimal('0.00')
        ortacha_tovar_narxi_prev = (jami_tushum_prev / sotilgan_soni_prev) if sotilgan_soni_prev > 0 else Decimal('0.00')

        lines = [
            f"<b>{date_str} sanasi uchun kunlik hisobot</b>\n",
            "<b>Sotuvlar</b>",
            "<b>Tushum (Savdo summasi)</b>",
            f"Jami: {fmt_val_pct(jami_tushum_today, jami_tushum_prev)}",
        ]
        for d in dokonlar:
            d_sales = sales_today.filter(dokon=d)
            d_prev = sales_prev.filter(dokon=d)
            d_tushum = d_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            d_prev_tushum = d_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            lines.append(f"Do'kon {d.nomi}: {fmt_val_pct(d_tushum, d_prev_tushum)}")

        lines.extend([
            "\n<b>Sof tushum</b>",
            f"Jami: {fmt_val_pct(sof_tushum_today, sof_tushum_prev)}",
        ])
        for d in dokonlar:
            d_sales = sales_today.filter(dokon=d)
            d_prev = sales_prev.filter(dokon=d)
            d_tushum = d_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            d_prev_tushum = d_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            lines.append(f"Do'kon {d.nomi}: {fmt_val_pct(d_tushum, d_prev_tushum)}")

        lines.extend([
            "\n<b>Sof foyda</b>",
            f"Jami: {fmt_val_pct(sof_foyda_today, sof_foyda_prev)}",
        ])
        for d in dokonlar:
            d_sales = sales_today.filter(dokon=d)
            d_prev = sales_prev.filter(dokon=d)
            d_items = SaleItem.objects.filter(sotuv__in=d_sales)
            d_tushum = d_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            d_cost = sum((item.kelish_narxi * Decimal(item.miqdori)) for item in d_items)
            d_foyda = max(Decimal('0.00'), d_tushum - d_cost)

            d_items_prev = SaleItem.objects.filter(sotuv__in=d_prev)
            d_tushum_prev = d_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            d_cost_prev = sum((item.kelish_narxi * Decimal(item.miqdori)) for item in d_items_prev)
            d_foyda_prev = max(Decimal('0.00'), d_tushum_prev - d_cost_prev)
            lines.append(f"Do'kon {d.nomi}: {fmt_val_pct(d_foyda, d_foyda_prev)}")

        lines.extend([
            "\n<b>Sotilgan mahsulotlar soni</b>",
            f"Jami: {fmt_val_pct(sotilgan_soni_today, sotilgan_soni_prev, 'dona')}",
        ])
        for d in dokonlar:
            d_sales = sales_today.filter(dokon=d)
            d_prev = sales_prev.filter(dokon=d)
            d_soni = SaleItem.objects.filter(sotuv__in=d_sales).aggregate(t=models.Sum('miqdori'))['t'] or 0
            d_prev_soni = SaleItem.objects.filter(sotuv__in=d_prev).aggregate(t=models.Sum('miqdori'))['t'] or 0
            lines.append(f"Do'kon {d.nomi}: {fmt_val_pct(d_soni, d_prev_soni, 'dona')}")

        lines.extend([
            "\n<b>Qaytarilgan mahsulotlar soni</b>",
            "Jami: 0 dona (0%)",
        ])
        for d in dokonlar:
            lines.append(f"Do'kon {d.nomi}: 0 dona (0%)")

        lines.extend([
            "\n<b>Mijozlar</b>",
            f"Jami: {fmt_val_pct(jami_mijozlar_today, jami_mijozlar_prev, 'ta')}",
            f"Yangi mijozlar: {yangi_mijozlar_cnt} ta (0%)",
            f"Qayta xarid qilgan mijozlar: {qayta_mijozlar_cnt} ta (0%)",
            "\n<b>Brendning asosiy ko'rsatkichlari</b>",
            "<b>O'rtacha chek summasi</b>",
            f"Jami: {fmt_val_pct(ortacha_chek_today, ortacha_chek_prev)}",
        ])
        for d in dokonlar:
            d_sales = sales_today.filter(dokon=d)
            d_prev = sales_prev.filter(dokon=d)
            d_cnt = d_sales.count()
            d_cnt_prev = d_prev.count()
            d_tushum = d_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            d_tushum_prev = d_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            d_avg = (d_tushum / d_cnt) if d_cnt > 0 else Decimal('0.00')
            d_avg_prev = (d_tushum_prev / d_cnt_prev) if d_cnt_prev > 0 else Decimal('0.00')
            lines.append(f"Do'kon {d.nomi}: {fmt_val_pct(d_avg, d_avg_prev)}")

        lines.extend([
            "\n<b>Bitta chekdagi o'rtacha mahsulotlar soni</b>",
            f"Jami: {fmt_val_pct(ortacha_tovar_chek_today, ortacha_tovar_chek_prev, 'dona')}",
        ])
        for d in dokonlar:
            d_sales = sales_today.filter(dokon=d)
            d_prev = sales_prev.filter(dokon=d)
            d_cnt = d_sales.count()
            d_cnt_prev = d_prev.count()
            d_soni = SaleItem.objects.filter(sotuv__in=d_sales).aggregate(t=models.Sum('miqdori'))['t'] or 0
            d_soni_prev = SaleItem.objects.filter(sotuv__in=d_prev).aggregate(t=models.Sum('miqdori'))['t'] or 0
            d_avg = round(d_soni / d_cnt, 1) if d_cnt > 0 else 0.0
            d_avg_prev = round(d_soni_prev / d_cnt_prev, 1) if d_cnt_prev > 0 else 0.0
            lines.append(f"Do'kon {d.nomi}: {fmt_val_pct(d_avg, d_avg_prev, 'dona')}")

        lines.extend([
            "\n<b>Chekdagi mahsulotlarning o'rtacha qiymati</b>",
            f"Jami: {fmt_val_pct(ortacha_tovar_narxi_today, ortacha_tovar_narxi_prev)}",
        ])
        for d in dokonlar:
            d_sales = sales_today.filter(dokon=d)
            d_prev = sales_prev.filter(dokon=d)
            d_soni = SaleItem.objects.filter(sotuv__in=d_sales).aggregate(t=models.Sum('miqdori'))['t'] or 0
            d_soni_prev = SaleItem.objects.filter(sotuv__in=d_prev).aggregate(t=models.Sum('miqdori'))['t'] or 0
            d_tushum = d_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            d_tushum_prev = d_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            d_avg = (d_tushum / d_soni) if d_soni > 0 else Decimal('0.00')
            d_avg_prev = (d_tushum_prev / d_soni_prev) if d_soni_prev > 0 else Decimal('0.00')
            lines.append(f"Do'kon {d.nomi}: {fmt_val_pct(d_avg, d_avg_prev)}")

        lines.extend([
            "\n<b>Sotuvchilar</b>",
            "<b>Sotuvchilar bo'yicha sof tushum</b>",
            f"Jami: {fmt_val_pct(jami_tushum_today, jami_tushum_prev)}",
        ])
        xodimlar = Xodim.objects.all()
        for x in xodimlar:
            x_sales = sales_today.filter(xodim=x)
            x_prev = sales_prev.filter(xodim=x)
            x_tushum = x_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            x_prev_tushum = x_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            if x_tushum > 0 or x_prev_tushum > 0:
                lines.append(f"{x.ism} {x.familiya or ''}: {fmt_val_pct(x_tushum, x_prev_tushum)}")

        lines.extend([
            "\n<b>Sotuvchilar bo'yicha o'rtacha chek summasi</b>",
            f"Jami: {fmt_val_pct(ortacha_chek_today, ortacha_chek_prev)}",
        ])
        for x in xodimlar:
            x_sales = sales_today.filter(xodim=x)
            x_prev = sales_prev.filter(xodim=x)
            x_cnt = x_sales.count()
            x_cnt_prev = x_prev.count()
            x_tushum = x_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            x_prev_tushum = x_prev.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            x_avg = (x_tushum / x_cnt) if x_cnt > 0 else Decimal('0.00')
            x_avg_prev = (x_prev_tushum / x_cnt_prev) if x_cnt_prev > 0 else Decimal('0.00')
            if x_cnt > 0 or x_cnt_prev > 0:
                lines.append(f"{x.ism} {x.familiya or ''}: {fmt_val_pct(x_avg, x_avg_prev)}")

        qarzlar_today = MijozQarzi.objects.filter(yaratilgan_vaqt__date=target_date)
        qarz_soni = qarzlar_today.count()

        qaytarilgan_qarz_summa = MijozTolovi.objects.filter(yaratilgan_vaqt__date=target_date).aggregate(t=models.Sum('summa'))['t'] or Decimal('0.00')
        qarz_qoldiq_summa = MijozQarzi.objects.filter(qoldiq_summa__gt=0).aggregate(t=models.Sum('qoldiq_summa'))['t'] or Decimal('0.00')
        qarzdorlar_soni = MijozQarzi.objects.filter(qoldiq_summa__gt=0).values('mijoz').distinct().count()

        qisman_cnt = MijozQarzi.objects.filter(yaratilgan_vaqt__date=target_date, holat='qisman_tolangan').count()
        toliq_cnt = MijozQarzi.objects.filter(yaratilgan_vaqt__date=target_date, holat='tolangan').count()
        tolanmagan_cnt = MijozQarzi.objects.filter(yaratilgan_vaqt__date=target_date, holat='tolanmagan').count()

        lines.extend([
            "\n<b>Qarzlar</b>",
            f"Berilgan qarzlar soni: {qarz_soni} ta",
            f"Qaytarilgan qarz summasi: {qaytarilgan_qarz_summa:,.0f} UZS",
            f"Jami qarzdorlik qoldig'i: {qarz_qoldiq_summa:,.0f} UZS",
            f"Jami qarzdorlar soni: {qarzdorlar_soni} ta",
            f"Qisman to'laganlar: {qisman_cnt} ta",
            f"To'liq to'laganlar: {toliq_cnt} ta",
            f"Umuman to'lamaganlar: {tolanmagan_cnt} ta",
        ])

        naqd_tushum = sales_today.filter(tolov_usuli='naqd').aggregate(t=models.Sum('tolangan_summa'))['t'] or Decimal('0.00')
        karta_tushum = sales_today.filter(tolov_usuli='karta').aggregate(t=models.Sum('tolangan_summa'))['t'] or Decimal('0.00')

        lines.extend([
            "\n<b>Qo'shimcha to'lov ko'rsatkichlari</b>",
            f"💵 Naqd to'lov: {naqd_tushum:,.0f} UZS",
            f"💳 Karta to'lov: {karta_tushum:,.0f} UZS",
            f"🏷 Chegirmalar summasi: {chegirma_today:,.0f} UZS",
            f"💸 Xarajatlar summasi: {xarajat_today:,.0f} UZS",
        ])

        full_message = "\n".join(lines)
        send_telegram_message(full_message)
    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")
