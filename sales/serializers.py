from rest_framework import serializers
from decimal import Decimal
from django.db import transaction, models
from .models import Sale, SaleItem
from user.serializers import XSSSanitizerMixin

class SaleItemSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    nomi = serializers.CharField(source='mahsulot.nomi', read_only=True)
    shtrix_kod = serializers.SerializerMethodField(read_only=True)
    kelish_narxi = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    sotish_narxi = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    jami_summa = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            'id', 'mahsulot', 'nomi', 'shtrix_kod', 'miqdori', 'kelish_narxi', 'sotish_narxi', 'is_ulgurji', 'jami_summa'
        ]

    def get_shtrix_kod(self, obj):
        return obj.mahsulot.shtrix_kodlar.first().kod if obj.mahsulot.shtrix_kodlar.exists() else None


class SaleSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    elementlar = SaleItemSerializer(many=True)
    xodim_nomi = serializers.SerializerMethodField(read_only=True)
    dokon_nomi = serializers.CharField(source='dokon.nomi', read_only=True)
    mijoz_nomi = serializers.SerializerMethodField(read_only=True)

    oraliq_jami = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    chegirma_summasi = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    yakuniy_summa = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    nasiya_summa = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = Sale
        fields = [
            'id', 'biznes', 'dokon', 'dokon_nomi', 'mijoz', 'mijoz_nomi', 'xodim', 'xodim_nomi',
            'kod', 'holat', 'oraliq_jami', 'chegirma_turi', 'chegirma_qiymati', 'chegirma_summasi',
            'yakuniy_summa', 'tolangan_summa', 'nasiya_summa', 'tolov_usuli', 'eslatma',
            'elementlar', 'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'xodim', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def get_xodim_nomi(self, obj):
        return f"{obj.xodim.ism} {obj.xodim.familiya}" if obj.xodim else ""

    def get_mijoz_nomi(self, obj):
        return f"{obj.mijoz.ism} {obj.mijoz.familiya}" if obj.mijoz else "Anonim Mijoz"

    def validate(self, attrs):
        # If creating or updating status to completed
        holat = attrs.get('holat', self.instance.holat if self.instance else 'yakunlangan')
        elementlar_data = attrs.get('elementlar', [])
        dokon = attrs.get('dokon', self.instance.dokon if self.instance else None)
        
        if holat == 'yakunlangan':
            # Check stock for each item
            for item_data in elementlar_data:
                mahsulot = item_data['mahsulot']
                miqdori = item_data['miqdori']
                
                # Check DokonQoldiq
                if dokon:
                    from products.models import DokonQoldiq
                    qoldiq = DokonQoldiq.objects.filter(mahsulot=mahsulot, dokon=dokon).first()
                    current_qty = qoldiq.miqdori if qoldiq else 0
                    
                    # If updating, add back the old qty of this product in this sale to current_qty to see if there is enough
                    if self.instance and self.instance.holat == 'yakunlangan':
                        old_item = self.instance.elementlar.filter(mahsulot=mahsulot).first()
                        if old_item:
                            current_qty += old_item.miqdori
                            
                    if current_qty < miqdori:
                        raise serializers.ValidationError(
                            {'elementlar': f"'{mahsulot.nomi}' uchun do'konda yetarli qoldiq mavjud emas (Mavjud: {current_qty}, So'ralgan: {miqdori})."}
                        )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        elementlar_data = validated_data.pop('elementlar', [])
        
        # Auto-populate xodim and biznes from request user
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim'):
            xodim = request.user.xodim
            validated_data['xodim'] = xodim
            validated_data['biznes'] = xodim.biznes

        sale = Sale.objects.create(**validated_data)
        
        for item_data in elementlar_data:
            mahsulot = item_data['mahsulot']
            miqdori = item_data['miqdori']
            is_ulgurji = item_data.get('is_ulgurji', False)
            
            # Auto-populate prices from product
            kelish_narxi = mahsulot.kelish_narxi or Decimal('0.00')
            sotish_narxi = mahsulot.ulgurji_narx if is_ulgurji else mahsulot.sotish_narxi
            if not sotish_narxi:
                sotish_narxi = Decimal('0.00')
            
            SaleItem.objects.create(
                sotuv=sale,
                mahsulot=mahsulot,
                miqdori=miqdori,
                kelish_narxi=kelish_narxi,
                sotish_narxi=sotish_narxi,
                is_ulgurji=is_ulgurji
            )
            
            # Deduct stock if completed
            if sale.holat == 'yakunlangan':
                from products.models import DokonQoldiq
                qoldiq = DokonQoldiq.objects.filter(mahsulot=mahsulot, dokon=sale.dokon).first()
                if qoldiq:
                    qoldiq.miqdori -= miqdori
                    qoldiq.save()
                
                # Update total qty
                mahsulot.miqdori = sum(q.miqdori for q in mahsulot.qoldiqlar.all())
                mahsulot.save(update_fields=['miqdori'])
                
        # Trigger recalculation of parent totals
        sale.oraliq_jami = sale.elementlar.aggregate(total=models.Sum('jami_summa'))['total'] or Decimal('0.00')
        sale.save()
        return sale

    @transaction.atomic
    def update(self, instance, validated_data):
        elementlar_data = validated_data.pop('elementlar', None)
        
        # If status changes from kechiktirilgan to yakunlangan, we must deduct stock!
        old_holat = instance.holat
        new_holat = validated_data.get('holat', old_holat)
        
        # First, standard fields update
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if elementlar_data is not None:
            # If cart items are updated, let's restore stock of old items if they were completed
            if old_holat == 'yakunlangan':
                for old_item in instance.elementlar.all():
                    from products.models import DokonQoldiq
                    qoldiq, created = DokonQoldiq.objects.get_or_create(mahsulot=old_item.mahsulot, dokon=instance.dokon)
                    qoldiq.miqdori += old_item.miqdori
                    qoldiq.save()
                    old_item.mahsulot.miqdori = sum(q.miqdori for q in old_item.mahsulot.qoldiqlar.all())
                    old_item.mahsulot.save(update_fields=['miqdori'])
            
            # Delete old items
            instance.elementlar.all().delete()
            
            # Create new items
            for item_data in elementlar_data:
                mahsulot = item_data['mahsulot']
                miqdori = item_data['miqdori']
                is_ulgurji = item_data.get('is_ulgurji', False)
                
                # Auto-populate prices
                kelish_narxi = mahsulot.kelish_narxi or Decimal('0.00')
                sotish_narxi = mahsulot.ulgurji_narx if is_ulgurji else mahsulot.sotish_narxi
                if not sotish_narxi:
                    sotish_narxi = Decimal('0.00')
                
                SaleItem.objects.create(
                    sotuv=instance,
                    mahsulot=mahsulot,
                    miqdori=miqdori,
                    kelish_narxi=kelish_narxi,
                    sotish_narxi=sotish_narxi,
                    is_ulgurji=is_ulgurji
                )
                
                # Deduct stock if new status is completed
                if new_holat == 'yakunlangan':
                    from products.models import DokonQoldiq
                    qoldiq = DokonQoldiq.objects.filter(mahsulot=mahsulot, dokon=instance.dokon).first()
                    if qoldiq:
                        qoldiq.miqdori -= miqdori
                        qoldiq.save()
                    
                    mahsulot.miqdori = sum(q.miqdori for q in mahsulot.qoldiqlar.all())
                    mahsulot.save(update_fields=['miqdori'])
        else:
            # If only status changed from kechiktirilgan to yakunlangan (without editing items list)
            if old_holat == 'kechiktirilgan' and new_holat == 'yakunlangan':
                for item in instance.elementlar.all():
                    from products.models import DokonQoldiq
                    qoldiq = DokonQoldiq.objects.filter(mahsulot=item.mahsulot, dokon=instance.dokon).first()
                    if qoldiq:
                        qoldiq.miqdori -= item.miqdori
                        qoldiq.save()
                    
                    item.mahsulot.miqdori = sum(q.miqdori for q in item.mahsulot.qoldiqlar.all())
                    item.mahsulot.save(update_fields=['miqdori'])
                    
        # Trigger recalculation of parent totals
        instance.oraliq_jami = instance.elementlar.aggregate(total=models.Sum('jami_summa'))['total'] or Decimal('0.00')
        instance.save()
        return instance


class XarajatKategoriyasiSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    name = serializers.CharField(source='nomi', required=False)

    class Meta:
        from .models import XarajatKategoriyasi
        model = XarajatKategoriyasi
        fields = ['id', 'biznes', 'nomi', 'name', 'tavsif', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']


class XarajatSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    kategoriya_nomi = serializers.CharField(source='kategoriya.nomi', read_only=True)
    category_name = serializers.CharField(source='kategoriya.nomi', read_only=True)
    taminotchi_nomi = serializers.CharField(source='taminotchi.nomi', read_only=True)
    amount = serializers.DecimalField(source='miqdor', max_digits=15, decimal_places=2, required=False)
    date = serializers.DateField(source='sana', required=False)
    payment_type = serializers.CharField(source='tolov_turi', required=False)
    note = serializers.CharField(source='izoh', required=False, allow_blank=True)

    class Meta:
        from .models import Xarajat
        model = Xarajat
        fields = [
            'id', 'biznes', 'kategoriya', 'kategoriya_nomi', 'category_name',
            'taminotchi', 'taminotchi_nomi', 'miqdor', 'amount', 'tolov_turi', 'payment_type',
            'sana', 'date', 'izoh', 'note', 'xodim', 'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'xodim', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def validate(self, attrs):
        if 'sana' not in attrs or attrs['sana'] is None:
            from django.utils import timezone
            attrs['sana'] = timezone.now().date()
        return attrs
