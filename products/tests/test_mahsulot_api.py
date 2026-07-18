from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from rest_framework.authtoken.models import Token
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from io import BytesIO

from user.models import Xodim, Biznes
from products.models import Mahsulot, Dokon, DokonQoldiq, Characteristic, MahsulotRasm, MahsulotShtrixKod, YorliqShablon

class MahsulotAPITestCase(APITestCase):
    def setUp(self):
        self.list_url = reverse('mahsulot-list')
        self.biznes = Biznes.objects.create(nomi="Test Biznes", egasi_ism="Owner")
        self.dokon = Dokon.objects.create(biznes=self.biznes, nomi="Test Dokon")

        self.manager_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Manager", familiya="Testov", telefon_raqam="+998907777777",
            parol="managerpassword123", rol="omborchi", jinsi="erkak"
        )
        self.manager_token = Token.objects.create(user=self.manager_xodim.user).key
        
        self.cashier_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Cashier", familiya="Testova", telefon_raqam="+998906666666",
            parol="cashierpassword123", rol="sotuvchi", jinsi="ayol"
        )
        self.cashier_token = Token.objects.create(user=self.cashier_xodim.user).key

        self.p1 = Mahsulot.objects.create(
            biznes=self.biznes,
            nomi="Shifer Plastik", olchov_birligi="dona",
            kelish_narxi=Decimal("50000.00"), ustama=Decimal("20.00"),
            miqdori=100, ogohlantirish=10
        )
        DokonQoldiq.objects.create(mahsulot=self.p1, dokon=self.dokon, miqdori=100, ogohlantirish=10)

        self.p2 = Mahsulot.objects.create(
            biznes=self.biznes,
            nomi="Massa Gips", olchov_birligi="kg",
            kelish_narxi=Decimal("10000.00"), ustama=Decimal("10.00"),
            miqdori=5, ogohlantirish=10
        )
        DokonQoldiq.objects.create(mahsulot=self.p2, dokon=self.dokon, miqdori=5, ogohlantirish=10)

    def test_create_product_api_success(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        payload = {
            "nomi": "Kran",
            "olchov_birligi": "dona",
            "kelish_narxi": "20000.00",
            "ustama": "15.00",
            "qoldiqlar": [
                {
                    "dokon": self.dokon.id,
                    "miqdori": 10,
                    "ogohlantirish": 2
                }
            ]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['sotish_narxi']), Decimal("23000.00"))

    def test_create_product_api_unauthorized_for_cashier(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.cashier_token)
        payload = {
            "nomi": "Kran",
            "olchov_birligi": "dona",
            "kelish_narxi": "20000.00",
            "ustama": "15.00",
            "miqdori": 10
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_products_allowed_for_cashier(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.cashier_token)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_product_detail(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.cashier_token)
        detail_url = reverse('mahsulot-detail', kwargs={'pk': self.p1.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nomi'], "Shifer Plastik")

    def test_update_product_success(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        detail_url = reverse('mahsulot-detail', kwargs={'pk': self.p1.pk})
        payload = {"nomi": "Shifer Plastik Yangi", "kelish_narxi": "50000.00", "sotish_narxi": "65000.00"}
        response = self.client.patch(detail_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nomi'], "Shifer Plastik Yangi")

    def test_delete_product_success(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        detail_url = reverse('mahsulot-detail', kwargs={'pk': self.p1.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Mahsulot.objects.count(), 1)

    def test_filter_by_olchov_birligi(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        response = self.client.get(self.list_url, {'olchov_birligi': 'kg'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nomi'], "Massa Gips")

    def test_search_by_name(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        response = self.client.get(self.list_url, {'search': 'Plastik'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nomi'], "Shifer Plastik")

    def test_custom_filter_kam_qoldi(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        response = self.client.get(self.list_url, {'kam_qoldi': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nomi'], "Massa Gips")

    def test_product_api_with_characteristics(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        char = Characteristic.objects.create(name="Kafolat", value="1 yil")
        self.p1.characteristics.add(char)
        
        detail_url = reverse('mahsulot-detail', kwargs={'pk': self.p1.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('characteristics', response.data)
        self.assertEqual(len(response.data['characteristics']), 1)
        self.assertEqual(response.data['characteristics'][0]['name'], "Kafolat")
        self.assertEqual(response.data['characteristics'][0]['value'], "1 yil")

    def test_create_product_with_characteristics(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        char1 = Characteristic.objects.create(name="Rang", value="Qora")
        char2 = Characteristic.objects.create(name="Kafolat", value="1 yil")
        payload = {
            "nomi": "Dazmol",
            "olchov_birligi": "dona",
            "kelish_narxi": "150000.00",
            "ustama": "20.00",
            "characteristics": [char1.id, char2.id],
            "qoldiqlar": [
                {
                    "dokon": self.dokon.id,
                    "miqdori": 10,
                    "ogohlantirish": 2
                }
            ]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['characteristics']), 2)
        self.assertEqual(response.data['characteristics'][0]['name'], "Rang")
        self.assertEqual(response.data['characteristics'][0]['value'], "Qora")
        self.assertEqual(response.data['characteristics'][1]['name'], "Kafolat")
        self.assertEqual(response.data['characteristics'][1]['value'], "1 yil")

    def test_create_product_invalid_characteristics(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        payload = {
            "nomi": "Dazmol",
            "olchov_birligi": "dona",
            "kelish_narxi": "150000.00",
            "ustama": "20.00",
            "miqdori": 10,
            "characteristics": [99999]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_grouped_characteristics_api(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        Characteristic.objects.create(name="Brend", value="Quvasoy")
        Characteristic.objects.create(name="Brend", value="Samsung")
        Characteristic.objects.create(name="Yetkazib beruvchi", value="Husniddin")
        
        grouped_url = reverse('characteristic-grouped')
        response = self.client.get(grouped_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Brend', response.data)
        self.assertIn('Yetkazib beruvchi', response.data)
        self.assertEqual(len(response.data['Brend']), 2)
        self.assertEqual(len(response.data['Yetkazib beruvchi']), 1)

    def test_create_product_with_multiple_barcodes(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        payload = {
            "nomi": "Dazmol",
            "olchov_birligi": "dona",
            "kelish_narxi": "150000.00",
            "ustama": "20.00",
            "shtrix_kod": ["12345678", "9876543210123"],
            "qoldiqlar": [
                {
                    "dokon": self.dokon.id,
                    "miqdori": 10,
                    "ogohlantirish": 2
                }
            ]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['shtrix_kod']), 2)
        self.assertIn("12345678", response.data['shtrix_kod'])
        self.assertIn("9876543210123", response.data['shtrix_kod'])

    def test_create_product_with_comma_separated_barcodes(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        payload = {
            "nomi": "Mikroto'lqinli Pech",
            "olchov_birligi": "dona",
            "kelish_narxi": "500000.00",
            "ustama": "15.00",
            "shtrix_kod": "11112222, 33334444, 55556666",
            "qoldiqlar": [
                {
                    "dokon": self.dokon.id,
                    "miqdori": 5,
                    "ogohlantirish": 1
                }
            ]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['shtrix_kod']), 3)
        self.assertIn("11112222", response.data['shtrix_kod'])
        self.assertIn("33334444", response.data['shtrix_kod'])
        self.assertIn("55556666", response.data['shtrix_kod'])

    def test_create_product_with_duplicate_barcodes(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        payload1 = {
            "nomi": "Dazmol 1",
            "olchov_birligi": "dona",
            "kelish_narxi": "150000.00",
            "ustama": "20.00",
            "shtrix_kod": ["12345678"],
            "qoldiqlar": [
                {
                    "dokon": self.dokon.id,
                    "miqdori": 10,
                    "ogohlantirish": 2
                }
            ]
        }
        self.client.post(self.list_url, payload1, format='json')

        payload2 = {
            "nomi": "Dazmol 2",
            "olchov_birligi": "dona",
            "kelish_narxi": "150000.00",
            "ustama": "20.00",
            "shtrix_kod": ["12345678"],
            "qoldiqlar": [
                {
                    "dokon": self.dokon.id,
                    "miqdori": 10,
                    "ogohlantirish": 2
                }
            ]
        }
        response = self.client.post(self.list_url, payload2, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('shtrix_kod', response.data['errors'])

    def test_search_by_multiple_barcodes(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)
        self.p1.shtrix_kodlar.all().delete()
        MahsulotShtrixKod.objects.create(mahsulot=self.p1, kod="1111111111111")
        MahsulotShtrixKod.objects.create(mahsulot=self.p1, kod="2222222222222")

        response = self.client.get(self.list_url, {'search': '2222222222222'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nomi'], "Shifer Plastik")

    def test_create_product_with_multiple_images(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)

        img = Image.new('RGB', (1, 1), color='red')
        buf = BytesIO()
        img.save(buf, format='JPEG')
        jpeg_data = buf.getvalue()

        img1 = SimpleUploadedFile("img1.jpg", jpeg_data, content_type="image/jpeg")
        img2 = SimpleUploadedFile("img2.jpg", jpeg_data, content_type="image/jpeg")
        img3 = SimpleUploadedFile("img3.jpg", jpeg_data, content_type="image/jpeg")
        
        payload = {
            "nomi": "Dazmol",
            "olchov_birligi": "dona",
            "kelish_narxi": "150000.00",
            "ustama": "20.00",
            "rasm": [img1, img2, img3],
            "qoldiqlar": '[{"dokon": %d, "miqdori": 10, "ogohlantirish": 2}]' % self.dokon.id
        }
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['rasm']), 3)

    def test_create_product_with_too_many_images(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)

        img = Image.new('RGB', (1, 1), color='red')
        buf = BytesIO()
        img.save(buf, format='JPEG')
        jpeg_data = buf.getvalue()

        images = [
            SimpleUploadedFile(f"img{i}.jpg", jpeg_data, content_type="image/jpeg")
            for i in range(6)
        ]
        payload = {
            "nomi": "Dazmol",
            "olchov_birligi": "dona",
            "kelish_narxi": "150000.00",
            "ustama": "20.00",
            "rasm": images,
            "qoldiqlar": '[{"dokon": %d, "miqdori": 10, "ogohlantirish": 2}]' % self.dokon.id
        }
        response = self.client.post(self.list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rasm', response.data['errors'])


class MahsulotRasmAPITestCase(APITestCase):
    def setUp(self):
        self.image_list_url = reverse('product-image-list')
        self.biznes = Biznes.objects.create(nomi="Test Biznes", egasi_ism="Owner")
        self.manager_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Manager", familiya="Testov", telefon_raqam="+998907777777",
            parol="managerpassword123", rol="omborchi", jinsi="erkak"
        )
        self.manager_token = Token.objects.create(user=self.manager_xodim.user).key
        self.product = Mahsulot.objects.create(
            biznes=self.biznes,
            nomi="Dazmol",
            olchov_birligi="dona",
            kelish_narxi=Decimal("150000.00"),
            ustama=Decimal("20.00"),
            miqdori=10
        )

    def test_upload_single_image_to_product(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)

        img = Image.new('RGB', (1, 1), color='red')
        buf = BytesIO()
        img.save(buf, format='JPEG')
        jpeg_data = buf.getvalue()

        file = SimpleUploadedFile("single.jpg", jpeg_data, content_type="image/jpeg")
        payload = {
            "mahsulot": self.product.id,
            "rasm": file
        }
        response = self.client.post(self.image_list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.rasmlar.count(), 1)

    def test_upload_image_exceeding_limit(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)

        img = Image.new('RGB', (1, 1), color='red')
        buf = BytesIO()
        img.save(buf, format='JPEG')
        jpeg_data = buf.getvalue()

        for i in range(5):
            file = SimpleUploadedFile(f"file_{i}.jpg", jpeg_data, content_type="image/jpeg")
            MahsulotRasm.objects.create(mahsulot=self.product, rasm=file)

        file = SimpleUploadedFile("sixth.jpg", jpeg_data, content_type="image/jpeg")
        payload = {
            "mahsulot": self.product.id,
            "rasm": file
        }
        response = self.client.post(self.image_list_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MahsulotShtrixKodAPITestCase(APITestCase):
    def setUp(self):
        self.barcodes_url = reverse('product-barcode-list')
        self.biznes = Biznes.objects.create(nomi="Test Biznes", egasi_ism="Owner")
        self.manager_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Manager", familiya="Testov", telefon_raqam="+998907777777",
            parol="managerpassword123", rol="omborchi", jinsi="erkak"
        )
        self.manager_token = Token.objects.create(user=self.manager_xodim.user).key
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token)

        self.product = Mahsulot.objects.create(
            biznes=self.biznes,
            nomi="Cement",
            shtrix_kod="12345678",
            olchov_birligi="kg",
            kelish_narxi=Decimal("10000.00"),
            ustama=Decimal("20.00"),
            miqdori=50,
            ogohlantirish=10
        )

    def test_list_barcodes_for_product(self):
        response = self.client.get(self.barcodes_url, {'mahsulot': self.product.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['kod'], "12345678")

    def test_add_barcode_success(self):
        payload = {
            "mahsulot": self.product.id,
            "kod": "9876543210123"
        }
        response = self.client.post(self.barcodes_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.shtrix_kodlar.count(), 2)

    def test_add_barcode_validation(self):
        payload = {
            "mahsulot": self.product.id,
            "kod": "12345678"
        }
        response = self.client.post(self.barcodes_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('kod', response.data['errors'])

        payload = {
            "mahsulot": self.product.id,
            "kod": "12345"
        }
        response = self.client.post(self.barcodes_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_barcode_protection(self):
        only_bc = self.product.shtrix_kodlar.first()
        delete_url = reverse('product-barcode-detail', kwargs={'pk': only_bc.id})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data['errors'])

        new_bc = MahsulotShtrixKod.objects.create(mahsulot=self.product, kod="9876543210123")
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.product.shtrix_kodlar.count(), 1)


class BulkOperationsAPITestCase(APITestCase):
    def setUp(self):
        from user.models import Biznes, Xodim, Tarif
        from products.models import Dokon, Mahsulot
        from rest_framework.authtoken.models import Token
        from django.contrib.auth.models import User

        self.tarif = Tarif.objects.create(nomi="Pro", dokon_limiti=5, mahsulot_limiti=100, xodim_limiti=5)
        self.biznes1 = Biznes.objects.create(nomi="Biznes 1", egasi_ism="Owner 1", tarif=self.tarif)
        self.biznes2 = Biznes.objects.create(nomi="Biznes 2", egasi_ism="Owner 2", tarif=self.tarif)

        self.u1 = User.objects.create_user(username="u1_bulk", password="password123")
        self.u2 = User.objects.create_user(username="u2_bulk", password="password123")

        self.x1 = Xodim.objects.create(
            user=self.u1, ism="Ali", familiya="Valiyev", telefon_raqam="+998901111111", 
            parol="secret123", jinsi="erkak", biznes=self.biznes1, rol="admin"
        )
        self.x2 = Xodim.objects.create(
            user=self.u2, ism="Bobur", familiya="Karimov", telefon_raqam="+998902222222", 
            parol="secret123", jinsi="erkak", biznes=self.biznes2, rol="admin"
        )

        self.t1 = Token.objects.create(user=self.u1).key
        self.t2 = Token.objects.create(user=self.u2).key

        self.p1 = Mahsulot.objects.create(biznes=self.biznes1, nomi="Metal A", olchov_birligi="dona", kelish_narxi=Decimal("1000.00"), sotish_narxi=Decimal("1500.00"), miqdori=10)
        self.p2 = Mahsulot.objects.create(biznes=self.biznes1, nomi="Metal B", olchov_birligi="dona", kelish_narxi=Decimal("2000.00"), sotish_narxi=Decimal("3000.00"), miqdori=20)
        self.p3 = Mahsulot.objects.create(biznes=self.biznes2, nomi="Cement C", olchov_birligi="kg", kelish_narxi=Decimal("1500.00"), sotish_narxi=Decimal("2000.00"), miqdori=15)

        self.bulk_url = reverse('mahsulot-bulk-operations')

    def test_bulk_archive(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        payload = {
            "action": "archive",
            "product_ids": [self.p1.id, self.p2.id],
            "params": {"archive": True}
        }
        response = self.client.post(self.bulk_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertFalse(self.p1.is_active)
        self.assertFalse(self.p2.is_active)

    def test_bulk_archive_saas_isolation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t2)
        payload = {
            "action": "archive",
            "product_ids": [self.p1.id],
            "params": {"archive": True}
        }
        response = self.client.post(self.bulk_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_set_low_stock(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        payload = {
            "action": "set_low_stock",
            "product_ids": [self.p1.id, self.p2.id],
            "params": {"threshold": 12}
        }
        response = self.client.post(self.bulk_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.ogohlantirish, 12)
        self.assertEqual(self.p2.ogohlantirish, 12)

    def test_bulk_edit_prices_percentage_increase(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        payload = {
            "action": "edit_prices",
            "product_ids": [self.p1.id, self.p2.id],
            "params": {
                "price_type": "sotish_narxi",
                "operation": "oshirish_foiz",
                "value": 10.00
            }
        }
        response = self.client.post(self.bulk_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.sotish_narxi, Decimal("1650.00"))
        self.assertEqual(self.p2.sotish_narxi, Decimal("3300.00"))

    def test_bulk_edit_prices_erkin_narx(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        payload = {
            "action": "edit_prices",
            "product_ids": [self.p1.id, self.p2.id],
            "params": {
                "erkin_narx": True
            }
        }
        response = self.client.post(self.bulk_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertTrue(self.p1.erkin_narx)
        self.assertTrue(self.p2.erkin_narx)

    def test_bulk_edit_characteristics(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        payload = {
            "action": "edit_characteristics",
            "product_ids": [self.p1.id, self.p2.id],
            "params": {
                "characteristics": {
                    "Qalinligi": "8mm",
                    "Rangi": "Ko'k"
                }
            }
        }
        response = self.client.post(self.bulk_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        
        c1 = self.p1.characteristics.filter(name="Qalinligi", value="8mm").first()
        self.assertIsNotNone(c1)
        c2 = self.p2.characteristics.filter(name="Rangi", value="Ko'k").first()
        self.assertIsNotNone(c2)

    def test_bulk_print_labels(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        payload = {
            "action": "print_labels",
            "product_ids": [self.p1.id, self.p2.id]
        }
        response = self.client.post(self.bulk_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("labels", response.data)
        self.assertEqual(len(response.data["labels"]), 2)
        self.assertEqual(response.data["labels"][0]["nomi"], "Metal A")

    def test_bulk_print_labels_with_stock_quantity(self):
        from products.models import DokonQoldiq, Dokon
        dokon = Dokon.objects.create(biznes=self.biznes1, nomi="Test Shop")
        DokonQoldiq.objects.create(mahsulot=self.p1, dokon=dokon, miqdori=7)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        
        payload = {
            "action": "print_labels",
            "product_ids": [self.p1.id],
            "params": {
                "soni_turi": "qoldiqlar_boyicha"
            }
        }
        response = self.client.post(self.bulk_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["labels"][0]["soni"], 10)

        payload_store = {
            "action": "print_labels",
            "product_ids": [self.p1.id],
            "params": {
                "soni_turi": "qoldiqlar_boyicha",
                "dokon": dokon.id
            }
        }
        response = self.client.post(self.bulk_url, payload_store, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["labels"][0]["soni"], 7)

        from products.models import Mahsulot
        p_zero = Mahsulot.objects.create(biznes=self.biznes1, nomi="Zero Stock", olchov_birligi="dona", kelish_narxi=Decimal("100.00"), sotish_narxi=Decimal("150.00"), miqdori=0)

        payload_skip = {
            "action": "print_labels",
            "product_ids": [self.p1.id, p_zero.id],
            "params": {
                "nol_qoldiq_otkazish": True
            }
        }
        response = self.client.post(self.bulk_url, payload_skip, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["labels"]), 1)
        self.assertEqual(response.data["labels"][0]["nomi"], "Metal A")


class YorliqShablonAPITestCase(APITestCase):
    def setUp(self):
        from user.models import Biznes, Xodim, Tarif
        from rest_framework.authtoken.models import Token
        from django.contrib.auth.models import User

        self.tarif = Tarif.objects.create(nomi="Pro", dokon_limiti=5, mahsulot_limiti=100, xodim_limiti=5)
        self.biznes1 = Biznes.objects.create(nomi="Biznes 1", egasi_ism="Owner 1", tarif=self.tarif)
        self.biznes2 = Biznes.objects.create(nomi="Biznes 2", egasi_ism="Owner 2", tarif=self.tarif)

        self.u1 = User.objects.create_user(username="u1_shablon", password="password123")
        self.u2 = User.objects.create_user(username="u2_shablon", password="password123")

        self.x1 = Xodim.objects.create(
            user=self.u1, ism="Ali", familiya="Valiyev", telefon_raqam="+998904444444", 
            parol="secret123", jinsi="erkak", biznes=self.biznes1, rol="admin"
        )
        self.x2 = Xodim.objects.create(
            user=self.u2, ism="Bobur", familiya="Karimov", telefon_raqam="+998905555555", 
            parol="secret123", jinsi="erkak", biznes=self.biznes2, rol="admin"
        )

        self.t1 = Token.objects.create(user=self.u1).key
        self.t2 = Token.objects.create(user=self.u2).key

        self.list_url = reverse('price-tag-templates-list')

    def test_create_and_read_template(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        payload = {
            "nomi": "Standart 40x20",
            "eni": 40.0,
            "uzunlik": 20.0,
            "shtrixkod_formati": "CODE128",
            "xususiyatlar": ["nomi", "sotish_narxi", "shtrix_kod"]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nomi"], "Standart 40x20")

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["xususiyatlar"], ["nomi", "sotish_narxi", "shtrix_kod"])

    def test_template_saas_isolation(self):
        from products.models import YorliqShablon
        shablon = YorliqShablon.objects.create(biznes=self.biznes1, nomi="Biznes 1 template", eni=40, uzunlik=20)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t2)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        detail_url = reverse('price-tag-templates-detail', kwargs={'pk': shablon.id})
        response = self.client.put(detail_url, {"nomi": "Hacked"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
