from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError
from temirdokon_v1.models import BaseModel
from user.models import Biznes, Xodim, Mijoz
from products.models import Dokon, Mahsulot

class Sale(BaseModel):
    HOLAT_CHOICES = (
        ('yakunlangan', 'Yakunlangan'),
        ('kechiktirilgan', 'Kechiktirilgan'),
    )
    TOLOV_USULI_CHOICES = (
        ('naqd', 'Naqd'),
        ('karta', 'Karta'),
        ('nasiya', 'Nasiya'),
        ('aralash', 'Aralash'),
    )
    CHEGIRMA_TURI_CHOICES = (
        ('foiz', 'Foiz'),
        ('summa', 'Summa'),
    )

    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='sotuvlar', null=True, blank=True)
    dokon = models.ForeignKey(Dokon, on_delete=models.PROTECT, related_name='sotuvlar')
    mijoz = models.ForeignKey(Mijoz, on_delete=models.SET_NULL, null=True, blank=True, related_name='sotuvlar')
    xodim = models.ForeignKey(Xodim, on_delete=models.PROTECT, related_name='sotuvlar')
    
    kod = models.CharField(max_length=100, unique=True)
    holat = models.CharField(max_length=20, choices=HOLAT_CHOICES, default='yakunlangan')
    
    oraliq_jami = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    chegirma_turi = models.CharField(max_length=10, choices=CHEGIRMA_TURI_CHOICES, default='foiz')
    chegirma_qiymati = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    chegirma_summasi = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    yakuniy_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    tolangan_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    nasiya_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tolov_usuli = models.CharField(max_length=20, choices=TOLOV_USULI_CHOICES, default='naqd')
    eslatma = models.TextField(blank=True, null=True)

    def clean(self):
        super().clean()
        if self.biznes:
            if self.dokon and self.dokon.biznes != self.biznes:
                raise ValidationError({'dokon': "Do'kon sizning biznesingizga tegishli emas."})
            if self.mijoz and self.mijoz.biznes != self.biznes:
                raise ValidationError({'mijoz': "Mijoz sizning biznesingizga tegishli emas."})
            if self.xodim and self.xodim.biznes != self.biznes:
                raise ValidationError({'xodim': "Xodim sizning biznesingizga tegishli emas."})

        if self.tolangan_summa < 0:
            raise ValidationError({'tolangan_summa': "To'langan summa manfiy bo'lishi mumkin emas."})
        if self.chegirma_qiymati < 0:
            raise ValidationError({'chegirma_qiymati': "Chegirma qiymati manfiy bo'lishi mumkin emas."})

        # Nasiya / aralash nasiya uchun mijoz shart
        has_nasiya = False
        if self.tolov_usuli == 'nasiya':
            has_nasiya = True
        elif self.tolov_usuli == 'aralash' and self.eslatma:
            import re
            cleaned_eslatma = re.sub(r'\s+', '', self.eslatma)
            nasiya_match = re.search(r'(?:Nasiya|Qarz|Credit)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
            p_nasiya = Decimal(nasiya_match.group(1)) if nasiya_match else Decimal('0.00')
            if p_nasiya > 0:
                has_nasiya = True

        if has_nasiya and not self.mijoz:
            raise ValidationError({'mijoz': "Nasiya (qarz)ga sotish uchun mijoz tanlanishi shart."})

    def save(self, *args, **kwargs):
        self.clean()
        
        # Calculate discount sum
        if self.chegirma_turi == 'foiz':
            self.chegirma_summasi = (self.oraliq_jami * (self.chegirma_qiymati / Decimal('100.00'))).quantize(Decimal('0.01'))
        else:
            self.chegirma_summasi = self.chegirma_qiymati
            
        self.yakuniy_summa = max(Decimal('0.00'), self.oraliq_jami - self.chegirma_summasi)
        if self.tolov_usuli == 'nasiya':
            self.tolangan_summa = Decimal('0.00')
            self.nasiya_summa = self.yakuniy_summa
        elif self.tolov_usuli == 'aralash' and self.eslatma:
            import re
            cleaned_eslatma = re.sub(r'\s+', '', self.eslatma)
            naqd_match = re.search(r'(?:Naqd|Cash)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
            karta_match = re.search(r'(?:Plastikkarta|Plastik|Karta|Card|Uzcard|Humo)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
            nasiya_match = re.search(r'(?:Nasiya|Qarz|Credit)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
            
            p_naqd = Decimal(naqd_match.group(1)) if naqd_match else Decimal('0.00')
            p_karta = Decimal(karta_match.group(1)) if karta_match else Decimal('0.00')
            p_nasiya = Decimal(nasiya_match.group(1)) if nasiya_match else Decimal('0.00')
            
            if p_naqd > 0 or p_karta > 0 or p_nasiya > 0:
                self.tolangan_summa = p_naqd + p_karta
                self.nasiya_summa = p_nasiya
            else:
                self.nasiya_summa = max(Decimal('0.00'), self.yakuniy_summa - self.tolangan_summa)
        else:
            self.nasiya_summa = max(Decimal('0.00'), self.yakuniy_summa - self.tolangan_summa)
        
        super().save(*args, **kwargs)

        # Nasiyaga sotilgan bo'lsa (yoki tolov_usuli='nasiya') va mijoz bo'lsa -> MijozQarzi yaratish/yangilash
        if (self.nasiya_summa > Decimal('0.00') or self.tolov_usuli == 'nasiya') and self.mijoz:
            from user.models import MijozQarzi
            debt_amount = self.nasiya_summa if self.nasiya_summa > Decimal('0.00') else self.yakuniy_summa
            qarz, created = MijozQarzi.objects.get_or_create(
                sotuv=self,
                defaults={
                    'biznes': self.biznes,
                    'mijoz': self.mijoz,
                    'umumiy_summa': debt_amount,
                    'tolangan_summa': Decimal('0.00'),
                    'qoldiq_summa': debt_amount,
                    'holat': 'tolanmagan'
                }
            )
            if not created:
                qarz.biznes = self.biznes
                qarz.mijoz = self.mijoz
                qarz.umumiy_summa = debt_amount
                qarz.save()

    def __str__(self):
        return f"Sotuv #{self.kod} ({self.get_holat_display()})"

    def delete(self, *args, **kwargs):
        if self.holat == 'yakunlangan':
            for item in self.elementlar.all():
                from products.models import DokonQoldiq
                qoldiq, created = DokonQoldiq.objects.get_or_create(mahsulot=item.mahsulot, dokon=self.dokon)
                qoldiq.miqdori += item.miqdori
                qoldiq.save()
                item.mahsulot.miqdori = sum(q.miqdori for q in item.mahsulot.qoldiqlar.all())
                item.mahsulot.save(update_fields=['miqdori'])
        super().delete(*args, **kwargs)


class SaleItem(BaseModel):
    sotuv = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='elementlar')
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.PROTECT, related_name='sotuv_elementlari')
    miqdori = models.PositiveIntegerField()
    kelish_narxi = models.DecimalField(max_digits=12, decimal_places=2)
    sotish_narxi = models.DecimalField(max_digits=12, decimal_places=2)
    is_ulgurji = models.BooleanField(default=False)
    jami_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    def clean(self):
        super().clean()
        if self.miqdori is not None and self.miqdori <= 0:
            raise ValidationError({'miqdori': "Sotiladigan miqdor 0 dan katta bo'lishi shart."})
        if self.sotuv and self.sotuv.biznes and self.mahsulot.biznes != self.sotuv.biznes:
            raise ValidationError({'mahsulot': "Mahsulot sizning biznesingizga tegishli emas."})

    def save(self, *args, **kwargs):
        self.clean()
        self.jami_summa = (self.sotish_narxi * Decimal(self.miqdori)).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
        self.recalculate_parent_totals()

    def delete(self, *args, **kwargs):
        sotuv = self.sotuv
        super().delete(*args, **kwargs)
        sotuv.oraliq_jami = sotuv.elementlar.aggregate(total=models.Sum('jami_summa'))['total'] or Decimal('0.00')
        sotuv.save()

    def recalculate_parent_totals(self):
        sotuv = self.sotuv
        sotuv.oraliq_jami = sotuv.elementlar.aggregate(total=models.Sum('jami_summa'))['total'] or Decimal('0.00')
        sotuv.save()

    def __str__(self):
        return f"{self.mahsulot.nomi} x{self.miqdori}"


class XarajatKategoriyasi(BaseModel):
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='xarajat_kategoriyalari', null=True, blank=True)
    nomi = models.CharField(max_length=100)
    tavsif = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nomi


class Xarajat(BaseModel):
    TOLOV_TURI_CHOICES = (
        ('naqd', 'Naqd'),
        ('karta', 'Karta'),
        ('nasiya', 'Nasiya'),
        ('aralash', 'Aralash'),
    )

    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='xarajatlar', null=True, blank=True)
    kategoriya = models.ForeignKey(XarajatKategoriyasi, on_delete=models.SET_NULL, null=True, blank=True, related_name='xarajatlar')
    taminotchi = models.ForeignKey('products.Taminotchi', on_delete=models.SET_NULL, null=True, blank=True, related_name='xarajatlar')
    miqdor = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tolov_turi = models.CharField(max_length=20, choices=TOLOV_TURI_CHOICES, default='naqd')
    sana = models.DateField(null=True, blank=True)
    izoh = models.TextField(blank=True, null=True)
    xodim = models.ForeignKey(Xodim, on_delete=models.SET_NULL, null=True, blank=True, related_name='xarajatlar')

    def __str__(self):
        return f"{self.kategoriya.nomi if self.kategoriya else 'Xarajat'}: {self.miqdor} so'm"
