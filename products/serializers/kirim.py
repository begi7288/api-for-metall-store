from rest_framework import serializers
from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from ..models import Import, Dokon, Taminotchi, Mahsulot
from user.models import Xodim

class KirimElementSerializer(serializers.Serializer):
    mahsulot_id = serializers.IntegerField(required=False, allow_null=True)
    nomi = serializers.CharField(max_length=255)
    toifa = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    brend = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    birlik = serializers.CharField(max_length=50, required=False, default='dona')
    olchov_birligi = serializers.CharField(max_length=50, required=False, default='dona')
    narxi = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=Decimal('0.00'))
    kelish_narxi = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=Decimal('0.00'))
    sotish_narxi = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=Decimal('0.00'))
    soni = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=Decimal('0.00'))
    miqdori = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=Decimal('0.00'))
    shtrix_kod = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    characteristics = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class KirimSerializer(serializers.ModelSerializer):
    dokon_nomi = serializers.SerializerMethodField(read_only=True)
    taminotchi_nomi = serializers.SerializerMethodField(read_only=True)
    yaratgan_xodim_nomi = serializers.SerializerMethodField(read_only=True)
    yakunlagan_xodim_nomi = serializers.SerializerMethodField(read_only=True)
    sana = serializers.DateTimeField(source='yaratilgan_vaqt', read_only=True)
    auto_confirm = serializers.BooleanField(write_only=True, required=False, default=True)

    class Meta:
        model = Import
        fields = [
            'id',
            'biznes',
            'dokon',
            'dokon_nomi',
            'taminotchi',
            'taminotchi_nomi',
            'tolov_turi',
            'chek_raqami',
            'nomi',
            'fayl',
            'holat',
            'import_turi',
            'shtrixkod_generatsiya_qilish',
            'miqdori',
            'kelish_summasi',
            'sotish_summasi',
            'elementlar',
            'yaratgan_xodim',
            'yaratgan_xodim_nomi',
            'yakunlagan_xodim',
            'yakunlagan_xodim_nomi',
            'sana',
            'auto_confirm',
            'yaratilgan_vaqt',
            'yangilangan_vaqt',
        ]
        read_only_fields = [
            'id',
            'biznes',
            'dokon_nomi',
            'taminotchi_nomi',
            'chek_raqami',
            'miqdori',
            'kelish_summasi',
            'sotish_summasi',
            'yaratgan_xodim',
            'yaratgan_xodim_nomi',
            'yakunlagan_xodim',
            'yakunlagan_xodim_nomi',
            'sana',
            'yaratilgan_vaqt',
            'yangilangan_vaqt',
        ]

    def get_dokon_nomi(self, obj):
        return obj.dokon.nomi if obj.dokon else None

    def get_taminotchi_nomi(self, obj):
        return obj.taminotchi.nomi if obj.taminotchi else None

    def get_yaratgan_xodim_nomi(self, obj):
        if obj.yaratgan_xodim:
            user = obj.yaratgan_xodim.user
            full = f"{user.first_name} {user.last_name}".strip()
            return full if full else user.username
        return None

    def get_yakunlagan_xodim_nomi(self, obj):
        if obj.yakunlagan_xodim:
            user = obj.yakunlagan_xodim.user
            full = f"{user.first_name} {user.last_name}".strip()
            return full if full else user.username
        return None

    def validate_elementlar(self, value):
        if not value or not isinstance(value, list):
            raise DRFValidationError("Kirim qilish uchun kamida bitta mahsulot kiritilishi shart.")
        
        normalized_elements = []
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                raise DRFValidationError(f"{index}-qatordagi mahsulot ma'lumotlari to'g'ri emas.")
            
            nomi = item.get('nomi') or item.get('name')
            if not nomi:
                raise DRFValidationError(f"{index}-qatorda mahsulot nomi kiritilmagan.")

            miqdori = item.get('miqdori') if item.get('miqdori') is not None else item.get('soni', 0)
            try:
                miqdori_val = float(miqdori)
            except (ValueError, TypeError):
                miqdori_val = 0.0

            if miqdori_val <= 0:
                raise DRFValidationError(f"{index}-qatordagi mahsulot miqdori 0 dan katta bo'lishi shart.")

            kelish_narxi = item.get('kelish_narxi') if item.get('kelish_narxi') is not None else item.get('narxi', 0.0)
            try:
                kelish_val = float(kelish_narxi)
            except (ValueError, TypeError):
                kelish_val = 0.0

            sotish_narxi = item.get('sotish_narxi', 0.0)
            try:
                sotish_val = float(sotish_narxi)
            except (ValueError, TypeError):
                sotish_val = 0.0

            birlik = item.get('olchov_birligi') or item.get('birlik', 'dona')

            normalized_item = {
                'nomi': str(nomi).strip(),
                'toifa': item.get('toifa') or item.get('kategoriya'),
                'brend': item.get('brend'),
                'olchov_birligi': str(birlik).strip(),
                'miqdori': miqdori_val,
                'kelish_narxi': kelish_val,
                'sotish_narxi': sotish_val,
                'shtrix_kod': item.get('shtrix_kod') or item.get('barcode'),
                'characteristics': item.get('characteristics', [])
            }
            normalized_elements.append(normalized_item)

        return normalized_elements

    def create(self, validated_data):
        auto_confirm = validated_data.pop('auto_confirm', True)
        elementlar = validated_data.get('elementlar', [])
        
        total_qty = sum(int(item.get('miqdori', 0)) for item in elementlar)
        total_kelish = sum(Decimal(str(item.get('miqdori', 0))) * Decimal(str(item.get('kelish_narxi', 0.0))) for item in elementlar)
        total_sotish = sum(Decimal(str(item.get('miqdori', 0))) * Decimal(str(item.get('sotish_narxi', 0.0))) for item in elementlar)

        validated_data['import_turi'] = 'kirim'
        validated_data['miqdori'] = total_qty
        validated_data['kelish_summasi'] = total_kelish
        validated_data['sotish_summasi'] = total_sotish

        if not validated_data.get('nomi'):
            validated_data['nomi'] = f"Omborga kirim"

        kirim_obj = super().create(validated_data)

        if auto_confirm and kirim_obj.holat == 'kutilmoqda':
            executor_xodim = validated_data.get('yaratgan_xodim')
            kirim_obj.confirm_and_execute(executor_xodim=executor_xodim)
            kirim_obj.refresh_from_db()

        return kirim_obj
