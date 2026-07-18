from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from rest_framework.authtoken.models import Token
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
import openpyxl
from io import BytesIO

from user.models import Biznes, Xodim
from products.models import Dokon, Mahsulot, DokonQoldiq

class TransferAPITestCase(APITestCase):
    def setUp(self):
        self.dokon_list_url = reverse('dokon-list')
        self.transfer_list_url = reverse('transfer-list')

        self.biznes = Biznes.objects.create(nomi="Test Biznes", egasi_ism="Owner")

        self.dokon_a = Dokon.objects.create(biznes=self.biznes, nomi="Shop A", tavsif="Sender Shop")
        self.dokon_b = Dokon.objects.create(biznes=self.biznes, nomi="Shop B", tavsif="Receiver Shop")

        self.prod_x = Mahsulot.objects.create(
            biznes=self.biznes,
            nomi="Cement",
            shtrix_kod="12345678",
            olchov_birligi="kg",
            kelish_narxi=Decimal("10000.00"),
            ustama=Decimal("20.00"),
            miqdori=50,
            ogohlantirish=10
        )
        DokonQoldiq.objects.create(mahsulot=self.prod_x, dokon=self.dokon_a, miqdori=50, ogohlantirish=10)

        self.prod_y = Mahsulot.objects.create(
            biznes=self.biznes,
            nomi="Brick",
            shtrix_kod="87654321",
            olchov_birligi="dona",
            kelish_narxi=Decimal("2000.00"),
            ustama=Decimal("15.00"),
            miqdori=100,
            ogohlantirish=20
        )
        DokonQoldiq.objects.create(mahsulot=self.prod_y, dokon=self.dokon_a, miqdori=100, ogohlantirish=20)

        self.admin_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Admin", familiya="Testov", telefon_raqam="+998909999999",
            parol="adminpassword123", rol="admin", jinsi="erkak"
        )
        self.admin_token = Token.objects.create(user=self.admin_xodim.user).key

        self.cashier_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Cashier", familiya="Restricted", telefon_raqam="+998908888888",
            parol="cashierpassword123", rol="sotuvchi", jinsi="ayol"
        )
        self.cashier_token = Token.objects.create(user=self.cashier_xodim.user).key

    def test_dokon_list_and_create_permissions(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.cashier_token)
        response = self.client.get(self.dokon_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        response = self.client.post(self.dokon_list_url, {"nomi": "New Shop"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        response = self.client.post(self.dokon_list_url, {"nomi": "New Shop"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_transfer_via_json(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        payload = {
            "nomi": "Transfer Cement",
            "dokondan": self.dokon_a.id,
            "dokonga": self.dokon_b.id,
            "elementlar": [
                {
                    "nomi": "Cement",
                    "shtrix_kod": "12345678",
                    "miqdori": 10
                }
            ]
        }
        response = self.client.post(self.transfer_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['holat'], 'yakunlangan')
        self.assertEqual(response.data['miqdori'], 10)
        self.assertEqual(float(response.data['summa']), 120000.0)

        q_sender = DokonQoldiq.objects.get(mahsulot=self.prod_x, dokon=self.dokon_a)
        self.assertEqual(q_sender.miqdori, 40)
        q_receiver = DokonQoldiq.objects.get(mahsulot=self.prod_x, dokon=self.dokon_b)
        self.assertEqual(q_receiver.miqdori, 10)

        t_id = response.data['id']
        search_res = self.client.get(self.transfer_list_url, {"search": str(t_id)})
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in search_res.data]
        self.assertIn(t_id, ids)

    def test_transfer_via_excel(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Nomi", "Shtrix-kod", "Miqdori", "O'lchov birligi"])
        ws.append(["Brick", "87654321", "30", "dona"])

        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        mock_file = SimpleUploadedFile("transfer.xlsx", excel_file.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        payload = {
            "nomi": "Excel Transfer",
            "dokondan": self.dokon_a.id,
            "dokonga": self.dokon_b.id,
            "fayl": mock_file
        }
        response = self.client.post(self.transfer_list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['holat'], 'yakunlangan')
        self.assertEqual(response.data['miqdori'], 30)
        self.assertEqual(float(response.data['summa']), 69000.0)

        q_sender = DokonQoldiq.objects.get(mahsulot=self.prod_y, dokon=self.dokon_a)
        self.assertEqual(q_sender.miqdori, 70)
        q_receiver = DokonQoldiq.objects.get(mahsulot=self.prod_y, dokon=self.dokon_b)
        self.assertEqual(q_receiver.miqdori, 30)

    def test_transfer_invalid_product(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        payload = {
            "nomi": "Transfer Fake",
            "dokondan": self.dokon_a.id,
            "dokonga": self.dokon_b.id,
            "elementlar": [
                {
                    "nomi": "Fake Product",
                    "shtrix_kod": "99999999",
                    "miqdori": 10
                }
            ]
        }
        response = self.client.post(self.transfer_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_insufficient_stock(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        payload = {
            "nomi": "Over Transfer",
            "dokondan": self.dokon_a.id,
            "dokonga": self.dokon_b.id,
            "elementlar": [
                {
                    "nomi": "Cement",
                    "shtrix_kod": "12345678",
                    "miqdori": 60
                }
            ]
        }
        response = self.client.post(self.transfer_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_same_shop(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        payload = {
            "nomi": "Same Shop Transfer",
            "dokondan": self.dokon_a.id,
            "dokonga": self.dokon_a.id,
            "elementlar": [
                {
                    "nomi": "Cement",
                    "shtrix_kod": "12345678",
                    "miqdori": 5
                }
            ]
        }
        response = self.client.post(self.transfer_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
