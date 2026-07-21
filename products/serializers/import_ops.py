from rest_framework import serializers
from django.core.exceptions import ValidationError
from products.models import Import, Dokon
from user.serializers import XSSSanitizerMixin

class ImportSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    yaratgan_xodim_nomi = serializers.SerializerMethodField()
    yakunlagan_xodim_nomi = serializers.SerializerMethodField()

    class Meta:
        model = Import
        fields = [
            'id', 'biznes', 'dokon', 'taminotchi', 'tolov_turi', 'chek_raqami', 'column_mapping', 'nomi', 'fayl', 'holat', 'import_turi',
            'shtrixkod_generatsiya_qilish', 'miqdori', 'kelish_summasi',
            'sotish_summasi', 'sotuvlar_taraqqiyoti', 'elementlar',
            'yaratgan_xodim', 'yaratgan_xodim_nomi', 'yakunlagan_xodim', 'yakunlagan_xodim_nomi',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = [
            'biznes', 'chek_raqami', 'holat', 'miqdori', 'kelish_summasi', 'sotish_summasi',
            'sotuvlar_taraqqiyoti', 'yaratgan_xodim',
            'yakunlagan_xodim', 'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            self.fields['dokon'].queryset = Dokon.objects.filter(biznes=biznes)
            from products.models import Taminotchi
            self.fields['taminotchi'].queryset = Taminotchi.objects.filter(biznes=biznes)

    def get_yaratgan_xodim_nomi(self, obj):
        if obj.yaratgan_xodim:
            return f"{obj.yaratgan_xodim.ism} {obj.yaratgan_xodim.familiya}"
        return "Tizim administratori"

    def get_yakunlagan_xodim_nomi(self, obj):
        if obj.yakunlagan_xodim:
            return f"{obj.yakunlagan_xodim.ism} {obj.yakunlagan_xodim.familiya}"
        return "Tizim administratori"

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            dokon_obj = attrs.get('dokon')
            if dokon_obj and dokon_obj.biznes != biznes:
                raise serializers.ValidationError({"dokon": "Tanlangan do'kon sizning kompaniyangizga tegishli emas."})
            taminotchi_obj = attrs.get('taminotchi')
            if taminotchi_obj and taminotchi_obj.biznes != biznes:
                raise serializers.ValidationError({"taminotchi": "Tanlangan yetkazib beruvchi sizning kompaniyangizga tegishli emas."})

        instance = self.instance
        temp_attrs = {}
        if instance:
            for field in self.Meta.fields:
                if hasattr(instance, field):
                    temp_attrs[field] = getattr(instance, field)
        temp_attrs.update(attrs)
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            temp_attrs['biznes'] = request.user.xodim.biznes
        temp_attrs.pop('id', None)
        
        fayl = attrs.get('fayl') or (instance.fayl if instance else None)
        elementlar = attrs.get('elementlar') or (instance.elementlar if instance else None)
        
        if not fayl and not elementlar:
            raise serializers.ValidationError({"detail": "Fayl yuklanishi yoki tovarlar kiritilishi shart."})

        from decimal import Decimal
        if fayl:
            temp_instance = Import(**temp_attrs)
            try:
                temp_instance.clean()
                if not instance:
                    temp_instance.parse_and_save_elements()
                    attrs['miqdori'] = temp_instance.miqdori
                    attrs['kelish_summasi'] = temp_instance.kelish_summasi
                    attrs['sotish_summasi'] = temp_instance.sotish_summasi
                    attrs['elementlar'] = temp_instance.elementlar
            except ValidationError as e:
                raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
        else:
            if not elementlar:
                raise serializers.ValidationError({"elementlar": "Tovar elementlari ro'yxati kiritilishi shart."})
            if not isinstance(elementlar, list):
                raise serializers.ValidationError({"elementlar": "Elementlar ro'yxat (list) bo'lishi shart."})
            
            total_qty = 0
            total_kelish = Decimal('0.00')
            total_sotish = Decimal('0.00')
            validated_elements = []
            
            for idx, item in enumerate(elementlar, start=1):
                if not isinstance(item, dict):
                    raise serializers.ValidationError({"elementlar": f"Element {idx} to'g'ri formatda emas."})
                
                nomi = item.get('nomi')
                shtrix_kod = item.get('shtrix_kod')
                if not nomi and not shtrix_kod:
                    raise serializers.ValidationError({"elementlar": f"Element {idx}: nomi yoki shtrix_kod kiritilishi shart."})
                
                qty = item.get('miqdori', 0)
                try:
                    qty = int(qty)
                except (ValueError, TypeError):
                    raise serializers.ValidationError({"elementlar": f"Element {idx}: miqdori butun son bo'lishi shart."})
                
                if qty <= 0:
                    raise serializers.ValidationError({"elementlar": f"Element {idx}: miqdori 0 dan katta bo'lishi shart."})
                
                cost = Decimal(str(item.get('kelish_narxi', 0.0)))
                sell = Decimal(str(item.get('sotish_narxi', 0.0)))
                
                total_qty += qty
                total_kelish += cost * qty
                total_sotish += sell * qty
                
                validated_elements.append({
                    'nomi': nomi or "",
                    'shtrix_kod': shtrix_kod or "",
                    'miqdori': qty,
                    'kelish_narxi': str(cost),
                    'sotish_narxi': str(sell),
                    'olchov_birligi': item.get('olchov_birligi', 'dona'),
                    'toifa': item.get('toifa', 'Mavjud emas'),
                    'brend': item.get('brend', 'Mavjud emas'),
                    'taminotchi_nomi': item.get('taminotchi_nomi'),
                    'tavsif': item.get('tavsif', ''),
                    'characteristics': item.get('characteristics', [])
                })
                
            attrs['miqdori'] = total_qty
            attrs['kelish_summasi'] = total_kelish
            attrs['sotish_summasi'] = total_sotish
            attrs['elementlar'] = validated_elements
            
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim'):
            validated_data['yaratgan_xodim'] = request.user.xodim
        return super().create(validated_data)
