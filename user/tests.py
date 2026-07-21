from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from rest_framework.authtoken.models import Token
from .models import Xodim, Mijoz, Biznes, Tarif

class XodimModelTest(TestCase):
    def test_password_hashing_and_strength(self):
        xodim = Xodim(
            ism="Ali", familiya="Valiyev", telefon_raqam="+998901234567",
            parol="secret123", rol="sotuvchi", jinsi="erkak"
        )
        xodim.save()
        self.assertNotEqual(xodim.parol, "secret123")
        self.assertTrue(check_password("secret123", xodim.parol))
        # Check standard user creation
        self.assertIsNotNone(xodim.user)
        self.assertEqual(xodim.user.username, "998901234567")

    def test_name_validations(self):
        # Numeric characters in name should raise ValidationError
        x1 = Xodim(ism="Ali123", familiya="Valiyev", telefon_raqam="+998901234567", parol="secret123", jinsi="erkak")
        with self.assertRaises(ValidationError):
            x1.full_clean()

    def test_password_strength_failures(self):
        # Too short (under 6 characters)
        with self.assertRaises(ValidationError):
            Xodim(ism="Ali", familiya="Valiyev", telefon_raqam="+998901234567", parol="sec12", jinsi="erkak").full_clean()

    def test_phone_length_constraints(self):
        # 5 characters phone number is too short
        x1 = Xodim(ism="Ali", familiya="Valiyev", telefon_raqam="12345", parol="secret123", jinsi="erkak")
        with self.assertRaises(ValidationError):
            x1.full_clean()


class MijozModelTest(TestCase):
    def test_name_validations(self):
        mijoz = Mijoz(ism="Sodiq123", familiya="Karimov", jinsi="erkak", telefon_raqam_1="901234567", telefon_raqam_2="901234568")
        with self.assertRaises(ValidationError):
            mijoz.full_clean()

    def test_non_matching_phone_numbers(self):
        # Same phone numbers for primary and secondary should fail
        mijoz = Mijoz(ism="Sodiq", familiya="Karimov", jinsi="erkak", telefon_raqam_1="901234567", telefon_raqam_2="901234567")
        with self.assertRaises(ValidationError):
            mijoz.full_clean()

    def test_global_cross_column_phone_uniqueness(self):
        # Create client 1
        m1 = Mijoz.objects.create(ism="Sodiq", familiya="Karimov", jinsi="erkak", telefon_raqam_1="901234567", telefon_raqam_2="909876543")
        
        # Client 2 trying to use client 1's secondary number as their primary number should fail
        m2 = Mijoz(ism="Umid", familiya="Usmanov", jinsi="erkak", telefon_raqam_1="909876543", telefon_raqam_2="901111111")
        with self.assertRaises(ValidationError):
            m2.full_clean()


@override_settings(REST_FRAMEWORK={
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'user.authentication.ExpiringTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'temirdokon_v1.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100000/day',
        'user': '100000/day',
        'login': '100000/day',
        'phone': '100000/day',
        'password_change': '100000/day',
        'register': '100000/day'
    }
})
class UserAPISecurityTestCase(APITestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.login_url = reverse('login')
        self.xodim_list_url = reverse('xodim-list')
        self.mijoz_list_url = reverse('mijoz-list')
        
        # Create a test Biznes
        self.biznes = Biznes.objects.create(nomi="Test Biznes", egasi_ism="Owner")
        
        # Create an admin employee
        self.admin_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Adminism", familiya="Adminev", telefon_raqam="+998901111111",
            parol="adminpassword123", rol="admin", jinsi="erkak"
        )
        self.admin_token = Token.objects.create(user=self.admin_xodim.user).key
        
        # Create a cashier employee
        self.cashier_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Cashierism", familiya="Kassirev", telefon_raqam="+998902222222",
            parol="cashierpassword123", rol="sotuvchi", jinsi="ayol"
        )
        self.cashier_token = Token.objects.create(user=self.cashier_xodim.user).key

    def test_login_api_success(self):
        payload = {"telefon_raqam": "+998901111111", "parol": "adminpassword123"}
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['rol'], 'admin')

    def test_login_api_failure_inactive_employee(self):
        self.cashier_xodim.is_active = False
        self.cashier_xodim.save()
        payload = {"telefon_raqam": "+998902222222", "parol": "cashierpassword123"}
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_endpoints_require_authentication(self):
        # Accessing endpoints without Token should be rejected (401 Unauthorized)
        response = self.client.get(self.xodim_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_permissions(self):
        # Admin can view employees
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        response = self.client.get(self.xodim_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cashier_permissions(self):
        # Cashier cannot view employees (403 Forbidden)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.cashier_token)
        response = self.client.get(self.xodim_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Cashier CAN CRUD customers
        payload = {
            "ism": "Mijozbek",
            "familiya": "Xaridorov",
            "jinsi": "erkak",
            "telefon_raqam_1": "903333333",
            "telefon_raqam_2": "904444444"
        }
        response = self.client.post(self.mijoz_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_prevent_role_escalation(self):
        # Cashier tries to change their own role to admin -> should be blocked by serialization validator
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.cashier_token)
        detail_url = reverse('xodim-detail', kwargs={'pk': self.cashier_xodim.pk})
        
        # Note: Kassir cannot even hit this ViewSet because XodimViewSet permission_classes is IsAdminOrManager.
        # But let's check that if we test the serializer directly or if a cashier has access (to verify validation fallback).
        # To test the serializer validation directly, let's perform a mock serializer request or check viewset permission.
        response = self.client.patch(detail_url, {"rol": "admin"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_xodim_filters_and_search(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        
        # Search by name
        response = self.client.get(self.xodim_list_url, {'search': 'Adminism'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['ism'], "Adminism")

        # Filter by role
        response = self.client.get(self.xodim_list_url, {'rol': 'sotuvchi'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['rol'], "sotuvchi")


@override_settings(REST_FRAMEWORK={
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'user.authentication.ExpiringTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'temirdokon_v1.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100000/day',
        'user': '100000/day',
        'login': '100000/day',
        'phone': '100000/day',
        'password_change': '100000/day',
        'register': '100000/day'
    }
})
class RegisterAPITestCase(APITestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.register_url = reverse('register')

    def test_successful_registration(self):
        payload = {
            "ism": "Vali",
            "telefon_raqam": "+998901111111",
            "parol": "123456",
            "parolni_tasdiqlash": "123456"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['ism'], "Vali")
        self.assertEqual(response.data['rol'], "admin")

        # Verify Xodim and User objects are created, and business is created
        xodim = Xodim.objects.filter(telefon_raqam="+998901111111").first()
        self.assertIsNotNone(xodim)
        self.assertIsNotNone(xodim.biznes)
        self.assertEqual(xodim.biznes.nomi, "Valining Biznesi")

    def test_registration_without_password_autogenerate(self):
        payload = {
            "ism": "Ali",
            "telefon_raqam": "+998909999999"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['ism'], "Ali")

        # Verify Xodim is created and has a hashed password
        xodim = Xodim.objects.filter(telefon_raqam="+998909999999").first()
        self.assertIsNotNone(xodim)
        self.assertNotEqual(xodim.parol, "")
        self.assertTrue(xodim.user.has_usable_password()) # Dummy hash check is not needed, user.password is hashed


    def test_registration_ignores_and_prevents_admin_role_escalation(self):
        # Security: Registrations cannot specify role, role must default to 'admin' (CEO)
        payload = {
            "ism": "Hacker",
            "telefon_raqam": "+998902222222",
            "rol": "sotuvchi",
            "parol": "123456",
            "parolni_tasdiqlash": "123456"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rol'], "admin") # forced to admin

    def test_registration_unmatched_passwords(self):
        payload = {
            "ism": "Vali",
            "telefon_raqam": "+998903333333",
            "parol": "123456",
            "parolni_tasdiqlash": "654321"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parolni_tasdiqlash', response.data['errors'])

    def test_registration_validation_weak_password(self):
        payload = {
            "ism": "Vali",
            "telefon_raqam": "+998904444444",
            "parol": "123",  # Too short, no letters
            "parolni_tasdiqlash": "123"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Note: clean() validates password strength
        self.assertIn('parol', response.data['errors'])


class MultiTenantSecurityTestCase(APITestCase):
    def setUp(self):
        from user.models import Biznes, Tarif
        # Create subscription tiers
        self.tarif1 = Tarif.objects.create(nomi="Tier 1", xodim_limiti=1, dokon_limiti=1, mahsulot_limiti=5)
        self.tarif2 = Tarif.objects.create(nomi="Tier 2", xodim_limiti=5, dokon_limiti=5, mahsulot_limiti=10)

        # Create businesses
        self.biznes1 = Biznes.objects.create(nomi="Biznes 1", egasi_ism="Owner 1", tarif=self.tarif1)
        self.biznes2 = Biznes.objects.create(nomi="Biznes 2", egasi_ism="Owner 2", tarif=self.tarif2)

        # Create employees
        self.admin1 = Xodim.objects.create(
            biznes=self.biznes1, ism="Admin", familiya="One", telefon_raqam="+998901000001",
            parol="SecurePass1!", rol="admin", jinsi="erkak"
        )
        self.admin1_token = Token.objects.create(user=self.admin1.user).key

        self.admin2 = Xodim.objects.create(
            biznes=self.biznes2, ism="Admin", familiya="Two", telefon_raqam="+998901000002",
            parol="SecurePass2!", rol="admin", jinsi="erkak"
        )
        self.admin2_token = Token.objects.create(user=self.admin2.user).key

        # Create customers
        self.m1 = Mijoz.objects.create(
            biznes=self.biznes1, ism="Mijoz", familiya="Bir",
            telefon_raqam_1="+998902000001", telefon_raqam_2="+998902000002", jinsi="erkak"
        )

    def test_customer_scoped_uniqueness(self):
        # 1. Different business can use the same phone numbers
        m2 = Mijoz(
            biznes=self.biznes2, ism="Mijoz", familiya="Ikki",
            telefon_raqam_1="+998902000001", telefon_raqam_2="+998902000002", jinsi="erkak"
        )
        m2.full_clean()  # Should not raise validation error because of different business
        m2.save()
        self.assertEqual(Mijoz.objects.filter(telefon_raqam_1="+998902000001").count(), 2)

        # 2. Same business trying to register duplicate primary phone number should fail
        m3 = Mijoz(
            biznes=self.biznes1, ism="Mijoz", familiya="Uch",
            telefon_raqam_1="+998902000001", telefon_raqam_2="+998902000003", jinsi="erkak"
        )
        with self.assertRaises(ValidationError):
            m3.full_clean()

        # 3. Same business trying to register duplicate secondary phone number should fail
        m4 = Mijoz(
            biznes=self.biznes1, ism="Mijoz", familiya="To'rt",
            telefon_raqam_1="+998902000004", telefon_raqam_2="+998902000002", jinsi="erkak"
        )
        with self.assertRaises(ValidationError):
            m4.full_clean()

    def test_employee_limit_enforced(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)
        # Biznes 1 has tarif with xodim_limiti=1. It already has admin1. Creating a second employee should fail.
        payload = {
            "ism": "Kassir",
            "familiya": "Valiyev",
            "telefon_raqam": "+998905555555",
            "rol": "sotuvchi",
            "jinsi": "erkak",
            "parol": "SecurePass123!",
            "parolni_tasdiqlash": "SecurePass123!"
        }
        response = self.client.post(reverse('xodim-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limit", str(response.data['errors']['detail']))

    def test_employee_limit_allowed_under_cap(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin2_token)
        # Biznes 2 has xodim_limiti=5. Currently has admin2 (1 employee). Creating a second employee should succeed.
        payload = {
            "ism": "Kassir",
            "familiya": "Karimov",
            "telefon_raqam": "+998906666666",
            "rol": "sotuvchi",
            "jinsi": "erkak",
            "parol": "SecurePass123!",
            "parolni_tasdiqlash": "SecurePass123!"
        }
        response = self.client.post(reverse('xodim-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_views_tenant_isolation(self):
        # Admin 1 queries employee list -> should see only admin1
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)
        response = self.client.get(reverse('xodim-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.admin1.id)

        # Admin 1 queries client list -> should see only m1
        response = self.client.get(reverse('mijoz-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.m1.id)

        # Admin 2 queries client list -> should see empty list (none)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin2_token)
        response = self.client.get(reverse('mijoz-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class BiznesAPITestCase(APITestCase):
    def setUp(self):
        self.biznes_list_url = reverse('biznes-list')
        
        self.biznes1 = Biznes.objects.create(nomi="Biznes A", egasi_ism="Owner A")
        self.biznes2 = Biznes.objects.create(nomi="Biznes B", egasi_ism="Owner B")

        self.admin1 = Xodim.objects.create(
            biznes=self.biznes1,
            ism="Adminbir", familiya="Testov", telefon_raqam="+998901111111",
            parol="adminpassword123!", rol="admin", jinsi="erkak"
        )
        self.admin1_token = Token.objects.create(user=self.admin1.user).key

        # Create a superuser
        self.superuser = User.objects.create_superuser('superuser', 'super@test.com', 'superpass123!')
        self.superuser_token = Token.objects.create(user=self.superuser).key

    def test_list_businesses_for_standard_user(self):
        # Admin 1 can only see their own business details
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)
        response = self.client.get(self.biznes_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nomi'], "Biznes A")

    def test_list_businesses_for_superuser(self):
        # Superuser can see all businesses
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.superuser_token)
        response = self.client.get(self.biznes_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_business_restricted_to_superuser(self):
        # Standard user cannot create a business
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)
        payload = {"nomi": "New Biz", "egasi_ism": "New Owner"}
        response = self.client.post(self.biznes_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Superuser can create a business
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.superuser_token)
        response = self.client.post(self.biznes_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nomi'], "New Biz")

    def test_delete_business_restricted_to_superuser(self):
        # Standard user cannot delete their business
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin1_token)
        detail_url = reverse('biznes-detail', kwargs={'pk': self.biznes1.id})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Superuser can delete the business
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.superuser_token)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TarifAPITestCase(APITestCase):
    def setUp(self):
        self.tarif_list_url = reverse('tarif-list')
        
        self.tarif_free = Tarif.objects.create(nomi="Free Plan", dokon_limiti=1, mahsulot_limiti=2, xodim_limiti=1)
        self.tarif_premium = Tarif.objects.create(nomi="Premium Plan", dokon_limiti=10, mahsulot_limiti=100, xodim_limiti=10)

        self.biznes = Biznes.objects.create(nomi="My Biznes", egasi_ism="CEO", tarif=self.tarif_free)

        self.admin_xodim = Xodim.objects.create(
            biznes=self.biznes,
            ism="Adminbir", familiya="Testov", telefon_raqam="+998901111111",
            parol="adminpassword123!", rol="admin", jinsi="erkak"
        )
        self.admin_token = Token.objects.create(user=self.admin_xodim.user).key

        # Create a superuser
        self.superuser = User.objects.create_superuser('superuser', 'super@test.com', 'superpass123!')
        self.superuser_token = Token.objects.create(user=self.superuser).key

    def test_list_tariffs_for_standard_user(self):
        # Authenticated users can read/list tariffs
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        response = self.client.get(self.tarif_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_tariff_restricted_to_superuser(self):
        # Standard user cannot create a tariff
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        payload = {"nomi": "Super Plan", "dokon_limiti": 100, "mahsulot_limiti": 1000, "xodim_limiti": 50}
        response = self.client.post(self.tarif_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Superuser can create a tariff
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.superuser_token)
        response = self.client.post(self.tarif_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nomi'], "Super Plan")

    def test_employee_limit_enforced(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        payload = {
            "ism": "Ali",
            "familiya": "Valiyev",
            "telefon_raqam": "+998902222222",
            "parol": "SecurePass123!",
            "parolni_tasdiqlash": "SecurePass123!",
            "rol": "sotuvchi",
            "jinsi": "erkak"
        }
        response = self.client.post(reverse('xodim-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limiti", str(response.data['errors']['detail']))

    def test_product_limit_enforced(self):
        from products.models import Dokon
        dokon = Dokon.objects.create(biznes=self.biznes, nomi="Main Store")
        
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        payload1 = {
            "nomi": "Cement",
            "olchov_birligi": "kg",
            "kelish_narxi": "40000.00",
            "sotish_narxi": "50000.00",
            "qoldiqlar": [{"dokon": dokon.id, "miqdori": 10}]
        }
        response = self.client.post(reverse('mahsulot-list'), payload1, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        payload2 = {
            "nomi": "Sand",
            "olchov_birligi": "kg",
            "kelish_narxi": "20000.00",
            "sotish_narxi": "30000.00",
            "qoldiqlar": [{"dokon": dokon.id, "miqdori": 5}]
        }
        response = self.client.post(reverse('mahsulot-list'), payload2, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        payload3 = {
            "nomi": "Gravel",
            "olchov_birligi": "kg",
            "kelish_narxi": "30000.00",
            "sotish_narxi": "45000.00",
            "qoldiqlar": [{"dokon": dokon.id, "miqdori": 5}]
        }
        response = self.client.post(reverse('mahsulot-list'), payload3, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("limiti", str(response.data['errors']['detail']))

    def test_business_tariff_downgrade_validation(self):
        self.biznes.tarif = self.tarif_premium
        self.biznes.save()

        Xodim.objects.create(
            biznes=self.biznes,
            ism="EmployeeTwo", familiya="Testov", telefon_raqam="+998902222222",
            parol="adminpassword123!", rol="sotuvchi", jinsi="erkak"
        )
        
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)
        payload = {"tarif": self.tarif_free.id}
        detail_url = reverse('biznes-detail', kwargs={'pk': self.biznes.id})
        response = self.client.patch(detail_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("xodim", str(response.data['errors']['tarif']))


class SwaggerAPITestCase(APITestCase):
    def test_swagger_endpoints_load(self):
        response = self.client.get(reverse('schema'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get(reverse('swagger-ui'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get(reverse('redoc'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ExtraEndpointsAPITestCase(APITestCase):
    def setUp(self):
        from user.models import Biznes, Xodim
        from products.models import Mahsulot
        self.biznes = Biznes.objects.create(nomi="Test Biznes", egasi_ism="Owner")
        self.xodim = Xodim.objects.create(
            biznes=self.biznes, ism="Ali", familiya="Vali", telefon_raqam="+998901234567",
            parol="SecurePass123!", rol="admin", jinsi="erkak"
        )
        self.token = Token.objects.create(user=self.xodim.user).key
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)
        
        # Create products (one active, one archived)
        Mahsulot.objects.create(
            biznes=self.biznes, nomi="Cement", olchov_birligi="kg",
            kelish_narxi="40000.00", sotish_narxi="50000.00", toifa="Stroy", is_active=True
        )
        Mahsulot.objects.create(
            biznes=self.biznes, nomi="Brick", olchov_birligi="dona",
            kelish_narxi="1000.00", sotish_narxi="1500.00", toifa="Material", is_active=False
        )

    def test_roles_endpoint_crud(self):
        # 1. List (and auto-populate)
        response = self.client.get(reverse('roles-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['role_id'], 'admin')

        # 2. Post (Create)
        response = self.client.post(reverse('roles-list'), {"nomi": "Super Manager", "role_id": "manager"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        role_id = response.data['id']

        # 3. Put (Update)
        response = self.client.put(reverse('roles-detail', kwargs={'pk': role_id}), {"nomi": "Updated Manager", "role_id": "manager"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nomi'], "Updated Manager")

        # 4. Delete (Destroy)
        response = self.client.delete(reverse('roles-detail', kwargs={'pk': role_id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_units_endpoint_crud(self):
        # 1. List (and auto-populate)
        response = self.client.get(reverse('units-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data[0]['short_name'], 'kg')

        # 2. Post
        response = self.client.post(reverse('units-list'), {"nomi": "Tonna", "short_name": "t"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        unit_id = response.data['id']

        # 3. Delete
        response = self.client.delete(reverse('units-detail', kwargs={'pk': unit_id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_categories_endpoint_crud(self):
        # 1. List (and auto-populate from existing product categories)
        response = self.client.get(reverse('categories-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['nomi'], 'Material')
        self.assertEqual(response.data[1]['nomi'], 'Stroy')

        # 2. Post
        response = self.client.post(reverse('categories-list'), {"nomi": "Instrument"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cat_id = response.data['id']

        # 3. Delete
        response = self.client.delete(reverse('categories-detail', kwargs={'pk': cat_id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_archive_endpoint(self):
        response = self.client.get(reverse('archive-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nomi'], 'Brick')

    def test_crud_with_aliased_payloads(self):
        # Test unit creation using 'name' and 'shortName'
        payload = {"name": "Millimetr", "shortName": "mm"}
        response = self.client.post(reverse('units-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nomi'], 'Millimetr')
        self.assertEqual(response.data['short_name'], 'mm')

        # Test category creation using 'name'
        payload_cat = {"name": "Lola"}
        response = self.client.post(reverse('categories-list'), payload_cat, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nomi'], 'Lola')




