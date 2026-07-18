from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from products.models import Mahsulot, Characteristic, MahsulotRasm, MahsulotShtrixKod

class MahsulotModelTest(TestCase):
    def test_product_characteristics(self):
        char1 = Characteristic.objects.create(name="Rang", value="Qizil")
        char2 = Characteristic.objects.create(name="Material", value="Temir")
        
        product = Mahsulot.objects.create(
            nomi="Truba",
            olchov_birligi="metr",
            kelish_narxi=Decimal("15000.00"),
            ustama=Decimal("10.00"),
            miqdori=20
        )
        
        product.characteristics.add(char1, char2)
        
        self.assertEqual(product.characteristics.count(), 2)
        self.assertIn(char1, product.characteristics.all())
        self.assertIn(char2, product.characteristics.all())

    def test_auto_calculate_sotish_narxi(self):
        product = Mahsulot(
            nomi="Gips",
            olchov_birligi="kg",
            kelish_narxi=Decimal("100.00"),
            ustama=Decimal("20.00"),
            miqdori=5,
            ogohlantirish=2
        )
        product.save()
        self.assertEqual(product.sotish_narxi, Decimal("120.00"))
        self.assertIsNotNone(product.shtrix_kod)
        self.assertEqual(len(product.shtrix_kod), 13)

    def test_auto_calculate_ustama(self):
        product = Mahsulot(
            nomi="Tsement",
            olchov_birligi="kg",
            kelish_narxi=Decimal("100.00"),
            sotish_narxi=Decimal("125.00"),
            miqdori=5
        )
        product.save()
        self.assertEqual(product.ustama, Decimal("25.00"))

    def test_selling_at_a_loss_validation(self):
        product = Mahsulot(
            nomi="Lopata",
            olchov_birligi="dona",
            kelish_narxi=Decimal("100.00"),
            sotish_narxi=Decimal("90.00")
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_invalid_barcode_validation(self):
        product = Mahsulot.objects.create(
            nomi="Vedro",
            olchov_birligi="dona",
            kelish_narxi=Decimal("50.00"),
            ustama=Decimal("10.00"),
            miqdori=5
        )
        invalid_bc = MahsulotShtrixKod(mahsulot=product, kod="abc123xyz")
        with self.assertRaises(ValidationError):
            invalid_bc.full_clean()

    def test_negative_values_validation(self):
        product = Mahsulot(
            nomi="Shlang",
            olchov_birligi="metr",
            kelish_narxi=Decimal("-10.00"),
            ustama=Decimal("10.00")
        )
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_image_size_validation(self):
        large_file = SimpleUploadedFile("large_image.jpg", b"x" * (6 * 1024 * 1024))
        product = Mahsulot.objects.create(
            nomi="Gips",
            olchov_birligi="kg",
            kelish_narxi=Decimal("100.00"),
            ustama=Decimal("20.00"),
            miqdori=5
        )
        prod_image = MahsulotRasm(mahsulot=product, rasm=large_file)
        with self.assertRaises(ValidationError):
            prod_image.full_clean()
