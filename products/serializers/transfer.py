from rest_framework import serializers
from django.core.exceptions import ValidationError
from products.models import Transfer, Dokon
from user.serializers import XSSSanitizerMixin

class TransferSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    dokondan_nomi = serializers.SerializerMethodField()
    dokonga_nomi = serializers.SerializerMethodField()
    yaratgan_xodim_nomi = serializers.SerializerMethodField()
    qabul_qilgan_xodim_nomi = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = [
            'id', 'biznes', 'nomi', 'dokondan', 'dokondan_nomi', 'dokonga', 'dokonga_nomi',
            'fayl', 'holat', 'miqdori', 'summa', 'elementlar',
            'yaratgan_xodim', 'yaratgan_xodim_nomi', 'qabul_qilgan_xodim', 'qabul_qilgan_xodim_nomi',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = [
            'biznes', 'holat', 'miqdori', 'summa', 'yaratgan_xodim', 'qabul_qilgan_xodim',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            self.fields['dokondan'].queryset = Dokon.objects.filter(biznes=biznes)
            self.fields['dokonga'].queryset = Dokon.objects.filter(biznes=biznes)

    def get_dokondan_nomi(self, obj):
        return obj.dokondan.nomi if obj.dokondan else ""

    def get_dokonga_nomi(self, obj):
        return obj.dokonga.nomi if obj.dokonga else ""

    def get_yaratgan_xodim_nomi(self, obj):
        if obj.yaratgan_xodim:
            return f"{obj.yaratgan_xodim.ism} {obj.yaratgan_xodim.familiya}"
        return "Tizim administratori"

    def get_qabul_qilgan_xodim_nomi(self, obj):
        if obj.qabul_qilgan_xodim:
            return f"{obj.qabul_qilgan_xodim.ism} {obj.qabul_qilgan_xodim.familiya}"
        return "Tizim administratori"

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            dokondan = attrs.get('dokondan')
            dokonga = attrs.get('dokonga')
            if dokondan and dokondan.biznes != biznes:
                raise serializers.ValidationError({"dokondan": "Yuboruvchi do'kon sizning kompaniyangizga tegishli emas."})
            if dokonga and dokonga.biznes != biznes:
                raise serializers.ValidationError({"dokonga": "Qabul qiluvchi do'kon sizning kompaniyangizga tegishli emas."})

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

        temp_instance = Transfer(**temp_attrs)
        
        try:
            temp_instance.clean()
            if not instance and temp_instance.fayl:
                temp_instance.parse_and_save_elements()
                attrs['miqdori'] = temp_instance.miqdori
                attrs['elementlar'] = temp_instance.elementlar
            elif not instance and not temp_instance.fayl:
                if 'elementlar' in attrs:
                    attrs['miqdori'] = temp_instance.miqdori
                    attrs['elementlar'] = temp_instance.elementlar
                else:
                    raise serializers.ValidationError({'elementlar': "Fayl kiritilmaganda elementlar kiritilishi shart."})
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim'):
            validated_data['yaratgan_xodim'] = request.user.xodim
        return super().create(validated_data)
