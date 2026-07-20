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

    class Meta:
        model = Taminotchi
        fields = [
            'id', 'biznes', 'nomi', 'telefon', 'tel_raqami', 'telRaqami', 'telefon_raqam', 'telefonlar', 'standart_ustama',
            'eslatma', 'boshliq', 'boshliq_ismi', 'boshliqIsmi', 'boshliq_nomi', 'boshliqNomi', 'director', 'director_name', 'directorName', 'yuridik_nomi',
            'manzil', 'yuridik_manzil', 'mamlakat', 'pochta_indeksi',
            'bank_hisob_raqami', 'bank_nomi_filiali', 'inn', 'mfo', 'balans',
            'oxirgi_qarz', 'oxirgiQarz', 'jami_qarz', 'jamiQarz', 'qarz_summasi', 'buyurtmalar_summasi', 'tolovlar_summasi', 'tovarlar_soni'
        ]
        read_only_fields = ['biznes']

    def get_oxirgi_qarz(self, obj):
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

