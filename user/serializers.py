import html
import re
from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import Xodim, Mijoz, validate_password_strength, Biznes, Tarif

def sanitize_input(value):
    if not isinstance(value, str):
        return value
    # Strip HTML tags
    clean_val = re.sub(r'<[^>]*>', '', value)
    # Escape HTML entities
    return html.escape(clean_val).strip()

class XSSSanitizerMixin:
    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        for key, value in ret.items():
            if isinstance(value, str):
                ret[key] = sanitize_input(value)
        return ret

class XodimSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    parol = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    parolni_tasdiqlash = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = Xodim
        fields = [
            'id', 'biznes', 'ism', 'familiya', 'telefon_raqam', 'parol', 'parolni_tasdiqlash',
            'rol', 'jinsi', 'tugilgan_sana', 'is_active',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def validate(self, attrs):
        # 1. Prevent role escalation (non-admin/non-omborchi cannot change rol or is_active)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            is_admin_or_omborchi = False
            try:
                is_admin_or_omborchi = request.user.xodim.rol in ['admin', 'omborchi']
            except AttributeError:
                pass
                
            if self.instance and not is_admin_or_omborchi:
                if 'rol' in attrs and attrs['rol'] != self.instance.rol:
                    raise serializers.ValidationError({'rol': "Faqat administrator yoki omborchi rolni o'zgartira oladi."})
                if 'is_active' in attrs and attrs['is_active'] != self.instance.is_active:
                    raise serializers.ValidationError({'is_active': "Faqat administrator yoki omborchi faollik holatini o'zgartira oladi."})

        parol = attrs.get('parol')
        parolni_tasdiqlash = attrs.get('parolni_tasdiqlash')
        
        # 2. Validation for password matching
        if not self.instance:  # Creation
            if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
                biznes = request.user.xodim.biznes
                if biznes.tarif:
                    limit = biznes.tarif.xodim_limiti
                    if Xodim.objects.filter(biznes=biznes).count() >= limit:
                        raise serializers.ValidationError({"detail": f"Tarif rejangiz bo'yicha xodimlar soni limiti ({limit}) tugagan. Iltimos tarifingizni yangilang."})
            
            if not parol:
                raise serializers.ValidationError({'parol': "Parol kiritilishi shart."})
            if not parolni_tasdiqlash:
                raise serializers.ValidationError({'parolni_tasdiqlash': "Parolni tasdiqlash kiritilishi shart."})
        
        if parol:
            if parol != parolni_tasdiqlash:
                raise serializers.ValidationError({'parolni_tasdiqlash': "Parollar bir-biriga mos kelmadi."})
                
        # Pop it now so it is not passed to the model constructor
        attrs.pop('parolni_tasdiqlash', None)

        # 3. Run model validation rules (including phone format & password strength checks)
        instance = self.instance
        temp_attrs = {}
        if instance:
            for field in self.Meta.fields:
                if field != 'parolni_tasdiqlash' and hasattr(instance, field):
                    temp_attrs[field] = getattr(instance, field)
        
        temp_attrs.update(attrs)
        temp_attrs.pop('id', None)
        
        temp_instance = Xodim(**temp_attrs)
        try:
            temp_instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
            
        return attrs


class MijozSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    class Meta:
        model = Mijoz
        fields = [
            'id', 'biznes', 'ism', 'familiya', 'otasining_ismi', 'tugilgan_sana',
            'jinsi', 'telefon_raqam_1', 'telefon_raqam_2',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def validate(self, attrs):
        instance = self.instance
        temp_attrs = {}
        if instance:
            for field in self.Meta.fields:
                if hasattr(instance, field):
                    temp_attrs[field] = getattr(instance, field)
        
        temp_attrs.update(attrs)
        temp_attrs.pop('id', None)
        
        temp_instance = Mijoz(**temp_attrs)
        try:
            temp_instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
            
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    eski_parol = serializers.CharField(required=True, style={'input_type': 'password'})
    yangi_parol = serializers.CharField(required=True, style={'input_type': 'password'})
    yangi_parol_tasdiqlash = serializers.CharField(required=True, style={'input_type': 'password'})

    def validate_eski_parol(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Eski parol noto'g'ri.")
        return value

    def validate(self, attrs):
        yangi_parol = attrs.get('yangi_parol')
        yangi_parol_tasdiqlash = attrs.get('yangi_parol_tasdiqlash')

        if yangi_parol != yangi_parol_tasdiqlash:
            raise serializers.ValidationError({'yangi_parol_tasdiqlash': "Yangi parollar bir-biriga mos kelmadi."})

        # Centralized password strength validation rules
        try:
            validate_password_strength(yangi_parol, field_name='yangi_parol')
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)

        return attrs

class LoginSerializer(serializers.Serializer):
    telefon_raqam = serializers.CharField(required=True, label="Telefon raqami")
    parol = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        label="Parol"
    )


class LogoutSerializer(serializers.Serializer):
    pass


class RegisterSerializer(serializers.ModelSerializer):
    parol = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    parolni_tasdiqlash = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    biznes_nomi = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Xodim
        fields = [
            'id', 'ism', 'telefon_raqam', 'parol', 'parolni_tasdiqlash', 'biznes_nomi'
        ]

    def validate(self, attrs):
        # 1. Sanitize text fields to prevent XSS
        if 'ism' in attrs:
            attrs['ism'] = sanitize_input(attrs['ism'])
        if 'biznes_nomi' in attrs:
            attrs['biznes_nomi'] = sanitize_input(attrs['biznes_nomi'])

        # 2. Check if phone number is already registered
        telefon_raqam = attrs.get('telefon_raqam')
        if telefon_raqam and Xodim.objects.filter(telefon_raqam=telefon_raqam).exists():
            raise serializers.ValidationError({'telefon_raqam': "Ushbu telefon raqami allaqachon ro'yxatdan o'tkazilgan."})

        parol = attrs.get('parol')
        parolni_tasdiqlash = attrs.get('parolni_tasdiqlash')

        if parol != parolni_tasdiqlash:
            raise serializers.ValidationError({'parolni_tasdiqlash': "Parollar bir-biriga mos kelmadi."})

        attrs.pop('parolni_tasdiqlash', None)

        # Build temp instance with default values to run model validations
        temp_attrs = attrs.copy()
        temp_attrs.pop('id', None)
        temp_attrs.pop('biznes_nomi', None)
        temp_attrs['familiya'] = 'Foydalanuvchi'
        temp_attrs['rol'] = 'admin'
        temp_attrs['jinsi'] = 'erkak'
        
        temp_instance = Xodim(**temp_attrs)
        try:
            temp_instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)

        return attrs

    def create(self, validated_data):
        from user.models import Biznes, Tarif
        from products.models import Dokon
        biznes_nomi = validated_data.pop('biznes_nomi', None)
        ism = validated_data.get('ism', 'Foydalanuvchi')
        if not biznes_nomi:
            biznes_nomi = f"{ism}ning Biznesi"
            
        tarif = Tarif.objects.first()
        if not tarif:
            tarif = Tarif.objects.create(nomi="Bepul tarif", dokon_limiti=2, mahsulot_limiti=100, xodim_limiti=3)
            
        biznes = Biznes.objects.create(
            nomi=biznes_nomi,
            egasi_ism=ism,
            tarif=tarif
        )
        
        # Create a default store/warehouse for the new business
        Dokon.objects.create(
            biznes=biznes,
            nomi=f"{biznes_nomi} do'koni"
        )

        # Create standard catalog fields as shown in catalog settings
        from products.models import XususiyatMaydoni
        XususiyatMaydoni.objects.create(biznes=biznes, nomi="Shtrix-kod", tur="matn")
        XususiyatMaydoni.objects.create(biznes=biznes, nomi="Tovar nomi", tur="matn")
        
        validated_data['biznes'] = biznes
        validated_data['is_active'] = True
        validated_data['rol'] = 'admin'
        validated_data['familiya'] = 'Foydalanuvchi'
        validated_data['jinsi'] = 'erkak'
        return Xodim.objects.create(**validated_data)


class BiznesSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    tarif_nomi = serializers.ReadOnlyField(source='tarif.nomi')

    class Meta:
        model = Biznes
        fields = ['id', 'nomi', 'egasi_ism', 'tarif', 'tarif_nomi', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['yaratilgan_vaqt', 'yangilangan_vaqt']

    def validate(self, attrs):
        tarif = attrs.get('tarif')
        if tarif and self.instance:
            current_stores = self.instance.dokonlar.count()
            current_products = self.instance.mahsulotlar.count()
            current_employees = self.instance.xodimlar.count()
            
            errors = []
            if current_stores > tarif.dokon_limiti:
                errors.append(f"Ushbu tarifga o'tib bo'lmaydi. Kompaniyangizda {current_stores} ta do'kon bor, yangi tarif esa faqat {tarif.dokon_limiti} tagacha ruxsat beradi.")
            if current_products > tarif.mahsulot_limiti:
                errors.append(f"Ushbu tarifga o'tib bo'lmaydi. Kompaniyangizda {current_products} ta mahsulot bor, yangi tarif esa faqat {tarif.mahsulot_limiti} tagacha ruxsat beradi.")
            if current_employees > tarif.xodim_limiti:
                errors.append(f"Ushbu tarifga o'tib bo'lmaydi. Kompaniyangizda {current_employees} ta xodim bor, yangi tarif esa faqat {tarif.xodim_limiti} tagacha ruxsat beradi.")
                
            if errors:
                raise serializers.ValidationError({"tarif": errors})
        return attrs


class TarifSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    class Meta:
        model = Tarif
        fields = ['id', 'nomi', 'dokon_limiti', 'mahsulot_limiti', 'xodim_limiti', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['yaratilgan_vaqt', 'yangilangan_vaqt']



