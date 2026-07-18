from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from user.models import Biznes, Xodim, BaseModel
from products.models import Dokon, Mahsulot, DokonQoldiq, Taminotchi

class SupplierOrder(BaseModel):
    HOLAT_CHOICES = (
        ('qoralama', 'Qoralama'),
        ('rasmiylashtirilgan', 'Rasmiylashtirilgan'),
        ('qabul_qilingan', 'Qabul qilingan'),
        ('bekor_qilingan', 'Bekor qilingan'),
    )

    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='xarid_buyurtmalari', null=True, blank=True)
    taminotchi = models.ForeignKey(Taminotchi, on_delete=models.PROTECT, related_name='xarid_buyurtmalari')
    dokon = models.ForeignKey(Dokon, on_delete=models.PROTECT, related_name='xarid_buyurtmalari')
    nomi = models.CharField(max_length=255)
    holat = models.CharField(max_length=30, choices=HOLAT_CHOICES, default='qoralama')
    qabul_qilish_sanasi = models.DateField()
    haqiqiy_qabul_sana = models.DateTimeField(null=True, blank=True)
    
    yaratgan_xodim = models.ForeignKey(Xodim, on_delete=models.SET_NULL, null=True, blank=True, related_name='yaratgan_xarid_buyurtmalari')
    qabul_qilgan_xodim = models.ForeignKey(Xodim, on_delete=models.SET_NULL, null=True, blank=True, related_name='qabul_qilgan_xarid_buyurtmalari')
    
    umumiy_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))  # cost sum
    sotuv_summasi = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))  # retail sum
    tolangan_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    nasiya_summa = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    sotuvlar_taraqqiyoti = models.FloatField(default=0.0)
    fayl = models.FileField(upload_to='supplier_orders/', null=True, blank=True)

    def clean(self):
        if self.biznes:
            if self.dokon and self.dokon.biznes != self.biznes:
                raise ValidationError("Do'kon sizning% kompaniyangizga tegishli emas.")
        if self.tolangan_summa > self.umumiy_summa:
            raise ValidationError("To'langan summa buyurtma summasidan oshib keta olmaydi.")
            
    def save(self, *args, **kwargs):
        self.nasiya_summa = max(Decimal('0.00'), self.umumiy_summa - self.tolangan_summa)
        super().save(*args, **kwargs)

    def rasmiylashtirish(self):
        if self.holat != 'qoralama':
            raise ValidationError("Faqat qoralama buyurtmalarni rasmiylashtirish mumkin.")
        if not self.elementlar.exists():
            raise ValidationError("Buyurtmada kamida bitta mahsulot bo'lishi shart.")
        self.holat = 'rasmiylashtirilgan'
        self.save()

    def add_payment(self, amount, tolov_turi, employee):
        if self.holat not in ['rasmiylashtirilgan', 'qabul_qilingan']:
            raise ValidationError("Faqat rasmiylashtirilgan yoki qabul qilingan buyurtmalarga to'lov qilish mumkin.")
        if amount <= 0:
            raise ValidationError("To'lov summasi noldan katta bo'lishi kerak.")
        if amount > self.nasiya_summa:
            raise ValidationError("To'lov summasi qolgan qarzdorlikdan oshib keta olmaydi.")

        if tolov_turi == 'balans_postavshika':
            if self.taminotchi.balans < amount:
                raise ValidationError("Yetkazib beruvchi balansi yetarli emas.")
            self.taminotchi.balans -= amount
            self.taminotchi.save()

        SupplierOrderPayment.objects.create(
            order=self,
            tolangan_summa=amount,
            tolov_turi=tolov_turi,
            xodim=employee
        )

        self.tolangan_summa += amount
        self.save()

    def get_price_differences(self):
        differences = []
        for item in self.elementlar.all():
            product = item.mahsulot
            if item.sotish_narxi != product.sotish_narxi:
                differences.append({
                    "id": item.id,
                    "nomi": product.nomi,
                    "buyurtma_narxi": item.sotish_narxi,
                    "dokondagi_narx": product.sotish_narxi,
                    "shtrix_kod": product.shtrix_kodlar.first().kod if product.shtrix_kodlar.exists() else None,
                    "toifa": "Mavjud emas" if not product.sotish_narxi else "Farqli"
                })
        return differences

    def qabul_qilish(self, apply_new_prices, executor_employee):
        if self.holat != 'rasmiylashtirilgan':
            raise ValidationError("Faqat rasmiylashtirilgan buyurtmalarni qabul qilish mumkin.")
            
        for item in self.elementlar.all():
            product = item.mahsulot
            if apply_new_prices:
                product.sotish_narxi = item.sotish_narxi
                product.kelish_narxi = item.kelish_narxi
                product.ulgurji_narx = item.ulgurji_narx
                product.ustama = item.ustama
                product.save()

            qoldiq, created = DokonQoldiq.objects.get_or_create(
                mahsulot=product,
                dokon=self.dokon,
                defaults={"miqdori": 0, "ogohlantirish": 2}
            )
            qoldiq.miqdori += item.miqdori
            qoldiq.save()

            total_stock = DokonQoldiq.objects.filter(mahsulot=product).aggregate(models.Sum('miqdori'))['miqdori__sum'] or 0
            product.miqdori = total_stock
            product.save(update_fields=['miqdori'])

        self.holat = 'qabul_qilingan'
        self.haqiqiy_qabul_sana = now()
        self.qabul_qilgan_xodim = executor_employee
        self.save()

    def bekor_qilish(self):
        if self.holat == 'qabul_qilingan':
            raise ValidationError("Qabul qilingan buyurtmalarni bekor qilib bo'lmaydi.")
        if self.holat == 'bekor_qilingan':
            raise ValidationError("Ushbu buyurtma allaqachon bekor qilingan.")
            
        if self.tolangan_summa > 0:
            for payment in self.to_lovlar.all():
                if payment.tolov_turi == 'balans_postavshika':
                    self.taminotchi.balans += payment.tolangan_summa
                    self.taminotchi.save()
            self.tolangan_summa = Decimal('0.00')

        self.holat = 'bekor_qilingan'
        self.save()

class SupplierOrderItem(BaseModel):
    order = models.ForeignKey(SupplierOrder, on_delete=models.CASCADE, related_name='elementlar')
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.PROTECT, related_name='xarid_elementlari')
    miqdori = models.PositiveIntegerField()
    kelish_narxi = models.DecimalField(max_digits=12, decimal_places=2)
    ustama = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    sotish_narxi = models.DecimalField(max_digits=12, decimal_places=2)
    ulgurji_narx = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def clean(self):
        if self.miqdori is not None and self.miqdori <= 0:
            raise ValidationError("Buyurtma miqdori 0 dan katta bo'lishi kerak.")
        if self.order and self.order.biznes and self.mahsulot.biznes != self.order.biznes:
            raise ValidationError("Tanlangan mahsulot buyurtma biznesiga tegishli emas.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        self.order.umumiy_summa = self.order.elementlar.aggregate(total=models.Sum(models.F('miqdori') * models.F('kelish_narxi')))['total'] or Decimal('0.00')
        self.order.sotuv_summasi = self.order.elementlar.aggregate(total=models.Sum(models.F('miqdori') * models.F('sotish_narxi')))['total'] or Decimal('0.00')
        self.order.save()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.umumiy_summa = order.elementlar.aggregate(total=models.Sum(models.F('miqdori') * models.F('kelish_narxi')))['total'] or Decimal('0.00')
        order.sotuv_summasi = order.elementlar.aggregate(total=models.Sum(models.F('miqdori') * models.F('sotish_narxi')))['total'] or Decimal('0.00')
        order.save()

class SupplierOrderPayment(BaseModel):
    TURI_CHOICES = (
        ('naqd', 'Naqd'),
        ('karta', 'Karta'),
        ('uzcard', 'UzCard'),
        ('humo', 'HUMO'),
        ('visa', 'VISA'),
        ('mastercard', 'Mastercard'),
        ('unionpay', 'UnionPay'),
        ('ingenico', 'Ingenico'),
        ('balans_postavshika', 'Yetkazib beruvchi balansi'),
    )

    order = models.ForeignKey(SupplierOrder, on_delete=models.CASCADE, related_name='to_lovlar')
    tolangan_summa = models.DecimalField(max_digits=15, decimal_places=2)
    tolov_turi = models.CharField(max_length=30, choices=TURI_CHOICES)
    xodim = models.ForeignKey(Xodim, on_delete=models.PROTECT, related_name='supplier_tolovlari')

    def __str__(self):
        return f"{self.tolangan_summa} - {self.tolov_turi}"

class SupplierOrderReturn(BaseModel):
    HOLAT_CHOICES = (
        ('kutilmoqda', 'Kutilmoqda'),
        ('yakunlangan', 'Yakunlangan'),
        ('bekor_qilingan', 'Bekor qilingan'),
    )
    biznes = models.ForeignKey(Biznes, on_delete=models.CASCADE, related_name='xarid_qaytarishlari', null=True, blank=True)
    order = models.ForeignKey(SupplierOrder, on_delete=models.CASCADE, related_name='qaytarishlar')
    dokon = models.ForeignKey(Dokon, on_delete=models.PROTECT, related_name='xarid_qaytarishlari')
    taminotchi = models.ForeignKey(Taminotchi, on_delete=models.PROTECT, related_name='xarid_qaytarishlari')
    holat = models.CharField(max_length=30, choices=HOLAT_CHOICES, default='kutilmoqda')
    qaytarish_summasi = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    miqdori = models.PositiveIntegerField(default=0)

    def execute_return(self):
        if self.holat != 'kutilmoqda':
            raise ValidationError("Faqat kutilayotgan qaytarishlarni yakunlash mumkin.")
            
        for item in self.elementlar.all():
            qoldiq = DokonQoldiq.objects.get(mahsulot=item.mahsulot, dokon=self.dokon)
            if qoldiq.miqdori < item.miqdori:
                raise ValidationError(f"{item.mahsulot.nomi} uchun do'konda yetarli qoldiq yo'q.")
            qoldiq.miqdori -= item.miqdori
            qoldiq.save()

            total_stock = DokonQoldiq.objects.filter(mahsulot=item.mahsulot).aggregate(models.Sum('miqdori'))['miqdori__sum'] or 0
            item.mahsulot.miqdori = total_stock
            item.mahsulot.save(update_fields=['miqdori'])

        self.taminotchi.balans += self.qaytarish_summasi
        self.taminotchi.save()

        self.holat = 'yakunlangan'
        self.save()

class SupplierOrderReturnItem(BaseModel):
    return_obj = models.ForeignKey(SupplierOrderReturn, on_delete=models.CASCADE, related_name='elementlar')
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.PROTECT, related_name='xarid_qaytarish_elementlari')
    miqdori = models.PositiveIntegerField()
    kelish_narxi = models.DecimalField(max_digits=12, decimal_places=2)

    def clean(self):
        if self.miqdori is not None and self.miqdori <= 0:
            raise ValidationError("Qaytariladigan mahsulot miqdori 0 dan katta bo'lishi kerak.")
        if self.return_obj and self.return_obj.biznes and self.mahsulot.biznes != self.return_obj.biznes:
            raise ValidationError("Tanlangan mahsulot sizning kompaniyangizga tegishli emas.")
        try:
            qoldiq = DokonQoldiq.objects.get(mahsulot=self.mahsulot, dokon=self.return_obj.dokon)
            if qoldiq.miqdori < self.miqdori:
                raise ValidationError(f"Qaytarish uchun do'konda yetarli mahsulot yo'q. Ombordagi qoldiq: {qoldiq.miqdori}")
        except DokonQoldiq.DoesNotExist:
            raise ValidationError("Ushbu mahsulot do'kon qoldiqlarida mavjud emas.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        self.return_obj.qaytarish_summasi = self.return_obj.elementlar.aggregate(total=models.Sum(models.F('miqdori') * models.F('kelish_narxi')))['total'] or Decimal('0.00')
        self.return_obj.miqdori = self.return_obj.elementlar.aggregate(total=models.Sum(models.F('miqdori')))['total'] or 0
        self.return_obj.save()
