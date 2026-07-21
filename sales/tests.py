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

    def test_export_sales_to_excel(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        # Create a sale first
        payload = {
            "dokon": self.dokon.id,
            "kod": "SOTUV-EXCEL",
            "holat": "kechiktirilgan",
            "elementlar": [
                {
                    "mahsulot": self.product1.id,
                    "miqdori": 2
                }
            ]
        }
        self.client.post(self.sales_list_url, payload, format='json')

        # Now retrieve list with export=excel
        response = self.client.get(self.sales_list_url, {'export': 'excel'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))

    def test_get_sale_chek_details(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        payload = {
            "dokon": self.dokon.id,
            "mijoz": self.mijoz.id,
            "kod": "SOTUV-CHEK-123",
            "holat": "yakunlangan",
            "eslatma": "Mijozga chegirma qilindi",
            "elementlar": [
                {
                    "mahsulot": self.product1.id,
                    "miqdori": 1
                }
            ]
        }
        create_res = self.client.post(self.sales_list_url, payload, format='json')
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)

        sale_id = create_res.data['id']
        chek_url = reverse('sotuvlar-chek', kwargs={'pk': sale_id})
        
        response = self.client.get(chek_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['kod'], "SOTUV-CHEK-123")
        self.assertEqual(response.data['eslatma'], "Mijozga chegirma qilindi")
        self.assertEqual(len(response.data['elementlar']), 1)
        self.assertEqual(response.data['dokon']['nomi'], "Test Shop")

    def test_sales_stats_and_date_range_filters(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        payload = {
            "dokon": self.dokon.id,
            "kod": "SOTUV-STATS-1",
            "holat": "yakunlangan",
            "tolangan_summa": "60000.00",
            "elementlar": [
                {
                    "mahsulot": self.product1.id,
                    "miqdori": 1
                }
            ]
        }
        self.client.post(self.sales_list_url, payload, format='json')

        stats_url = reverse('sotuvlar-stats')
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['jami_kirim']), Decimal('60000.00'))
        self.assertIn('jami_chiqim', response.data)

    def test_cheklar_stats_summary(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        payload = {
            "dokon": self.dokon.id,
            "kod": "CHEK-STATS-1",
            "holat": "yakunlangan",
            "tolangan_summa": "120000.00",
            "elementlar": [
                {
                    "mahsulot": self.product1.id,
                    "miqdori": 2
                }
            ]
        }
        self.client.post(self.sales_list_url, payload, format='json')

        cheklar_stats_url = reverse('sotuvlar-cheklar-stats')
        response = self.client.get(cheklar_stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['cheklar'], 1)
        self.assertGreaterEqual(response.data['soni'], 2)
        self.assertGreaterEqual(Decimal(response.data['jami']), Decimal('120000.00'))

    def test_sales_dashboard_and_analytics(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)
        dashboard_url = reverse('sales-dashboard')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bugungi_savdo', response.data)
        self.assertIn('bugungi_xarajat', response.data)
        self.assertIn('sof_pul', response.data)
        self.assertIn('nasiyaga_sotilgan', response.data)
        self.assertIn('tolov_turlari', response.data)
        self.assertIn('top_5_mahsulot', response.data)
        self.assertIn('oxirgi_harakatlar', response.data)

        top_products_url = reverse('sales-top-products')
        response_top = self.client.get(top_products_url)
        self.assertEqual(response_top.status_code, status.HTTP_200_OK)

        recent_act_url = reverse('sales-recent-activities')
        response_act = self.client.get(recent_act_url)
        self.assertEqual(response_act.status_code, status.HTTP_200_OK)

    def test_expenses_and_panel_subtabs(self):
        self.client.force_authenticate(user=self.sotuvchi_user.user)

        cats_url = reverse('expense-categories')
        res_cats = self.client.get(cats_url)
        self.assertEqual(res_cats.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_cats.data), 5)
        cat_id = res_cats.data[0]['id']

        exp_url = reverse('expenses-list')
        exp_payload = {
            "kategoriya": cat_id,
            "miqdor": "150000.00",
            "tolov_turi": "naqd",
            "izoh": "Taksi xarajati"
        }
        res_exp = self.client.post(exp_url, exp_payload, format='json')
        self.assertEqual(res_exp.status_code, status.HTTP_201_CREATED)

        res_exp_list = self.client.get(exp_url)
        self.assertEqual(res_exp_list.status_code, status.HTTP_200_OK)

        res_cf = self.client.get(reverse('sales-cashflow'))
        self.assertEqual(res_cf.status_code, status.HTTP_200_OK)

        res_m = self.client.get(reverse('sales-monthly'))
        self.assertEqual(res_m.status_code, status.HTTP_200_OK)

        res_pa = self.client.get(reverse('sales-products-analytics'))
        self.assertEqual(res_pa.status_code, status.HTTP_200_OK)

        res_da = self.client.get(reverse('sales-debts-analytics'))
        self.assertEqual(res_da.status_code, status.HTTP_200_OK)

        res_abc = self.client.get(reverse('sales-abc-xyz'))
        self.assertEqual(res_abc.status_code, status.HTTP_200_OK)
        self.assertIn('summary', res_abc.data)
        self.assertIn('matrix', res_abc.data)
