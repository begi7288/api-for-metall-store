from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from rest_framework.authtoken.models import Token
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
import openpyxl
from io import BytesIO
import datetime

from user.models import Biznes, Xodim, Tarif
from products.models import Dokon, Mahsulot, DokonQoldiq, MahsulotShtrixKod, WriteOff

class WriteOffAPITestCase(APITestCase):
    def setUp(self):
        self.write_off_list_url = reverse('write-off-list')
        self.biznes1 = Biznes.objects.create(nomi="Biznes 1", egasi_ism="Owner 1")
        self.biznes2 = Biznes.objects.create(nomi="Biznes 2", egasi_ism="Owner 2")

        self.admin1 = Xodim.objects.create(
            biznes=self.biznes1,
            ism="AdminBir", familiya="Testov", telefon_raqam="+998901111111",
            parol="adminpassword123!", rol="admin", jinsi="erkak"
        )
        self.admin1_token = Token.objects.create(user=self.admin1.user).key

        self.admin2 = Xodim.objects.create(
            biznes=self.biznes2,
            ism="AdminIkki", familiya="Testov", telefon_raqam="+998902222222",
            parol="adminpassword234!", rol="admin", jinsi="erkak"
        )
        self.admin2_token = Token.objects.create(user=self.admin2.user).key

        self.dokon1 = Dokon.objects.create(biznes=self.biznes1, nomi="Store 1")
        self.dokon2 = Dokon.objects.create(biznes=self.biznes2, nomi="Store 2")

        self.prod_a = Mahsulot.objects.create(
            biznes=self.biznes1, nomi="Cement A", olchov_birligi="kg",
            kelish_narxi=Decimal("10000.00"), sotish_narxi=Decimal("15000.00"), miqdori=100
        )
        MahsulotShtrixKod.objects.create(mahsulot=self.prod_a, kod="11111111")
        self.qoldiq_a = DokonQoldiq.objects.create(mahsulot=self.prod_a, dokon=self.dokon1, miqdori=100)

        self.prod_b = Mahsulot.objects.create(
            biznes=self.biznes2, nomi="Cement B", olchov_birligi="kg",
            kelish_narxi=Decimal("10000.00"), sotish_narxi=Decimal("15000.00"), miqdori=100
        )
        MahsulotShtrixKod.objects.create(mahsulot=self.prod_b, kod="22222222")
        self.qoldiq_b = DokonQoldiq.objects.create(mahsulot=self.prod_b, dokon=self.dokon2, miqdori=100)

    def test_write_off_manual_workflow(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)

        payload = {
            "nomi": "Yaroqsiz Mahsulotlar",
            "dokon": self.dokon1.id,
            "sababi": "defekt",
            "fayldan_hisobdan_chiqarish": False,
            "elementlar": [
                {
                    "mahsulot": self.prod_a.id,
                    "miqdori": 10
                }
            ]
        }
        response = self.client.post(self.write_off_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        write_off_id = response.data['id']
        self.assertEqual(response.data['holat'], 'qoralama')
        self.assertEqual(response.data['miqdori'], 10)
        self.assertEqual(float(response.data['kelish_summasi']), 100000.0)
        self.assertEqual(float(response.data['sotish_summasi']), 150000.0)

        confirm_url = reverse('write-off-confirm', kwargs={'pk': write_off_id})
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['holat'], 'yakunlangan')

        self.qoldiq_a.refresh_from_db()
        self.assertEqual(self.qoldiq_a.miqdori, 90)
        self.prod_a.refresh_from_db()
        self.assertEqual(self.prod_a.miqdori, 90)

    def test_write_off_insufficient_stock(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)

        payload = {
            "nomi": "Excess Write-off",
            "dokon": self.dokon1.id,
            "sababi": "defekt",
            "fayldan_hisobdan_chiqarish": False,
            "elementlar": [
                {
                    "mahsulot": self.prod_a.id,
                    "miqdori": 150
                }
            ]
        }
        response = self.client.post(self.write_off_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        write_off_id = response.data['id']

        confirm_url = reverse('write-off-confirm', kwargs={'pk': write_off_id})
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_write_off_excel_import(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Nomi", "Shtrix-kod", "Miqdori", "Kelish narxi"])
        ws.append(["Cement A", "11111111", "20", "10000.00"])

        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        mock_file = SimpleUploadedFile("write_off.xlsx", excel_file.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        payload = {
            "nomi": "Excel Write-off",
            "dokon": self.dokon1.id,
            "sababi": "yoqotish",
            "fayldan_hisobdan_chiqarish": True,
            "fayl": mock_file
        }
        response = self.client.post(self.write_off_list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['miqdori'], 20)
        self.assertEqual(float(response.data['kelish_summasi']), 200000.0)

    def test_write_off_excel_missing_file(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)
        payload = {
            "nomi": "Missing Excel File",
            "dokon": self.dokon1.id,
            "sababi": "yoqotish",
            "fayldan_hisobdan_chiqarish": True
        }
        response = self.client.post(self.write_off_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fayl', response.data['errors'])

    def test_write_off_saas_tenant_isolation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin2_token)
        payload = {
            "nomi": "Illegal Store",
            "dokon": self.dokon1.id,
            "sababi": "yoqotish",
            "fayldan_hisobdan_chiqarish": False,
            "elementlar": [
                {
                    "mahsulot": self.prod_b.id,
                    "miqdori": 5
                }
            ]
        }
        response = self.client.post(self.write_off_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('dokon', response.data['errors'])


class WriteOffExtraAPITestCase(APITestCase):
    def setUp(self):
        self.tarif = Tarif.objects.create(nomi="Pro", dokon_limiti=5, mahsulot_limiti=100, xodim_limiti=5)
        self.biznes = Biznes.objects.create(nomi="Biznes 1", egasi_ism="Owner 1", tarif=self.tarif)

        from django.contrib.auth.models import User
        self.u1 = User.objects.create_user(username="u1_writeoff", password="password123")
        self.x1 = Xodim.objects.create(
            user=self.u1, ism="Ali", familiya="Valiyev", telefon_raqam="+998906666666", 
            parol="secret123", jinsi="erkak", biznes=self.biznes, rol="admin"
        )
        self.t1 = Token.objects.create(user=self.u1).key

        self.dokon = Dokon.objects.create(biznes=self.biznes, nomi="WriteOff Shop")
        self.p1 = Mahsulot.objects.create(biznes=self.biznes, nomi="Cement A", olchov_birligi="kg", kelish_narxi=Decimal("100.00"), sotish_narxi=Decimal("150.00"), miqdori=10)

        DokonQoldiq.objects.create(mahsulot=self.p1, dokon=self.dokon, miqdori=10)
        self.w1 = WriteOff.objects.create(biznes=self.biznes, dokon=self.dokon, nomi="Defect writeoff", sababi="defekt", holat="qoralama")
        self.list_url = reverse('write-off-list')

    def test_write_off_list_search_and_filter(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)

        response = self.client.get(self.list_url, {"search": str(self.w1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get(self.list_url, {"search": "Defect"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get(self.list_url, {"sababi": "defekt"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get(self.list_url, {"sababi": "inventarizatsiya"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        today_str = datetime.date.today().isoformat()
        response = self.client.get(self.list_url, {"sana": today_str})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
