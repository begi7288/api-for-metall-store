from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
from django.core.exceptions import ValidationError

from user.models import Biznes, Xodim, Mijoz
from products.models import Dokon, Mahsulot, DokonQoldiq
from sales.models import Sale, SaleItem

class SalesAPITestCase(APITestCase):
    def setUp(self):
        # 1. Create Business
        self.biznes = Biznes.objects.create(nomi="Test Biznes", egasi_ism="Owner")
        
        # 2. Create Employees
        self.admin_user = Xodim.objects.create(
            ism="Admin", familiya="Testov", telefon_raqam="+998901111111",
            parol="adminpassword123!", rol="admin", jinsi="erkak", biznes=self.biznes
        )
        self.sotuvchi_user = Xodim.objects.create(
            ism="Sotuvchi", familiya="Kassir", telefon_raqam="+998902222222",
            parol="cashierpassword123", rol="sotuvchi", jinsi="ayol", biznes=self.biznes
        )

        # 3. Create Dokon
        self.dokon = Dokon.objects.create(biznes=self.biznes, nomi="Test Shop")

        # 4. Create Mijoz
        self.mijoz = Mijoz.objects.create(
            biznes=self.biznes, ism="Ali", familiya="Valiyev", jinsi="erkak",
            telefon_raqam_1="901234567", telefon_raqam_2="901234568"
        )

        # 5. Create Products & initial inventory
        self.product1 = Mahsulot.objects.create(
            biznes=self.biznes, nomi="Armatura", olchov_birligi="kg",
            kelish_narxi=Decimal('40000.00'), ustama=Decimal('50.00'),
            sotish_narxi=Decimal('60000.00'), ulgurji_narx=Decimal('55000.00')
        )
        self.product2 = Mahsulot.objects.create(
            biznes=self.biznes, nomi="Cement", olchov_birligi="kg",
            kelish_narxi=Decimal('10000.00'), ustama=Decimal('20.00'),
            sotish_narxi=Decimal('12000.00'), ulgurji_narx=Decimal('11000.00')
        )

        # Add initial inventory stock
        self.qoldiq1 = DokonQoldiq.objects.create(mahsulot=self.product1, dokon=self.dokon, miqdori=100)
        self.qoldiq2 = DokonQoldiq.objects.create(mahsulot=self.product2, dokon=self.dokon, miqdori=50)

        self.product1.miqdori = 100
        self.product1.save()
        self.product2.miqdori = 50
        self.product2.save()

        # URLs
        self.sales_list_url = reverse('sotuvlar-list')

    def test_create_sale_completed_success(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        
        payload = {
            "dokon": self.dokon.id,
            "mijoz": self.mijoz.id,
            "kod": "SOTUV-987654",
            "holat": "yakunlangan",
            "chegirma_turi": "foiz",
            "chegirma_qiymati": "10.00",
            "tolangan_summa": "60000.00",
            "tolov_usuli": "naqd",
            "elementlar": [
                {
                    "mahsulot": self.product1.id,
                    "miqdori": 1,
                    "is_ulgurji": False
                },
                {
                    "mahsulot": self.product2.id,
                    "miqdori": 1,
                    "is_ulgurji": True
                }
            ]
        }
        
        response = self.client.post(self.sales_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Oraliq jami should be: Armatura sotish_narxi (60,000) + Cement ulgurji_narx (11,000) = 71,000 UZS
        self.assertEqual(Decimal(response.data['oraliq_jami']), Decimal('71000.00'))
        
        # Chegirma summasi: 10% of 71,000 = 7,100 UZS
        self.assertEqual(Decimal(response.data['chegirma_summasi']), Decimal('7100.00'))
        
        # Yakuniy summa: 71,000 - 7,100 = 63,900 UZS
        self.assertEqual(Decimal(response.data['yakuniy_summa']), Decimal('63900.00'))
        
        # Nasiya summa: 63,900 - 60,000 = 3,900 UZS
        self.assertEqual(Decimal(response.data['nasiya_summa']), Decimal('3900.00'))

        # Check stock deduction
        self.qoldiq1.refresh_from_db()
        self.qoldiq2.refresh_from_db()
        self.assertEqual(self.qoldiq1.miqdori, 99)
        self.assertEqual(self.qoldiq2.miqdori, 49)

    def test_create_sale_insufficient_stock(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        
        payload = {
            "dokon": self.dokon.id,
            "kod": "SOTUV-ERROR",
            "holat": "yakunlangan",
            "elementlar": [
                {
                    "mahsulot": self.product1.id,
                    "miqdori": 150 # Exceeds available 100
                }
            ]
        }
        response = self.client.post(self.sales_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('elementlar', response.data['errors'])

    def test_create_sale_delayed_no_stock_deduction(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        
        payload = {
            "dokon": self.dokon.id,
            "kod": "SOTUV-DELAYED",
            "holat": "kechiktirilgan",
            "elementlar": [
                {
                    "mahsulot": self.product1.id,
                    "miqdori": 10
                }
            ]
        }
        response = self.client.post(self.sales_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Stock should NOT be deducted
        self.qoldiq1.refresh_from_db()
        self.assertEqual(self.qoldiq1.miqdori, 100)

        # Now complete the sale via patch/update
        sale_id = response.data['id']
        detail_url = reverse('sotuvlar-detail', kwargs={'pk': sale_id})
        
        patch_response = self.client.patch(detail_url, {"holat": "yakunlangan"}, format='json')
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        # Stock should be deducted now
        self.qoldiq1.refresh_from_db()
        self.assertEqual(self.qoldiq1.miqdori, 90)

    def test_delete_sale_restores_stock(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        
        payload = {
            "dokon": self.dokon.id,
            "kod": "SOTUV-TO-DELETE",
            "holat": "yakunlangan",
            "elementlar": [
                {
                    "mahsulot": self.product1.id,
                    "miqdori": 5
                }
            ]
        }
        response = self.client.post(self.sales_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.qoldiq1.refresh_from_db()
        self.assertEqual(self.qoldiq1.miqdori, 95)

        # Delete the sale
        sale_id = response.data['id']
        detail_url = reverse('sotuvlar-detail', kwargs={'pk': sale_id})
        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Stock should be restored to 100
        self.qoldiq1.refresh_from_db()
        self.assertEqual(self.qoldiq1.miqdori, 100)
