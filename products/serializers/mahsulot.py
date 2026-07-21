from rest_framework import serializers
from django.core.exceptions import ValidationError
from decimal import Decimal
from products.models import Mahsulot, Characteristic, MahsulotRasm, MahsulotShtrixKod, DokonQoldiq, OlchovBirligi
from user.serializers import XSSSanitizerMixin

class OlchovBirligiRelatedField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        if isinstance(data, int) or (isinstance(data, str) and data.isdigit()):
            return super().to_internal_value(data)
        
        if isinstance(data, str):
            request = self.context.get('request')
            biznes = request.user.xodim.biznes if (request and request.user and hasattr(request.user, 'xodim')) else None
            
            val_clean = data.strip().lower()
            unit_obj, created = OlchovBirligi.objects.get_or_create(
                biznes=biznes,
                short_name=val_clean,
                defaults={'nomi': data.strip().capitalize()}
            )
            return unit_obj
        
        return super().to_internal_value(data)

class CharacteristicSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    class Meta:
        model = Characteristic
        fields = ['id', 'name', 'value', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['yaratilgan_vaqt', 'yangilangan_vaqt']


class DokonQoldiqSerializer(serializers.ModelSerializer):
    class Meta:
        model = DokonQoldiq
        fields = ['id', 'dokon', 'miqdori', 'ogohlantirish', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['yaratilgan_vaqt', 'yangilangan_vaqt']


class MahsulotRasmSerializer(serializers.ModelSerializer):
    class Meta:
        model = MahsulotRasm
        fields = ['id', 'rasm', 'mahsulot', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['yaratilgan_vaqt', 'yangilangan_vaqt']

    def validate(self, attrs):
        mahsulot = attrs.get('mahsulot')
        if mahsulot:
            existing_count = mahsulot.rasmlar.exclude(id=self.instance.id).count() if self.instance else mahsulot.rasmlar.count()
            if existing_count >= 5:
                raise serializers.ValidationError({"detail": "Ushbu mahsulotga ko'pi bilan 5 tagacha rasm yuklash mumkin."})
        return attrs


class MahsulotShtrixKodSerializer(serializers.ModelSerializer):
    class Meta:
        model = MahsulotShtrixKod
        fields = ['id', 'kod', 'mahsulot', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['yaratilgan_vaqt', 'yangilangan_vaqt']

    def validate(self, attrs):
        kod = attrs.get('kod')
        if kod:
            kod_str = str(kod).strip()
            if not kod_str.isdigit():
                raise serializers.ValidationError({"kod": "Shtrix kod faqat raqamlardan iborat bo'lishi shart."})
            if len(kod_str) not in [8, 12, 13]:
                raise serializers.ValidationError({"kod": "Shtrix kod uzunligi 8, 12 yoki 13 ta raqamdan iborat bo'lishi kerak."})
                
            qs = MahsulotShtrixKod.objects.filter(kod=kod_str)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError({"kod": f"Shtrix kod '{kod_str}' allaqachon boshqa mahsulotga biriktirilgan."})
            attrs['kod'] = kod_str
        return attrs


class MultiImageField(serializers.FileField):
    def to_internal_value(self, data):
        if not data:
            return []
        
        if not isinstance(data, list):
            data = [data]
            
        if len(data) > 5:
            raise serializers.ValidationError("Ko'pi bilan 5 tagacha rasm yuklash mumkin.")
            
        from products.models import validate_image_size
        
        validated_files = []
        image_field = serializers.ImageField(allow_empty_file=False)
        for img in data:
            try:
                validated_img = image_field.run_validation(img)
                validate_image_size(validated_img)
                validated_files.append(validated_img)
            except serializers.ValidationError as e:
                raise serializers.ValidationError(e.detail)
            except ValidationError as e:
                raise serializers.ValidationError(e.messages)
        return validated_files


class MultiBarcodeField(serializers.CharField):
    def to_internal_value(self, data):
        if not data:
            return []
        
        if isinstance(data, str):
            if ',' in data:
                data = [x.strip() for x in data.split(',') if x.strip()]
            else:
                data = [data.strip()]
        elif not isinstance(data, list):
            data = [data]
            
        validated_codes = []
        parent_serializer = self.parent
        parent_instance = parent_serializer.instance if parent_serializer else None
        
        for val in data:
            val_str = str(val).strip()
            if not val_str:
                continue
            if not val_str.isdigit():
                raise serializers.ValidationError("Shtrix kod faqat raqamlardan iborat bo'lishi shart.")
            if len(val_str) not in [8, 12, 13]:
                raise serializers.ValidationError("Shtrix kod uzunligi 8, 12 yoki 13 ta raqamdan iborat bo'lishi kerak.")
            
            qs = MahsulotShtrixKod.objects.filter(kod=val_str)
            if parent_instance:
                qs = qs.exclude(mahsulot=parent_instance)
            if qs.exists():
                raise serializers.ValidationError(f"Shtrix kod '{val_str}' allaqachon boshqa mahsulotga biriktirilgan.")
                
            validated_codes.append(val_str)
        return validated_codes


class DokonQoldiqWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DokonQoldiq
        fields = ['dokon', 'miqdori', 'ogohlantirish']


class MahsulotSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    kam_qoldi = serializers.ReadOnlyField()
    sotish_narxi = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    ustama = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0.00)
    rasm = MultiImageField(required=False, write_only=True, style={'multiple': True})
    shtrix_kod = MultiBarcodeField(required=False, style={'multiple': True})
    qoldiqlar = DokonQoldiqWriteSerializer(many=True, required=False)
    olchov_birligi = OlchovBirligiRelatedField(queryset=OlchovBirligi.objects.all(), required=False, allow_null=True)
    characteristics = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Characteristic.objects.all(),
        required=False
    )
    taminotchi_nomi = serializers.ReadOnlyField(source='taminotchi.nomi')
    dokon = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            from products.models import Taminotchi
            self.fields['taminotchi'].queryset = Taminotchi.objects.filter(biznes=biznes)
            self.fields['olchov_birligi'].queryset = OlchovBirligi.objects.filter(biznes=biznes)

    holat_rangi = serializers.SerializerMethodField()

    def get_holat_rangi(self, obj):
        request = self.context.get('request')
        kritik = 10
        kam = 20
        if request:
            try:
                kritik = int(request.query_params.get('kritik_chegara', 10))
                kam = int(request.query_params.get('kam_chegara', 20))
            except ValueError:
                pass
        
        miqdor = obj.miqdori if obj.miqdori is not None else 0
        if miqdor <= kritik:
            return 'kritik'
        elif miqdor <= kam:
            return 'kam'
        else:
            return 'normal'

    class Meta:
        model = Mahsulot
        fields = [
            'id', 'biznes', 'nomi', 'shtrix_kod', 'olchov_birligi', 'rasm',
            'kelish_narxi', 'ustama', 'sotish_narxi', 'ulgurji_narx', 'miqdori',
            'ogohlantirish', 'is_active', 'toifa', 'brend', 'taminotchi', 'taminotchi_nomi',
            'erkin_narx', 'tavsif', 'characteristics', 'qoldiqlar', 'yaratilgan_vaqt',
            'yangilangan_vaqt', 'kam_qoldi', 'dokon', 'holat_rangi'
        ]
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def to_internal_value(self, data):
        if hasattr(data, 'getlist'):
            mutable_data = {}
            for key in data.keys():
                if key == 'rasm':
                    mutable_data[key] = data.getlist(key)
                elif key == 'shtrix_kod':
                    mutable_data[key] = data.getlist(key)
                elif key == 'characteristics':
                    mutable_data[key] = data.getlist(key)
                else:
                    mutable_data[key] = data.get(key)
            data = mutable_data

        if 'qoldiqlar' in data:
            import json
            val = data['qoldiqlar']
            if isinstance(val, str):
                try:
                    data['qoldiqlar'] = json.loads(val)
                except json.JSONDecodeError:
                    pass
            elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], str):
                try:
                    data['qoldiqlar'] = json.loads(val[0])
                except json.JSONDecodeError:
                    pass

        return super().to_internal_value(data)

    def validate(self, attrs):
        instance = self.instance
        temp_attrs = {}
        request = self.context.get('request')
        
        if not instance:
            qoldiqlar = attrs.get('qoldiqlar')
            if not qoldiqlar:
                raise serializers.ValidationError({"qoldiqlar": "Yangi mahsulot yaratilayotganda kamida bitta do'kon uchun qoldiq kiritilgan bo'lishi shart."})
            
            if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
                biznes = request.user.xodim.biznes
                if biznes.tarif:
                    limit = biznes.tarif.mahsulot_limiti
                    if Mahsulot.objects.filter(biznes=biznes).count() >= limit:
                        raise serializers.ValidationError({"detail": f"Tarif rejangiz bo'yicha mahsulotlar soni limiti ({limit}) tugagan. Yangi mahsulot yaratib bo'lmaydi."})

        taminotchi = attrs.get('taminotchi')
        if taminotchi and request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            if taminotchi.biznes != request.user.xodim.biznes:
                raise serializers.ValidationError({"taminotchi": "Tanlangan yetkazib beruvchi sizning kompaniyangizga tegishli emas."})

        qoldiqlar = attrs.get('qoldiqlar')
        if qoldiqlar and request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            for q in qoldiqlar:
                dokon_obj = q.get('dokon')
                if dokon_obj.biznes != biznes:
                    raise serializers.ValidationError({"qoldiqlar": f"Tanlangan do'kon ({dokon_obj.nomi}) sizning kompaniyangizga tegishli emas."})
        
        if instance:
            for field in self.Meta.fields:
                if hasattr(instance, field):
                    temp_attrs[field] = getattr(instance, field)
        
        temp_attrs.update(attrs)
        
        temp_attrs.pop('id', None)
        temp_attrs.pop('kam_qoldi', None)
        temp_attrs.pop('rasm', None)
        temp_attrs.pop('shtrix_kod', None)
        temp_attrs.pop('characteristics', None)
        temp_attrs.pop('qoldiqlar', None)
        
        temp_instance = Mahsulot(**temp_attrs)
        
        try:
            temp_instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
            
        attrs['ustama'] = temp_instance.ustama
        attrs['sotish_narxi'] = temp_instance.sotish_narxi
        
        return attrs

    def get_dokon(self, obj):
        request = self.context.get('request')
        if request:
            dokon_id = request.query_params.get('dokon')
            if dokon_id:
                try:
                    return int(dokon_id)
                except ValueError:
                    pass
        return list(obj.qoldiqlar.values_list('dokon_id', flat=True))

    def create(self, validated_data):
        characteristics = validated_data.pop('characteristics', [])
        rasm_files = validated_data.pop('rasm', [])
        shtrix_kodlar = validated_data.pop('shtrix_kod', [])
        qoldiqlar_data = validated_data.pop('qoldiqlar', [])
        
        product = Mahsulot(**validated_data)
        if shtrix_kodlar:
            product._custom_barcodes = shtrix_kodlar
        product.miqdori = sum(q.get('miqdori', 0) for q in qoldiqlar_data)
        product.save()
        product.characteristics.set(characteristics)
        
        for q_data in qoldiqlar_data:
            DokonQoldiq.objects.create(mahsulot=product, **q_data)
            
        for file in rasm_files:
            MahsulotRasm.objects.create(mahsulot=product, rasm=file)
        return product

    def update(self, instance, validated_data):
        characteristics = validated_data.pop('characteristics', None)
        rasm_files = validated_data.pop('rasm', None)
        shtrix_kodlar = validated_data.pop('shtrix_kod', None)
        qoldiqlar_data = validated_data.pop('qoldiqlar', None)
        
        instance = super().update(instance, validated_data)
        if characteristics is not None:
            instance.characteristics.set(characteristics)
            
        if rasm_files is not None:
            instance.rasmlar.all().delete()
            for file in rasm_files:
                MahsulotRasm.objects.create(mahsulot=instance, rasm=file)
                
        if shtrix_kodlar is not None:
            instance.shtrix_kodlar.all().delete()
            if not shtrix_kodlar:
                code = instance.generate_unique_barcode()
                MahsulotShtrixKod.objects.create(mahsulot=instance, kod=code)
            else:
                for code in shtrix_kodlar:
                    MahsulotShtrixKod.objects.create(mahsulot=instance, kod=code)
                    
        if qoldiqlar_data is not None:
            instance.qoldiqlar.all().delete()
            for q_data in qoldiqlar_data:
                DokonQoldiq.objects.create(mahsulot=instance, **q_data)
            instance.miqdori = sum(q.get('miqdori', 0) for q in qoldiqlar_data)
            instance.save(update_fields=['miqdori'])
            
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['olchov_birligi'] = instance.olchov_birligi.short_name if instance.olchov_birligi else ""
        representation['rasm'] = MahsulotRasmSerializer(
            instance.rasmlar.all(),
            many=True,
            context=self.context
        ).data
        representation['shtrix_kod'] = [b.kod for b in instance.shtrix_kodlar.all()]
        representation['characteristics'] = CharacteristicSerializer(
            instance.characteristics.all(),
            many=True
        ).data
        representation['qoldiqlar'] = DokonQoldiqSerializer(
            instance.qoldiqlar.filter(miqdori__gt=0),
            many=True
        ).data
        return representation


from products.models import XususiyatMaydoni, Toplam, ToplamElement, YorliqShablon, Dokon

class XususiyatMaydoniSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    tur_display = serializers.SerializerMethodField()

    class Meta:
        model = XususiyatMaydoni
        fields = ['id', 'biznes', 'nomi', 'tur', 'tur_display', 'is_active', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def get_tur_display(self, obj):
        tur_map = {
            'matn': 'Matn',
            'text': 'Matn',
            'raqam': 'Raqam',
            'number': 'Raqam',
            'tanlov': 'Tanlov',
            'select': 'Tanlov',
            'sana': 'Sana',
            'date': 'Sana',
        }
        val = str(obj.tur).lower() if obj.tur else 'matn'
        return tur_map.get(val, val.capitalize())

    def validate(self, attrs):
        nomi = attrs.get('nomi')
        if nomi:
            nomi_clean = nomi.strip()
            request = self.context.get('request')
            biznes = None
            if request and request.user and hasattr(request.user, 'xodim'):
                biznes = request.user.xodim.biznes

            qs = XususiyatMaydoni.objects.filter(biznes=biznes, nomi__iexact=nomi_clean, is_active=True)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError({"nomi": f"'{nomi_clean}' nomli faol xususiyat maydoni allaqachon mavjud."})

            attrs['nomi'] = nomi_clean
        return attrs


class ToplamElementSerializer(serializers.ModelSerializer):
    mahsulot_nomi = serializers.ReadOnlyField(source='mahsulot.nomi')
    mahsulot_shtrix_kod = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            self.fields['mahsulot'].queryset = Mahsulot.objects.filter(biznes=biznes)

    class Meta:
        model = ToplamElement
        fields = ['id', 'mahsulot', 'mahsulot_nomi', 'mahsulot_shtrix_kod', 'miqdori', 'kelish_narxi', 'sotish_narxi']
        read_only_fields = ['kelish_narxi', 'sotish_narxi']

    def get_mahsulot_shtrix_kod(self, obj):
        if obj.mahsulot and obj.mahsulot.shtrix_kodlar.exists():
            return obj.mahsulot.shtrix_kodlar.first().kod
        return ""

    def validate_miqdori(self, value):
        if value <= 0:
            raise serializers.ValidationError("Kirim miqdori 0 dan katta bo'lishi shart.")
        return value


class ToplamSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    elementlar = ToplamElementSerializer(many=True, required=False)
    dokon_nomi = serializers.ReadOnlyField(source='dokon.nomi')
    yaratgan_xodim_nomi = serializers.SerializerMethodField()

    # Write-only fields for bundle finished product creation
    shtrix_kod = serializers.CharField(write_only=True, required=False, allow_blank=True)
    sotish_narxi = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False)
    kelish_narxi = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False)
    ustama = serializers.DecimalField(max_digits=5, decimal_places=2, write_only=True, required=False)
    ulgurji_narx = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False)
    rasm = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
    characteristics = serializers.JSONField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            self.fields['dokon'].queryset = Dokon.objects.filter(biznes=biznes)

    class Meta:
        model = Toplam
        fields = [
            'id', 'biznes', 'mahsulot', 'dokon', 'dokon_nomi', 'nomi', 'holat', 'miqdori', 'summa',
            'elementlar', 'yaratgan_xodim', 'yaratgan_xodim_nomi', 'yaratilgan_vaqt', 'yangilangan_vaqt',
            'shtrix_kod', 'sotish_narxi', 'kelish_narxi', 'ustama', 'ulgurji_narx', 'rasm', 'characteristics'
        ]
        read_only_fields = [
            'biznes', 'mahsulot', 'holat', 'summa', 'yaratgan_xodim', 'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]

    def get_yaratgan_xodim_nomi(self, obj):
        if obj.yaratgan_xodim:
            return f"{obj.yaratgan_xodim.ism} {obj.yaratgan_xodim.familiya}"
        return ""

    def validate(self, attrs):
        request = self.context.get('request')
        biznes = None
        if request and request.user and hasattr(request.user, 'xodim'):
            biznes = request.user.xodim.biznes

        if biznes:
            dokon = attrs.get('dokon')
            if dokon and dokon.biznes != biznes:
                raise serializers.ValidationError({"dokon": "Ushbu do'kon sizning biznesingizga tegishli emas."})

        if not self.instance:
            elementlar = attrs.get('elementlar', [])
            initial_elementlar = self.initial_data.get('elementlar', []) if hasattr(self, 'initial_data') else []
            if not elementlar and not initial_elementlar:
                raise serializers.ValidationError({"elementlar": "To'plam kirimi uchun kamida bitta mahsulot kiritilgan bo'lishi shart."})

        return attrs

    def create(self, validated_data):
        elementlar_data = validated_data.pop('elementlar', [])
        
        # Finished product parameters
        shtrix_kod = validated_data.pop('shtrix_kod', None)
        sotish_narxi = validated_data.pop('sotish_narxi', None)
        kelish_narxi = validated_data.pop('kelish_narxi', None)
        ustama = validated_data.pop('ustama', None)
        ulgurji_narx = validated_data.pop('ulgurji_narx', None)
        rasm_files = validated_data.pop('rasm', None)
        characteristics_data = validated_data.pop('characteristics', None)

        request = self.context.get('request')
        biznes = None
        yaratgan_xodim = None
        if request and request.user and hasattr(request.user, 'xodim'):
            yaratgan_xodim = request.user.xodim
            biznes = yaratgan_xodim.biznes

        finished_product = None
        if shtrix_kod or sotish_narxi is not None or validated_data.get('nomi'):
            # Check if this is a finished bundle product creation
            # If the user just wanted a legacy batch replenishment, they would not submit shtrix_kod or prices.
            # However, we can check if it's explicitly intended. Let's check if any of these are present.
            if shtrix_kod or sotish_narxi is not None or rasm_files or characteristics_data:
                from products.models import OlchovBirligi, Mahsulot, MahsulotShtrixKod, MahsulotRasm, Characteristic
                
                # Resolve unit 'dona' or create it
                unit_obj, _ = OlchovBirligi.objects.get_or_create(
                    biznes=biznes,
                    short_name='dona',
                    defaults={'nomi': 'Dona'}
                )
                
                k_narx = kelish_narxi or Decimal('0.00')
                s_narx = sotish_narxi or Decimal('0.00')
                ust = ustama or Decimal('0.00')
                if k_narx > 0 and s_narx > 0:
                    ust = (((s_narx - k_narx) / k_narx) * Decimal('100.00')).quantize(Decimal('0.01'))
                elif k_narx > 0 and ust > 0:
                    s_narx = (k_narx * (Decimal('1.00') + ust / Decimal('100.00'))).quantize(Decimal('0.01'))

                finished_product = Mahsulot.objects.create(
                    biznes=biznes,
                    nomi=validated_data.get('nomi') or "Yangi To'plam",
                    olchov_birligi=unit_obj,
                    kelish_narxi=k_narx,
                    sotish_narxi=s_narx,
                    ustama=ust,
                    ulgurji_narx=ulgurji_narx or Decimal('0.00'),
                    miqdori=0
                )

                if shtrix_kod:
                    MahsulotShtrixKod.objects.create(mahsulot=finished_product, kod=shtrix_kod)
                else:
                    finished_product.shtrix_kod = finished_product.generate_unique_barcode()
                    finished_product.save()

                if rasm_files:
                    for f in rasm_files:
                        MahsulotRasm.objects.create(mahsulot=finished_product, rasm=f)

                if characteristics_data:
                    if isinstance(characteristics_data, list):
                        for char_item in characteristics_data:
                            c_name = char_item.get('name')
                            c_val = char_item.get('value')
                            if c_name and c_val:
                                Characteristic.objects.create(mahsulot=finished_product, name=c_name, value=c_val)

        toplam = Toplam.objects.create(
            biznes=biznes,
            yaratgan_xodim=yaratgan_xodim,
            mahsulot=finished_product,
            **validated_data
        )

        for item_data in elementlar_data:
            mahsulot = item_data['mahsulot']
            if biznes and mahsulot.biznes != biznes:
                raise serializers.ValidationError({"elementlar": f"'{mahsulot.nomi}' mahsuloti sizning biznesingizga tegishli emas."})
            ToplamElement.objects.create(
                toplam=toplam,
                mahsulot=mahsulot,
                miqdori=item_data['miqdori'],
                kelish_narxi=mahsulot.kelish_narxi or Decimal('0.00'),
                sotish_narxi=mahsulot.sotish_narxi or Decimal('0.00')
            )

        return toplam


class YorliqShablonSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    class Meta:
        model = YorliqShablon
        fields = ['id', 'biznes', 'nomi', 'eni', 'uzunlik', 'shtrixkod_formati', 'xususiyatlar', 'is_active']
        read_only_fields = ['biznes']

    def validate(self, attrs):
        nomi = attrs.get('nomi')
        if nomi:
            attrs['nomi'] = nomi.strip()

        eni = attrs.get('eni')
        if eni is not None and eni <= 0:
            raise serializers.ValidationError({"eni": "Eni 0 dan katta bo'lishi shart."})

        uzunlik = attrs.get('uzunlik')
        if uzunlik is not None and uzunlik <= 0:
            raise serializers.ValidationError({"uzunlik": "Uzunlik 0 dan katta bo'lishi shart."})

        return attrs
