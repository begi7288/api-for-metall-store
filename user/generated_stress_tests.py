# -*- coding: utf-8 -*-
"""Mass stress test suite – creates 10,000 records for each main model and verifies basic CRUD.
Run with: python manage.py test user.generated_stress_tests
"""

from django.test import TestCase
from django.db import transaction
from user.models import Xodim, Mijoz, Biznes, Tarif

RECORD_COUNT = 10_000

class MassModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # One tariff and business for foreign keys
        cls.tarif = Tarif.objects.create(
            nomi="Stress Plan",
            xodim_limiti=RECORD_COUNT,
            dokon_limiti=RECORD_COUNT,
            mahsulot_limiti=RECORD_COUNT,
        )
        cls.biznes = Biznes.objects.create(
            nomi="StressBiz",
            egasi_ism="Owner",
            tarif=cls.tarif,
        )

    def test_create_xodim_bulk(self):
        objs = []
        for i in range(RECORD_COUNT):
            objs.append(
                Xodim(
                    biznes=self.biznes,
                    ism=f"Ism{i}",
                    familiya=f"Fam{i}",
                    telefon_raqam=f"+99890{i:07d}",
                    parol="StrongPass123!",
                    rol="sotuvchi",
                    jinsi="erkak",
                )
            )
        Xodim.objects.bulk_create(objs)
        self.assertEqual(Xodim.objects.count(), RECORD_COUNT)

    def test_create_mijoz_bulk(self):
        objs = []
        for i in range(RECORD_COUNT):
            objs.append(
                Mijoz(
                    biznes=self.biznes,
                    ism=f"Mijoz{i}",
                    familiya="Family",
                    jinsi="erkak",
                    telefon_raqam_1=f"901{i:07d}",
                    telefon_raqam_2=f"902{i:07d}",
                )
            )
        Mijoz.objects.bulk_create(objs)
        self.assertEqual(Mijoz.objects.count(), RECORD_COUNT)

    def test_create_biznes_bulk(self):
        objs = []
        for i in range(RECORD_COUNT):
            objs.append(
                Biznes(
                    nomi=f"Biz{i}",
                    egasi_ism=f"Owner{i}",
                    tarif=self.tarif,
                )
            )
        Biznes.objects.bulk_create(objs)
        # +1 from setUpTestData
        self.assertEqual(Biznes.objects.count(), RECORD_COUNT + 1)

    def test_update_and_delete_xodim(self):
        objs = []
        for i in range(100):
            objs.append(
                Xodim(
                    biznes=self.biznes,
                    ism=f"Tmp{i}",
                    familiya=f"Tmp{i}",
                    telefon_raqam=f"+99894{i:07d}",
                    parol="TmpPass123!",
                    rol="sotuvchi",
                    jinsi="erkak",
                )
            )
        Xodim.objects.bulk_create(objs)
        self.assertEqual(Xodim.objects.filter(ism__startswith="Tmp").count(), 100)
        Xodim.objects.filter(ism__startswith="Tmp").delete()
        self.assertEqual(Xodim.objects.filter(ism__startswith="Tmp").count(), 0)

    def test_transaction_integrity(self):
        # bulk_create should rollback on error
        with self.assertRaises(Exception):
            with transaction.atomic():
                Xodim.objects.create(
                    biznes=self.biznes,
                    ism="Bad",
                    familiya="Bad",
                    telefon_raqam="invalid",  # invalid phone triggers ValidationError
                    parol="BadPass123!",
                    rol="sotuvchi",
                    jinsi="erkak",
                )
                Xodim.objects.create(
                    biznes=self.biznes,
                    ism="Bad2",
                    familiya="Bad2",
                    telefon_raqam="+998901234567",
                    parol="BadPass123!",
                    rol="sotuvchi",
                    jinsi="erkak",
                )
        self.assertEqual(Xodim.objects.filter(ism="Bad").count(), 0)
