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

    def __str__(self):
        return self.nomi


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
            
            if not re.match(r"^(998)?\d{9}$", phone):
                raise ValidationError({'telefon_raqam': "Telefon raqami noto'g'ri formatda kiritildi."})
                
            if has_plus and len(phone) != 12:
                raise ValidationError({'telefon_raqam': "+ bilan boshlangan telefon raqami 13 ta belgidan iborat bo'lishi kerak."})

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
                
            django_user = User.objects.create_user(
                username=username,
                password=raw_password or self.parol
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
    familiya = models.CharField(max_length=100)
    otasining_ismi = models.CharField(max_length=100, blank=True, null=True)
    tugilgan_sana = models.DateField(blank=True, null=True)
    jinsi = models.CharField(max_length=10, choices=JINS_CHOICES)
    telefon_raqam_1 = models.CharField(max_length=13)
    telefon_raqam_2 = models.CharField(max_length=13)

    def clean(self):
        super().clean()
        
        # 1. Name format validation
        validate_name_letters(self.ism, 'ism')
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
        return f"{self.ism} {self.familiya}"


class XodimRoli(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='xodim_rollari', null=True, blank=True)
    nomi = models.CharField(max_length=255)
    role_id = models.CharField(max_length=50)
    huquqlar = models.JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return self.nomi