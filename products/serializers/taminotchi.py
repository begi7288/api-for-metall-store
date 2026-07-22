from rest_framework import serializers
from decimal import Decimal
from products.models import Taminotchi
from user.serializers import XSSSanitizerMixin

class TaminotchiSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    boshliq = serializers.CharField(source='yuridik_nomi', required=False, allow_null=True, allow_blank=True)
    boshliq_ismi = serializers.CharField(source='yuridik_nomi', required=False, allow_null=True, allow_blank=True)
    boshliqIsmi = serializers.CharField(source='yuridik_nomi', required=False, allow_null=True, allow_blank=True)
    boshliq_nomi = serializers.CharField(source='yuridik_nomi', required=False, allow_null=True, allow_blank=True)
    boshliqNomi = serializers.CharField(source='yuridik_nomi', required=False, allow_null=True, allow_blank=True)
    director = serializers.CharField(source='yuridik_nomi', required=False, allow_null=True, allow_blank=True)
    director_name = serializers.CharField(source='yuridik_nomi', required=False, allow_null=True, allow_blank=True)
    directorName = serializers.CharField(source='yuridik_nomi', required=False, allow_null=True, allow_blank=True)
    manzil = serializers.CharField(source='yuridik_manzil', required=False, allow_null=True, allow_blank=True)
    telefon = serializers.CharField(source='telefon_raqam', required=False, allow_null=True, allow_blank=True)
    tel_raqami = serializers.CharField(source='telefon_raqam', required=False, allow_null=True, allow_blank=True)
    telRaqami = serializers.CharField(source='telefon_raqam', required=False, allow_null=True, allow_blank=True)
    oxirgi_qarz = serializers.SerializerMethodField()
    oxirgiQarz = serializers.SerializerMethodField()
    jami_qarz = serializers.SerializerMethodField()
    jamiQarz = serializers.SerializerMethodField()
    qarz_summasi = serializers.SerializerMethodField()
    buyurtmalar_summasi = serializers.SerializerMethodField()
    tolovlar_summasi = serializers.SerializerMethodField()
    tovarlar_soni = serializers.SerializerMethodField()

    dastlabki_qarz = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, write_only=True)
    dastlabkiQarz = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, write_only=True)

    class Meta:
        model = Taminotchi
        fields = [
            'id', 'biznes', 'nomi', 'telefon', 'tel_raqami', 'telRaqami', 'telefon_raqam', 'telefonlar', 'standart_ustama',
            'eslatma', 'boshliq', 'boshliq_ismi', 'boshliqIsmi', 'boshliq_nomi', 'boshliqNomi', 'director', 'director_name', 'directorName', 'yuridik_nomi',
            'manzil', 'yuridik_manzil', 'mamlakat', 'pochta_indeksi',
            'bank_hisob_raqami', 'bank_nomi_filiali', 'inn', 'mfo', 'balans',
            'oxirgi_qarz', 'oxirgiQarz', 'jami_qarz', 'jamiQarz', 'qarz_summasi', 'buyurtmalar_summasi', 'tolovlar_summasi', 'tovarlar_soni',
            'dastlabki_qarz', 'dastlabkiQarz'
        ]
        read_only_fields = ['biznes']

    def get_oxirgi_qarz(self, obj):
        last_unpaid = obj.xarid_buyurtmalari.exclude(holat='bekor_qilingan').filter(nasiya_summa__gt=0).order_by('-yaratilgan_vaqt').first()
        if last_unpaid:
            return last_unpaid.nasiya_summa
        last_order = obj.xarid_buyurtmalari.exclude(holat='bekor_qilingan').order_by('-yaratilgan_vaqt').first()
        if last_order:
            return last_order.nasiya_summa
        return Decimal('0.00')

    def get_oxirgiQarz(self, obj):
        return self.get_oxirgi_qarz(obj)

    def get_jami_qarz(self, obj):
        return self.get_qarz_summasi(obj)

    def get_jamiQarz(self, obj):
        return self.get_jami_qarz(obj)

    def get_qarz_summasi(self, obj):
        from django.db.models import Sum
        return obj.xarid_buyurtmalari.exclude(holat='bekor_qilingan').aggregate(total=Sum('nasiya_summa'))['total'] or Decimal('0.00')

    def get_buyurtmalar_summasi(self, obj):
        from django.db.models import Sum
        return obj.xarid_buyurtmalari.exclude(holat='bekor_qilingan').aggregate(total=Sum('umumiy_summa'))['total'] or Decimal('0.00')

    def get_tolovlar_summasi(self, obj):
        from django.db.models import Sum
        return obj.xarid_buyurtmalari.exclude(holat='bekor_qilingan').aggregate(total=Sum('tolangan_summa'))['total'] or Decimal('0.00')

    def get_tovarlar_soni(self, obj):
        from django.db.models import Sum
        return obj.xarid_buyurtmalari.exclude(holat='bekor_qilingan').aggregate(total=Sum('elementlar__miqdori'))['total'] or 0

    def to_internal_value(self, data):
        def clean_val(val):
            if val is None:
                return None
            if isinstance(val, str):
                val = val.replace(' ', '').replace(',', '').strip()
                if not val or val.lower() in ('null', 'undefined'):
                    return None
            try:
                return str(Decimal(str(val)))
            except Exception:
                return None

        val_oxirgi = clean_val(data.get('oxirgi_qarz') or data.get('oxirgiQarz'))
        val_jami = clean_val(data.get('jami_qarz') or data.get('jamiQarz') or data.get('qarz_summasi') or data.get('qarzSummasi'))
        
        target_val = val_oxirgi or val_jami
        
        if target_val is not None and not data.get('dastlabki_qarz') and not data.get('dastlabkiQarz'):
            if hasattr(data, 'copy'):
                data = data.copy()
            else:
                data = dict(data)
            data['dastlabki_qarz'] = target_val
            
        return super().to_internal_value(data)

    def create(self, validated_data):
        dastlabki_qarz = validated_data.pop('dastlabki_qarz', None)
        dastlabki_qarz_camel = validated_data.pop('dastlabkiQarz', None)
        
        initial_debt = dastlabki_qarz or dastlabki_qarz_camel or Decimal('0.00')
        
        taminotchi = super().create(validated_data)
        
        if initial_debt > Decimal('0.00'):
            from orders.models import SupplierOrder
            from products.models import Dokon
            from django.utils.timezone import now
            
            dokon = Dokon.objects.filter(biznes=taminotchi.biznes).first() if taminotchi.biznes else None
            if not dokon and taminotchi.biznes:
                dokon = Dokon.objects.create(biznes=taminotchi.biznes, nomi="Asosiy do'kon")
            
            if dokon:
                SupplierOrder.objects.create(
                    biznes=taminotchi.biznes,
                    taminotchi=taminotchi,
                    dokon=dokon,
                    nomi="Dastlabki qarz",
                    holat='rasmiylashtirilgan',
                    qabul_qilish_sanasi=now().date(),
                    umumiy_summa=initial_debt,
                    nasiya_summa=initial_debt
                )
            taminotchi.refresh_from_db()
        return taminotchi

    def update(self, instance, validated_data):
        dastlabki_qarz = validated_data.pop('dastlabki_qarz', None)
        dastlabki_qarz_camel = validated_data.pop('dastlabkiQarz', None)
        initial_debt = dastlabki_qarz or dastlabki_qarz_camel
        
        taminotchi = super().update(instance, validated_data)
        
        if initial_debt is not None:
            try:
                initial_debt_decimal = Decimal(str(initial_debt))
            except Exception:
                initial_debt_decimal = Decimal('0.00')
            from orders.models import SupplierOrder
            from products.models import Dokon
            from django.utils.timezone import now
            
            dastlabki_order = instance.xarid_buyurtmalari.filter(nomi="Dastlabki qarz").first()
            if dastlabki_order:
                dastlabki_order.umumiy_summa = initial_debt_decimal
                dastlabki_order.nasiya_summa = max(Decimal('0.00'), initial_debt_decimal - dastlabki_order.tolangan_summa)
                dastlabki_order.save()
            elif initial_debt_decimal > Decimal('0.00'):
                dokon = Dokon.objects.filter(biznes=taminotchi.biznes).first() if taminotchi.biznes else None
                if not dokon and taminotchi.biznes:
                    dokon = Dokon.objects.create(biznes=taminotchi.biznes, nomi="Asosiy do'kon")
                if dokon:
                    SupplierOrder.objects.create(
                        biznes=taminotchi.biznes,
                        taminotchi=taminotchi,
                        dokon=dokon,
                        nomi="Dastlabki qarz",
                        holat='rasmiylashtirilgan',
                        qabul_qilish_sanasi=now().date(),
                        umumiy_summa=initial_debt_decimal,
                        nasiya_summa=initial_debt_decimal
                    )
            taminotchi.refresh_from_db()
        return taminotchi

