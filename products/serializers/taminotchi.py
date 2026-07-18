from rest_framework import serializers
from decimal import Decimal
from products.models import Taminotchi
from user.serializers import XSSSanitizerMixin

class TaminotchiSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    qarz_summasi = serializers.SerializerMethodField()
    buyurtmalar_summasi = serializers.SerializerMethodField()
    tolovlar_summasi = serializers.SerializerMethodField()
    tovarlar_soni = serializers.SerializerMethodField()

    class Meta:
        model = Taminotchi
        fields = [
            'id', 'biznes', 'nomi', 'telefon_raqam', 'telefonlar', 'standart_ustama',
            'eslatma', 'yuridik_nomi', 'yuridik_manzil', 'mamlakat', 'pochta_indeksi',
            'bank_hisob_raqami', 'bank_nomi_filiali', 'inn', 'mfo', 'balans',
            'qarz_summasi', 'buyurtmalar_summasi', 'tolovlar_summasi', 'tovarlar_soni'
        ]
        read_only_fields = ['biznes']

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
