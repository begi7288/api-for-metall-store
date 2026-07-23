import re
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, identify_hasher
from django.contrib.auth.models import User
from temirdokon_v1.models import BaseModel

# Helper function to validate names
def validate_name_letters(value, field_name):
    if not value:
        return
    # Match Uzbek names in Latin and Cyrillic script: letters, spaces, and Uzbek character apostrophes (', `, ʻ)
    if not re.match(r"^[a-zA-Zа-яА-ЯёЁ\s'`ʻ]+$", value):
        raise ValidationError({field_name: "Faqat harflardan iborat bo'lishi kerak."})


def validate_password_strength(password, field_name='parol'):
    if not password:
        return
    try:
        identify_hasher(password)
    except ValueError:
        # Allow 6-digit numeric code for SMS verification mockup
        if password.isdigit() and len(password) == 6:
            return
            
        if len(password) < 6:
            raise ValidationError({field_name: "Parol kamida 6 ta belgidan iborat bo'lishi kerak."})



class Tarif(BaseModel):
    nomi = models.CharField(max_length=255, unique=True)
    dokon_limiti = models.PositiveIntegerField(default=1)
    mahsulot_limiti = models.PositiveIntegerField(default=100)
    xodim_limiti = models.PositiveIntegerField(default=2)

    def __str__(self):
        return self.nomi


class Biznes(BaseModel):
    nomi = models.CharField(max_length=255)
    egasi_ism = models.CharField(max_length=255)
    tarif = models.ForeignKey(Tarif, on_delete=models.SET_NULL, null=True, blank=True)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    soha = models.CharField(max_length=100, blank=True, null=True)
    manzil = models.CharField(max_length=255, blank=True, null=True)
    yuridik_nomi = models.CharField(max_length=255, blank=True, null=True)
    yuridik_manzil = models.CharField(max_length=255, blank=True, null=True)
    mamlakat = models.CharField(max_length=100, blank=True, null=True)
    pochta_indeksi = models.CharField(max_length=20, blank=True, null=True)
    inn = models.CharField(max_length=20, blank=True, null=True)
    mfo = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.nomi

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            from products.models import OlchovBirligi
            from user.models import XodimRoli
            defaults_units = [
                ("Kilogramm", "kg"),
                ("Dona", "dona"),
                ("Metr", "metr"),
                ("Litr", "litr")
            ]
            for nomi, short_name in defaults_units:
                OlchovBirligi.objects.get_or_create(biznes=self, short_name=short_name, defaults={'nomi': nomi})

            defaults_roles = [
                ("Administrator", "admin"),
                ("Omborchi", "omborchi"),
                ("Sotuvchi", "sotuvchi")
            ]
            for nomi, role_id in defaults_roles:
                XodimRoli.objects.get_or_create(biznes=self, role_id=role_id, defaults={'nomi': nomi})


class Xodim(BaseModel):
    ROL_CHOICES = (
        ('admin', 'Administrator'),
        ('omborchi', 'Omborchi'),
        ('sotuvchi', 'Sotuvchi'),)
    JINS_CHOICES = (
        ('erkak', 'Erkak'),
        ('ayol', 'Ayol'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='xodim', blank=True, null=True)
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='xodimlar', null=True, blank=True)
    ism = models.CharField(max_length=100)
    familiya = models.CharField(max_length=100)
    telefon_raqam = models.CharField(max_length=13, unique=True)
    parol = models.CharField(max_length=128)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='sotuvchi')
    jinsi = models.CharField(max_length=10, choices=JINS_CHOICES)
    tugilgan_sana = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    vaqt_mintaqasi = models.CharField(max_length=50, default='Toshkent (GMT +5)', blank=True, null=True)
    avatar = models.CharField(max_length=255, blank=True, null=True)
    pin_kod = models.CharField(max_length=10, blank=True, null=True)
    til = models.CharField(max_length=20, default='O\'zbekcha', blank=True, null=True)
    mavzu = models.CharField(max_length=20, default='Yorug\'', blank=True, null=True)

    def clean(self):
        super().clean()
        
        # 1. Name format validation
        validate_name_letters(self.ism, 'ism')
        validate_name_letters(self.familiya, 'familiya')
        
        # 2. Phone number validation
        if self.telefon_raqam:
            phone = self.telefon_raqam
            has_plus = phone.startswith('+')
            if has_plus:
                phone = phone[1:]
            
            if not phone.isdigit():
                raise ValidationError({'telefon_raqam': "Telefon raqami faqat raqamlardan iborat bo'lishi kerak (ixtiyoriy '+' belgisi bilan)."})
            
            if not re.match(r"^\d{7,15}$", phone):
                raise ValidationError({'telefon_raqam': "Telefon raqami noto'g'ri formatda kiritildi."})

        # 3. Password strength validation
        validate_password_strength(self.parol)

    def save(self, *args, **kwargs):
        # validation is handled by BaseModel.save()
        raw_password = None
        if self.parol:
            try:
                identify_hasher(self.parol)
            except ValueError:
                raw_password = self.parol
                self.parol = make_password(self.parol)
                
        # Link or create standard Django User to integrate with TokenAuthentication
        if not self.user:
            username = self.telefon_raqam.replace('+', '')
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
                
            is_first = not User.objects.exists()
            django_user = User.objects.create_user(
                username=username,
                password=raw_password or self.parol,
                is_superuser=is_first,
                is_staff=is_first
            )
            self.user = django_user
        else:
            django_user = self.user
            new_username = self.telefon_raqam.replace('+', '')
            if django_user.username != new_username:
                django_user.username = new_username
            if raw_password:
                django_user.set_password(raw_password)
            django_user.is_active = self.is_active
            django_user.save()
            
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        if user:
            user.delete()

    def __str__(self):
        return f"{self.ism} {self.familiya} ({self.get_rol_display()})"


class Mijoz(BaseModel):
    JINS_CHOICES = (
        ('erkak', 'Erkak'),
        ('ayol', 'Ayol'),
    )
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='mijozlar', null=True, blank=True)
    ism = models.CharField(max_length=100)
    familiya = models.CharField(max_length=100, blank=True, null=True)
    otasining_ismi = models.CharField(max_length=100, blank=True, null=True)
    tugilgan_sana = models.DateField(blank=True, null=True)
    jinsi = models.CharField(max_length=10, choices=JINS_CHOICES)
    telefon_raqam_1 = models.CharField(max_length=13)
    telefon_raqam_2 = models.CharField(max_length=13, blank=True, null=True)
    manzil = models.CharField(max_length=255, blank=True, null=True)
    guruhlar = models.CharField(max_length=255, blank=True, null=True)
    teglar = models.CharField(max_length=255, blank=True, null=True)

    def clean(self):
        super().clean()
        
        # 1. Name format validation
        validate_name_letters(self.ism, 'ism')
        if self.familiya:
            validate_name_letters(self.familiya, 'familiya')
        if self.otasining_ismi:
            validate_name_letters(self.otasining_ismi, 'otasining_ismi')
        
        # Helper to validate phone format and length
        def validate_phone(phone, field_name):
            if not phone:
                return
            has_plus = phone.startswith('+')
            if has_plus:
                phone = phone[1:]
            
            if not phone.isdigit():
                raise ValidationError({field_name: "Telefon raqami faqat raqamlardan iborat bo'lishi kerak (ixtiyoriy '+' belgisi bilan)."})
            
            if len(phone) not in [9, 12]:
                raise ValidationError({field_name: "Telefon raqami 9 yoki 12 ta raqamdan iborat bo'lishi kerak."})
                
            if has_plus and len(phone) != 12:
                raise ValidationError({field_name: "+ bilan boshlangan telefon raqami 13 ta belgidan iborat bo'lishi kerak."})

        validate_phone(self.telefon_raqam_1, 'telefon_raqam_1')
        validate_phone(self.telefon_raqam_2, 'telefon_raqam_2')

        # 2. No matching primary and secondary numbers
        if self.telefon_raqam_1 and self.telefon_raqam_2:
            if self.telefon_raqam_1 == self.telefon_raqam_2:
                raise ValidationError({'telefon_raqam_2': "Ikkinchi telefon raqami birinchisi bilan bir xil bo'lishi mumkin emas."})
                
        # 3. Check uniqueness and cross-uniqueness within the same business across columns
        if self.telefon_raqam_1:
            qs1 = Mijoz.objects.filter(biznes=self.biznes, telefon_raqam_1=self.telefon_raqam_1)
            qs2 = Mijoz.objects.filter(biznes=self.biznes, telefon_raqam_2=self.telefon_raqam_1)
            if self.pk:
                qs1 = qs1.exclude(pk=self.pk)
                qs2 = qs2.exclude(pk=self.pk)
            if qs1.exists():
                raise ValidationError({'telefon_raqam_1': "Bu telefon raqami ushbu biznesda allaqachon boshqa mijozning birinchi raqami sifatida ro'yxatdan o'tgan."})
            if qs2.exists():
                raise ValidationError({'telefon_raqam_1': "Bu telefon raqami ushbu biznesda allaqachon boshqa mijozning ikkinchi raqami sifatida ro'yxatdan o'tgan."})
                
        if self.telefon_raqam_2:
            qs1 = Mijoz.objects.filter(biznes=self.biznes, telefon_raqam_2=self.telefon_raqam_2)
            qs2 = Mijoz.objects.filter(biznes=self.biznes, telefon_raqam_1=self.telefon_raqam_2)
            if self.pk:
                qs1 = qs1.exclude(pk=self.pk)
                qs2 = qs2.exclude(pk=self.pk)
            if qs1.exists():
                raise ValidationError({'telefon_raqam_2': "Bu telefon raqami ushbu biznesda allaqachon boshqa mijozning ikkinchi raqami sifatida ro'yxatdan o'tgan."})
            if qs2.exists():
                raise ValidationError({'telefon_raqam_2': "Bu telefon raqami ushbu biznesda allaqachon boshqa mijozning birinchi raqami sifatida ro'yxatdan o'tgan."})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ism} {self.familiya or ''}".strip()


class XodimRoli(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='xodim_rollari', null=True, blank=True)
    nomi = models.CharField(max_length=255)
    role_id = models.CharField(max_length=50)
    huquqlar = models.JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return self.nomi


from decimal import Decimal

class MijozQarzi(BaseModel):
    HOLAT_CHOICES = (
        ('tolanmagan', 'To\'lanmagan'),
        ('qisman_tolangan', 'Qisman to\'langan'),
        ('tolangan', 'To\'langan'),
        ('muddati_otgan', 'Muddati o\'tgan'),
    )
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='mijoz_qarzlari', null=True, blank=True)
    mijoz = models.ForeignKey(Mijoz, on_delete=models.CASCADE, related_name='qarzlar')
    sotuv = models.ForeignKey('sales.Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='qarz_yozuvlari')
    umumiy_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tolangan_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    qoldiq_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    holat = models.CharField(max_length=20, choices=HOLAT_CHOICES, default='tolanmagan')
    muddati = models.DateField(blank=True, null=True)
    eslatma = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.qoldiq_summa = max(Decimal('0.00'), self.umumiy_summa - self.tolangan_summa)
        if self.qoldiq_summa <= Decimal('0.00'):
            self.holat = 'tolangan'
        elif self.tolangan_summa > Decimal('0.00'):
            self.holat = 'qisman_tolangan'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.mijoz} - {self.qoldiq_summa} UZS"


class MijozTolovi(BaseModel):
    TOLOV_USULI_CHOICES = (
        ('naqd', 'Naqd'),
        ('karta', 'Karta'),
        ('aralash', 'Aralash'),
    )
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='mijoz_tolovlari', null=True, blank=True)
    mijoz = models.ForeignKey(Mijoz, on_delete=models.CASCADE, related_name='tolovlar')
    qarz = models.ForeignKey(MijozQarzi, on_delete=models.SET_NULL, null=True, blank=True, related_name='tolovlar')
    summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tolov_usuli = models.CharField(max_length=20, choices=TOLOV_USULI_CHOICES, default='naqd')
    xodim = models.ForeignKey(Xodim, on_delete=models.SET_NULL, null=True, blank=True)
    eslatma = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.mijoz} to'lovi - {self.summa} UZS"


class SodiqlikDasturi(BaseModel):
    TURI_CHOICES = (
        ('chegirma', 'Chegirma tizimi'),
        ('kashbek', 'Keshbek tizimi'),
        ('ball', 'Ballar tizimi'),
    )
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='sodiqlik_dasturi', null=True, blank=True)
    turi = models.CharField(max_length=20, choices=TURI_CHOICES, default='chegirma')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.biznes} - {self.get_turi_display()}"


class SodiqlikDarajasi(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='sodiqlik_darajalari', null=True, blank=True)
    nomi = models.CharField(max_length=100)
    xaridlar_summasi = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    chegirma = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.nomi} ({self.chegirma}%)"


class ChekSozlamalari(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='chek_sozlamalari', null=True, blank=True)
    nomi = models.CharField(max_length=100, default='Standart')
    chop_etish_turi = models.CharField(max_length=50, default='Chek')
    logotip = models.BooleanField(default=False)
    logo_icon = models.CharField(max_length=50, blank=True, null=True)
    logo_size = models.IntegerField(default=50)
    dokon_nomi_text = models.CharField(max_length=255, blank=True, null=True)
    malumot_bloki = models.BooleanField(default=False)
    malumot_bloki_options = models.JSONField(default=dict, blank=True)
    mijoz_balansi = models.BooleanField(default=False)
    mijoz_balansi_options = models.JSONField(default=dict, blank=True)
    mijoz_qarzi = models.BooleanField(default=False)
    mijoz_qarzi_options = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.biznes} Chek Sozlamalari"


class Valyuta(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='valyutalar', null=True, blank=True)
    kod = models.CharField(max_length=10)
    nomi = models.CharField(max_length=100)
    is_asosiy = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.kod} ({self.nomi})"


class TolovTuriSozlama(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='tolov_turi_sozlamalari', null=True, blank=True)
    nomi = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_asosiy = models.BooleanField(default=False)
    is_custom = models.BooleanField(default=False)

    def __str__(self):
        return self.nomi


class MahsulotSozlamalari(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='mahsulot_sozlamalari', null=True, blank=True)
    auto_generate_barcode = models.BooleanField(default=True)
    require_image = models.BooleanField(default=False)
    min_stock_alert = models.PositiveIntegerField(default=10)

    def __str__(self):
        return f"{self.biznes} Mahsulot Sozlamalari"


class BildirishnomaSozlamalari(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='bildirishnoma_sozlamalari', null=True, blank=True)
    matrix = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.biznes} Bildirishnoma Sozlamalari"


class Ilova(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='ilovalar', null=True, blank=True)
    kod = models.CharField(max_length=50)
    nomi = models.CharField(max_length=100)
    is_connected = models.BooleanField(default=False)
    status_text = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.nomi} ({'Ulangan' if self.is_connected else 'Ulanmagan'})"