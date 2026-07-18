from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from rest_framework.authtoken.models import Token
from decimal import Decimal

from user.models import Biznes, Xodim, Tarif
from products.models import Dokon, Mahsulot, DokonQoldiq

class ToplamAPITestCase(APITestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.tarif = Tarif.objects.create(nomi="Pro", dokon_limiti=5, mahsulot_limiti=100, xodim_limiti=5)
        
        self.biznes1 = Biznes.objects.create(nomi="Biznes 1", egasi_ism="Owner 1", tarif=self.tarif)
        self.biznes2 = Biznes.objects.create(nomi="Biznes 2", egasi_ism="Owner 2", tarif=self.tarif)

        self.u1 = User.objects.create_user(username="u1", password="p1")
        self.u2 = User.objects.create_user(username="u2", password="p2")

        self.x1 = Xodim.objects.create(user=self.u1, ism="Ali", familiya="Valiyev", telefon_raqam="+998901234567", parol="secret123", jinsi="erkak", biznes=self.biznes1, rol="admin")
        self.x2 = Xodim.objects.create(user=self.u2, ism="Bobur", familiya="Karimov", telefon_raqam="+998901234568", parol="secret123", jinsi="erkak", biznes=self.biznes2, rol="admin")

        self.t1 = Token.objects.create(user=self.u1).key
        self.t2 = Token.objects.create(user=self.u2).key

        self.dokon1 = Dokon.objects.create(biznes=self.biznes1, nomi="Store 1")
        self.dokon2 = Dokon.objects.create(biznes=self.biznes2, nomi="Store 2")

        self.p1 = Mahsulot.objects.create(biznes=self.biznes1, nomi="Cement", olchov_birligi="dona", kelish_narxi=Decimal("100.00"), sotish_narxi=Decimal("150.00"), miqdori=0)
        self.p2 = Mahsulot.objects.create(biznes=self.biznes2, nomi="Metal", olchov_birligi="dona", kelish_narxi=Decimal("200.00"), sotish_narxi=Decimal("300.00"), miqdori=0)

        self.dq1 = DokonQoldiq.objects.create(mahsulot=self.p1, dokon=self.dokon1, miqdori=10, ogohlantirish=0)
        self.p1.miqdori = 10
        self.p1.save()

        self.list_url = reverse('toplam-list')

    def test_create_toplam_replenishment_success(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t1)
        payload = {
            "nomi": "Topilgan batch",
            "dokon": self.dokon1.id,
            "elementlar": [
                {
                    "mahsulot": self.p1.id,
                    "miqdori": 15
                }
            ]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['holat'], 'yakunlangan')

        self.dq1.refresh_from_db()
        self.assertEqual(self.dq1.miqdori, 25)

        self.p1.refresh_from_db()
        self.assertEqual(self.p1.miqdori, 25)

    def test_toplam_saas_isolation(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.t2)
        payload = {
            "nomi": "Illegal replenishment",
            "dokon": self.dokon1.id,
            "elementlar": [
                {
                    "mahsulot": self.p2.id,
                    "miqdori": 5
                }
            ]
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('dokon', response.data['errors'])
