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
            'id', 'biznes', 'dokon', 'nomi', 'fayl', 'holat', 'import_turi',
            'shtrixkod_generatsiya_qilish', 'miqdori', 'kelish_summasi',
            'sotish_summasi', 'sotuvlar_taraqqiyoti', 'elementlar',
            'yaratgan_xodim', 'yaratgan_xodim_nomi', 'yakunlagan_xodim', 'yakunlagan_xodim_nomi',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = [
            'biznes', 'holat', 'miqdori', 'kelish_summasi', 'sotish_summasi',
            'sotuvlar_taraqqiyoti', 'elementlar', 'yaratgan_xodim',
            'yakunlagan_xodim', 'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            self.fields['dokon'].queryset = Dokon.objects.filter(biznes=biznes)

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
        
        temp_instance = Import(**temp_attrs)
        try:
            temp_instance.clean()
            if not instance and temp_instance.fayl:
                temp_instance.parse_and_save_elements()
                attrs['miqdori'] = temp_instance.miqdori
                attrs['kelish_summasi'] = temp_instance.kelish_summasi
                attrs['sotish_summasi'] = temp_instance.sotish_summasi
                attrs['elementlar'] = temp_instance.elementlar
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
            
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim'):
            validated_data['yaratgan_xodim'] = request.user.xodim
        return super().create(validated_data)
