from django.test import TestCase, override_settings
from decimal import Decimal
from user.models import Biznes, Xodim, TelegramSession
from sales.models import Sale
from products.models import Dokon, Mahsulot, WriteOff, OlchovBirligi
from user.telegram_bot import (
    normalize_phone,
    verify_xodim_password,
    process_telegram_update,
    send_business_telegram_notification,
    notify_sale,
    notify_write_off
)


@override_settings(TEST_TELEGRAM_BOT_HTTP=False)
class TelegramBotTestCase(TestCase):
    def setUp(self):
        self.biznes1 = Biznes.objects.create(nomi="Do'kon A", egasi_ism="Ali")
        self.biznes2 = Biznes.objects.create(nomi="Do'kon B", egasi_ism="Vali")

        self.xodim1 = Xodim.objects.create(
            biznes=self.biznes1,
            ism="Ali",
            familiya="Valiyev",
            telefon_raqam="+998901234567",
            parol="secret123",
            jinsi="erkak"
        )
        self.xodim2 = Xodim.objects.create(
            biznes=self.biznes2,
            ism="Vali",
            familiya="Aliyev",
            telefon_raqam="+998907654321",
            parol="password456",
            jinsi="erkak"
        )

        self.dokon1 = Dokon.objects.create(biznes=self.biznes1, nomi="Asosiy Do'kon A")

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("+998 90 123 45 67"), "998901234567")
        self.assertEqual(normalize_phone("901234567"), "998901234567")
        self.assertEqual(normalize_phone(""), "")

    def test_verify_password(self):
        self.assertTrue(verify_xodim_password(self.xodim1, "secret123"))
        self.assertFalse(verify_xodim_password(self.xodim1, "wrongpass"))

    def test_bot_login_flow(self):
        chat_id = "111222333"

        # 1. /start
        update1 = {
            "update_id": 1,
            "message": {
                "chat": {"id": chat_id},
                "text": "/start"
            }
        }
        process_telegram_update(update1)
        session = TelegramSession.objects.get(chat_id=chat_id)
        self.assertEqual(session.state, 'AWAITING_PHONE')

        # 2. Share contact with matching phone number
        update2 = {
            "update_id": 2,
            "message": {
                "chat": {"id": chat_id},
                "contact": {"phone_number": "998901234567"}
            }
        }
        process_telegram_update(update2)
        session.refresh_from_db()
        self.assertEqual(session.state, 'AWAITING_PASSWORD')
        self.assertEqual(session.xodim, self.xodim1)

        # 3. Enter wrong password
        update3 = {
            "update_id": 3,
            "message": {
                "chat": {"id": chat_id},
                "text": "wrong_pass"
            }
        }
        process_telegram_update(update3)
        session.refresh_from_db()
        self.assertEqual(session.state, 'AWAITING_PASSWORD')

        # 4. Enter correct password
        update4 = {
            "update_id": 4,
            "message": {
                "chat": {"id": chat_id},
                "text": "secret123"
            }
        }
        process_telegram_update(update4)
        session.refresh_from_db()
        self.xodim1.refresh_from_db()

        self.assertEqual(session.state, 'AUTHENTICATED')
        self.assertEqual(self.xodim1.telegram_chat_id, chat_id)
        self.assertTrue(self.xodim1.telegram_notifications_enabled)

    def test_bot_authenticated_commands(self):
        chat_id = "999888777"
        self.xodim1.telegram_chat_id = chat_id
        self.xodim1.save()
        TelegramSession.objects.create(chat_id=chat_id, xodim=self.xodim1, state='AUTHENTICATED')

        # Command: Bugungi hisobot
        up_rep = {
            "update_id": 10,
            "message": {
                "chat": {"id": chat_id},
                "text": "📊 Bugungi hisobot"
            }
        }
        res = process_telegram_update(up_rep)
        self.assertTrue(res)

        # Command: Sozlamalar
        up_set = {
            "update_id": 11,
            "message": {
                "chat": {"id": chat_id},
                "text": "⚙️ Sozlamalar"
            }
        }
        res_set = process_telegram_update(up_set)
        self.assertTrue(res_set)

        # Toggle Notifications
        up_tog = {
            "update_id": 12,
            "message": {
                "chat": {"id": chat_id},
                "text": "🔔 Bildirishnomalar: Yoqilgan 🟢"
            }
        }
        process_telegram_update(up_tog)
        self.xodim1.refresh_from_db()
        self.assertFalse(self.xodim1.telegram_notifications_enabled)

        # Logout command
        up_out = {
            "update_id": 13,
            "message": {
                "chat": {"id": chat_id},
                "text": "🚪 Tizimdan chiqish"
            }
        }
        process_telegram_update(up_out)
        self.xodim1.refresh_from_db()
        session = TelegramSession.objects.get(chat_id=chat_id)
        self.assertIsNone(self.xodim1.telegram_chat_id)
        self.assertEqual(session.state, 'AWAITING_PHONE')

    def test_multi_tenant_notification_routing(self):
        self.xodim1.telegram_chat_id = "chat_owner_a"
        self.xodim1.telegram_notifications_enabled = True
        self.xodim1.save()

        self.xodim2.telegram_chat_id = "chat_owner_b"
        self.xodim2.telegram_notifications_enabled = True
        self.xodim2.save()

        # Create a sale for Biznes 1
        sale1 = Sale.objects.create(
            biznes=self.biznes1,
            dokon=self.dokon1,
            xodim=self.xodim1,
            kod="SALE-TEST-001",
            yakuniy_summa=Decimal("150000.00"),
            tolov_usuli="naqd"
        )
        notify_sale(sale1)

        # Create a write off for Biznes 1
        wo1 = WriteOff.objects.create(
            biznes=self.biznes1,
            dokon=self.dokon1,
            yaratgan_xodim=self.xodim1,
            sababi="Yaroqsiz holga kelgan",
            sotish_summasi=Decimal("20000.00")
        )
        notify_write_off(wo1)
