from rest_framework import serializers
from django.core.exceptions import ValidationError
from decimal import Decimal
import openpyxl
import csv
from io import BytesIO
from user.serializers import XSSSanitizerMixin
from products.models import Mahsulot, Dokon, MahsulotShtrixKod, Taminotchi
from .models import Taminotchi, SupplierOrder, SupplierOrderItem, SupplierOrderPayment, SupplierOrderReturn, SupplierOrderReturnItem

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
            'dastlabki_qarz', 'dastlabkiQarz', 'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'balans', 'yaratilgan_vaqt', 'yangilangan_vaqt']

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

class SupplierOrderPaymentSerializer(serializers.ModelSerializer):
    xodim_nomi = serializers.SerializerMethodField()

    class Meta:
        model = SupplierOrderPayment
        fields = ['id', 'tolangan_summa', 'tolov_turi', 'xodim', 'xodim_nomi', 'yaratilgan_vaqt']
        read_only_fields = ['xodim', 'yaratilgan_vaqt']

    def get_xodim_nomi(self, obj):
        if obj.xodim:
            return f"{obj.xodim.ism} {obj.xodim.familiya}"
        return ""

class SupplierOrderItemSerializer(serializers.ModelSerializer):
    mahsulot_nomi = serializers.ReadOnlyField(source='mahsulot.nomi')
    shtrix_kod = serializers.SerializerMethodField()
    kelish_narxi = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    ustama = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    sotish_narxi = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    ulgurji_narx = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = SupplierOrderItem
        fields = ['id', 'mahsulot', 'mahsulot_nomi', 'shtrix_kod', 'miqdori', 'kelish_narxi', 'ustama', 'sotish_narxi', 'ulgurji_narx']

    def get_shtrix_kod(self, obj):
        if obj.mahsulot and obj.mahsulot.shtrix_kodlar.exists():
            return obj.mahsulot.shtrix_kodlar.first().kod
        return ""

class SupplierOrderSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    nomi = serializers.CharField(required=False, allow_blank=True)
    taminotchi = serializers.PrimaryKeyRelatedField(queryset=Taminotchi.objects.all(), required=False, allow_null=True)
    dokon = serializers.PrimaryKeyRelatedField(queryset=Dokon.objects.all(), required=False, allow_null=True)
    qabul_qilish_sanasi = serializers.DateField(required=False, allow_null=True)
    elementlar = SupplierOrderItemSerializer(many=True, required=False, style={'base_template': 'textarea.html'})
    to_lovlar = SupplierOrderPaymentSerializer(many=True, read_only=True)
    taminotchi_nomi = serializers.ReadOnlyField(source='taminotchi.nomi')
    dokon_nomi = serializers.ReadOnlyField(source='dokon.nomi')
    yaratgan_xodim_nomi = serializers.SerializerMethodField()
    qabul_qilgan_xodim_nomi = serializers.SerializerMethodField()
    tolov_status = serializers.SerializerMethodField()
    tolangan_vaqt = serializers.SerializerMethodField()

    class Meta:
        model = SupplierOrder
        fields = [
            'id', 'biznes', 'taminotchi', 'taminotchi_nomi', 'dokon', 'dokon_nomi',
            'nomi', 'holat', 'qabul_qilish_sanasi', 'haqiqiy_qabul_sana',
            'yaratgan_xodim', 'yaratgan_xodim_nomi', 'qabul_qilgan_xodim', 'qabul_qilgan_xodim_nomi',
            'umumiy_summa', 'sotuv_summasi', 'tolangan_summa', 'nasiya_summa',
            'sotuvlar_taraqqiyoti', 'fayl', 'elementlar', 'to_lovlar', 'yaratilgan_vaqt', 'yangilangan_vaqt',
            'tolov_status', 'tolangan_vaqt'
        ]
        read_only_fields = [
            'biznes', 'holat', 'haqiqiy_qabul_sana', 'yaratgan_xodim', 'qabul_qilgan_xodim',
            'umumiy_summa', 'sotuv_summasi', 'tolangan_summa', 'nasiya_summa', 'sotuvlar_taraqqiyoti',
            'yaratilgan_vaqt', 'yangilangan_vaqt', 'tolov_status', 'tolangan_vaqt'
        ]

    def get_tolangan_vaqt(self, obj):
        payments = [p for p in obj.to_lovlar.all() if p.yaratilgan_vaqt]
        if payments:
            payments.sort(key=lambda x: x.yaratilgan_vaqt)
            return payments[-1].yaratilgan_vaqt
        return None

    def get_tolov_status(self, obj):
        if obj.umumiy_summa == 0:
            return 'tolanmagan'
        if obj.tolangan_summa == 0:
            return 'tolanmagan'
        if obj.tolangan_summa < obj.umumiy_summa:
            return 'qisman_tolangan'
        return 'tolangan'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            self.fields['dokon'].queryset = Dokon.objects.filter(biznes=biznes)
            self.fields['taminotchi'].queryset = Taminotchi.objects.filter(biznes=biznes)

    def get_yaratgan_xodim_nomi(self, obj):
        if obj.yaratgan_xodim:
            return f"{obj.yaratgan_xodim.ism} {obj.yaratgan_xodim.familiya}"
        return ""

    def get_qabul_qilgan_xodim_nomi(self, obj):
        if obj.qabul_qilgan_xodim:
            return f"{obj.qabul_qilgan_xodim.ism} {obj.qabul_qilgan_xodim.familiya}"
        return ""

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)

        for field in ['taminotchi', 'dokon', 'qabul_qilish_sanasi']:
            val = data.get(field)
            if val is None or val == '' or str(val).lower() in ('null', 'undefined', 'none'):
                data.pop(field, None)

        return super().to_internal_value(data)

    def validate(self, attrs):
        request = self.context.get('request')
        biznes = None
        if request and request.user and hasattr(request.user, 'xodim'):
            biznes = request.user.xodim.biznes

        if biznes:
            taminotchi = attrs.get('taminotchi')
            if not taminotchi:
                taminotchi = Taminotchi.objects.filter(biznes=biznes).first()
                if not taminotchi:
                    taminotchi = Taminotchi.objects.create(biznes=biznes, nomi="Asosiy yetkazib beruvchi")
                attrs['taminotchi'] = taminotchi
            elif taminotchi.biznes != biznes:
                raise serializers.ValidationError({"taminotchi": "Tanlangan yetkazib beruvchi sizning kompaniyangizga tegishli emas."})

            dokon = attrs.get('dokon')
            if not dokon:
                dokon = Dokon.objects.filter(biznes=biznes).first()
                if not dokon:
                    dokon = Dokon.objects.create(biznes=biznes, nomi="Asosiy do'kon")
                attrs['dokon'] = dokon
            elif dokon.biznes != biznes:
                raise serializers.ValidationError({"dokon": "Tanlangan do'kon sizning kompaniyangizga tegishli emas."})

        if not attrs.get('qabul_qilish_sanasi'):
            from django.utils.timezone import now
            attrs['qabul_qilish_sanasi'] = now().date()

        elementlar_data = attrs.get('elementlar', [])
        fayl = attrs.get('fayl') or (self.instance and self.instance.fayl)
        if not elementlar_data and not fayl and not self.instance:
            raise serializers.ValidationError({"elementlar": "Buyurtmada kamida bitta mahsulot bo'lishi shart yoki Excel fayli yuklanishi lozim."})

        for idx, item in enumerate(elementlar_data):
            mahsulot = item.get('mahsulot')
            if mahsulot and biznes and mahsulot.biznes != biznes:
                raise serializers.ValidationError({"elementlar": f"Element {idx+1}: Tanlangan mahsulot ({mahsulot.nomi}) sizning kompaniyangizga tegishli emas."})

        instance = self.instance
        temp_attrs = {}
        if instance:
            for field in self.Meta.fields:
                if hasattr(instance, field):
                    temp_attrs[field] = getattr(instance, field)
        temp_attrs.update(attrs)
        if biznes:
            temp_attrs['biznes'] = biznes
        temp_attrs.pop('id', None)
        temp_attrs.pop('elementlar', None)
        temp_attrs.pop('to_lovlar', None)
        temp_attrs.pop('fayl', None)

        temp_instance = SupplierOrder(**temp_attrs)
        try:
            temp_instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)

        return attrs

    def create(self, validated_data):
        elementlar_data = validated_data.pop('elementlar', [])
        fayl = validated_data.pop('fayl', None)

        request = self.context.get('request')
        xodim = None
        biznes = None
        if request and request.user and hasattr(request.user, 'xodim'):
            xodim = request.user.xodim
            biznes = xodim.biznes

        if not validated_data.get('nomi'):
            from django.utils.timezone import now
            validated_data['nomi'] = f"Buyurtma {now().strftime('%Y.%m.%d %H:%M')}"

        order = SupplierOrder.objects.create(biznes=biznes, yaratgan_xodim=xodim, **validated_data)

        if fayl:
            order.fayl = fayl
            order.save()
            self._parse_and_save_elements_from_file(fayl, order, biznes)
        else:
            for item_data in elementlar_data:
                mahsulot = item_data['mahsulot']
                if biznes and mahsulot.biznes != biznes:
                    order.delete()
                    raise serializers.ValidationError({"elementlar": f"Mahsulot ({mahsulot.nomi}) sizning kompaniyangizga tegishli emas."})
                SupplierOrderItem.objects.create(
                    order=order,
                    mahsulot=mahsulot,
                    miqdori=item_data['miqdori'],
                    kelish_narxi=item_data.get('kelish_narxi') or mahsulot.kelish_narxi or Decimal('0.00'),
                    ustama=item_data.get('ustama') or mahsulot.ustama or Decimal('0.00'),
                    sotish_narxi=item_data.get('sotish_narxi') or mahsulot.sotish_narxi or Decimal('0.00'),
                    ulgurji_narx=item_data.get('ulgurji_narx') or mahsulot.ulgurji_narx or Decimal('0.00')
                )

        return order

    def update(self, instance, validated_data):
        if instance.holat != 'qoralama':
            raise serializers.ValidationError({"detail": "Faqat qoralama buyurtmalarni tahrirlash mumkin."})

        elementlar_data = validated_data.pop('elementlar', None)
        fayl = validated_data.pop('fayl', None)

        request = self.context.get('request')
        biznes = None
        if request and request.user and hasattr(request.user, 'xodim'):
            biznes = request.user.xodim.biznes

        instance = super().update(instance, validated_data)

        if fayl:
            instance.fayl = fayl
            instance.save()
            instance.elementlar.all().delete()
            self._parse_and_save_elements_from_file(fayl, instance, biznes)
        elif elementlar_data is not None:
            instance.elementlar.all().delete()
            for item_data in elementlar_data:
                mahsulot = item_data['mahsulot']
                if biznes and mahsulot.biznes != biznes:
                    raise serializers.ValidationError({"elementlar": f"Mahsulot ({mahsulot.nomi}) sizning kompaniyangizga tegishli emas."})
                SupplierOrderItem.objects.create(
                    order=instance,
                    mahsulot=mahsulot,
                    miqdori=item_data['miqdori'],
                    kelish_narxi=item_data.get('kelish_narxi') or mahsulot.kelish_narxi or Decimal('0.00'),
                    ustama=item_data.get('ustama') or mahsulot.ustama or Decimal('0.00'),
                    sotish_narxi=item_data.get('sotish_narxi') or mahsulot.sotish_narxi or Decimal('0.00'),
                    ulgurji_narx=item_data.get('ulgurji_narx') or mahsulot.ulgurji_narx or Decimal('0.00')
                )

        return instance

    def _parse_and_save_elements_from_file(self, file_obj, order, biznes):
        def clean_num_str(val):
            if val is None:
                return "0"
            s = str(val).strip()
            s = s.replace('\xa0', '').replace(' ', '')
            if ',' in s and '.' not in s:
                parts = s.split(',')
                if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
                    s = s.replace(',', '')
                else:
                    s = s.replace(',', '.')
            elif ',' in s and '.' in s:
                s = s.replace(',', '')
            return s

        def parse_decimal_safe(val):
            try:
                s = clean_num_str(val)
                d = Decimal(s)
                return d.quantize(Decimal('0.01'))
            except Exception:
                return Decimal('0.00')

        def parse_int_safe(val):
            try:
                s = clean_num_str(val)
                return int(float(s))
            except Exception:
                return 0

        file_name = file_obj.name.lower()
        file_obj.seek(0)
        content = file_obj.read()

        rows = []
        if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            wb = openpyxl.load_workbook(filename=BytesIO(content), data_only=True, read_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                if any(x is not None for x in row):
                    rows.append([str(x) if x is not None else "" for x in row])
        else:
            decoded = None
            for encoding in ['utf-8-sig', 'utf-8', 'cp1251', 'latin-1']:
                try:
                    decoded = content.decode(encoding)
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            if not decoded:
                decoded = content.decode('utf-8', errors='ignore')

            lines = [line for line in decoded.splitlines() if line.strip()]
            if lines:
                delimiter = ','
                first_line = lines[0]
                if ';' in first_line and first_line.count(';') >= first_line.count(','):
                    delimiter = ';'
                elif '\t' in first_line:
                    delimiter = '\t'

                reader = csv.reader(lines, delimiter=delimiter)
                for row in reader:
                    if any(x.strip() != "" for x in row):
                        rows.append(row)

        if not rows:
            order.delete()
            raise serializers.ValidationError({"fayl": "Fayl bo'sh yoki uni o'qib bo'lmadi."})

        headers = [str(h).lower().strip().replace('\ufeff', '') for h in rows[0]]
        col_mapping = {}
        for idx, h in enumerate(headers):
            if any(k in h for k in ['nomi', 'name', 'наименование', 'tovar', 'mahsulot']):
                col_mapping['nomi'] = idx
            elif any(k in h for k in ['shtrix', 'barcode', 'баркод', 'kod', 'код']):
                col_mapping['shtrix_kod'] = idx
            elif any(k in h for k in ['miqdor', 'qty', 'kol', 'кол', 'buyurtmaga', 'soni', 'son']):
                col_mapping['miqdori'] = idx
            elif any(k in h for k in ['kelish', 'cost', 'поставки', 'tannarx', 'kirish']):
                col_mapping['kelish_narxi'] = idx
            elif any(k in h for k in ['ustama', 'markup', 'наценка']):
                col_mapping['ustama'] = idx
            elif any(k in h for k in ['sotish', 'retail', 'sotuv', 'продажи', 'розничная', 'narxi']):
                if 'kelish' not in h and 'ulgurji' not in h:
                    col_mapping['sotish_narxi'] = idx
            elif any(k in h for k in ['ulgurji', 'wholesale', 'оптом']):
                col_mapping['ulgurji_narx'] = idx

        if 'nomi' not in col_mapping and len(headers) > 0: col_mapping['nomi'] = 0
        if 'shtrix_kod' not in col_mapping and len(headers) > 1: col_mapping['shtrix_kod'] = 1
        if 'miqdori' not in col_mapping and len(headers) > 2: col_mapping['miqdori'] = 2
        if 'kelish_narxi' not in col_mapping and len(headers) > 3: col_mapping['kelish_narxi'] = 3
        if 'ustama' not in col_mapping and len(headers) > 4: col_mapping['ustama'] = 4
        if 'sotish_narxi' not in col_mapping and len(headers) > 5: col_mapping['sotish_narxi'] = 5
        if 'ulgurji_narx' not in col_mapping and len(headers) > 6: col_mapping['ulgurji_narx'] = 6

        start_row_idx = 1
        first_row_nomi = rows[0][col_mapping['nomi']].strip().lower() if 'nomi' in col_mapping and len(rows[0]) > col_mapping['nomi'] else ""
        if any(k in first_row_nomi for k in ['nomi', 'name', 'наименование', 'tovar', 'mahsulot']):
            start_row_idx = 1
        else:
            start_row_idx = 0

        for row in rows[start_row_idx:]:
            nomi = row[col_mapping['nomi']].strip() if 'nomi' in col_mapping and len(row) > col_mapping['nomi'] else ""
            if not nomi:
                continue

            shtrix_kod = row[col_mapping['shtrix_kod']].strip() if 'shtrix_kod' in col_mapping and len(row) > col_mapping['shtrix_kod'] else ""
            miqdori = parse_int_safe(row[col_mapping['miqdori']]) if 'miqdori' in col_mapping and len(row) > col_mapping['miqdori'] else 0
            kelish_narxi = parse_decimal_safe(row[col_mapping['kelish_narxi']]) if 'kelish_narxi' in col_mapping and len(row) > col_mapping['kelish_narxi'] else Decimal('0.00')
            ustama = parse_decimal_safe(row[col_mapping['ustama']]) if 'ustama' in col_mapping and len(row) > col_mapping['ustama'] else Decimal('0.00')
            sotish_narxi = parse_decimal_safe(row[col_mapping['sotish_narxi']]) if 'sotish_narxi' in col_mapping and len(row) > col_mapping['sotish_narxi'] else Decimal('0.00')
            ulgurji_narx = parse_decimal_safe(row[col_mapping['ulgurji_narx']]) if 'ulgurji_narx' in col_mapping and len(row) > col_mapping['ulgurji_narx'] else Decimal('0.00')

            if kelish_narxi > Decimal('0.00'):
                if sotish_narxi < kelish_narxi:
                    if ustama > Decimal('0.00'):
                        sotish_narxi = (kelish_narxi * (Decimal('1.00') + ustama / Decimal('100.00'))).quantize(Decimal('0.01'))
                    else:
                        sotish_narxi = kelish_narxi
                if ustama == Decimal('0.00') and sotish_narxi > kelish_narxi:
                    ustama = (((sotish_narxi - kelish_narxi) / kelish_narxi) * Decimal('100.00')).quantize(Decimal('0.01'))
                if ustama > Decimal('100.00'):
                    ustama = Decimal('100.00')

            if ulgurji_narx < kelish_narxi:
                ulgurji_narx = sotish_narxi

            product = None
            if shtrix_kod:
                try:
                    product = Mahsulot.objects.filter(biznes=biznes, shtrix_kodlar__kod=shtrix_kod).first()
                except Exception:
                    pass
            if not product:
                product = Mahsulot.objects.filter(biznes=biznes, nomi__iexact=nomi).first()

            if not product:
                if biznes and biznes.tarif:
                    limit = biznes.tarif.mahsulot_limiti
                    if Mahsulot.objects.filter(biznes=biznes).count() >= limit:
                        order.delete()
                        raise serializers.ValidationError({"detail": f"Tarif rejangiz bo'yicha mahsulotlar soni limiti ({limit}) tugagan. Yangi mahsulot yaratib bo'lmaydi."})
                product = Mahsulot.objects.create(
                    biznes=biznes,
                    nomi=nomi,
                    olchov_birligi='dona',
                    kelish_narxi=kelish_narxi,
                    ustama=ustama,
                    sotish_narxi=sotish_narxi,
                    ulgurji_narx=ulgurji_narx,
                    miqdori=0
                )
                if shtrix_kod and not MahsulotShtrixKod.objects.filter(kod=shtrix_kod).exists():
                    try:
                        MahsulotShtrixKod.objects.create(mahsulot=product, kod=shtrix_kod)
                    except Exception:
                        pass

            SupplierOrderItem.objects.create(
                order=order,
                mahsulot=product,
                miqdori=miqdori,
                kelish_narxi=kelish_narxi,
                ustama=ustama,
                sotish_narxi=sotish_narxi,
                ulgurji_narx=ulgurji_narx
            )

class SupplierOrderReturnItemSerializer(serializers.ModelSerializer):
    mahsulot_nomi = serializers.ReadOnlyField(source='mahsulot.nomi')

    class Meta:
        model = SupplierOrderReturnItem
        fields = ['id', 'mahsulot', 'mahsulot_nomi', 'miqdori', 'kelish_narxi']

class SupplierOrderReturnSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    elementlar = SupplierOrderReturnItemSerializer(many=True, required=True, style={'base_template': 'textarea.html'})
    dokon_nomi = serializers.ReadOnlyField(source='dokon.nomi')
    taminotchi_nomi = serializers.ReadOnlyField(source='taminotchi.nomi')

    class Meta:
        model = SupplierOrderReturn
        fields = [
            'id', 'biznes', 'order', 'dokon', 'dokon_nomi', 'taminotchi', 'taminotchi_nomi',
            'holat', 'qaytarish_summasi', 'miqdori', 'elementlar', 'yaratilgan_vaqt'
        ]
        read_only_fields = ['biznes', 'holat', 'qaytarish_summasi', 'miqdori', 'yaratilgan_vaqt']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            self.fields['dokon'].queryset = Dokon.objects.filter(biznes=biznes)
            self.fields['taminotchi'].queryset = Taminotchi.objects.filter(biznes=biznes)
            self.fields['order'].queryset = SupplierOrder.objects.filter(biznes=biznes)

    def validate(self, attrs):
        request = self.context.get('request')
        biznes = None
        if request and request.user and hasattr(request.user, 'xodim'):
            biznes = request.user.xodim.biznes

        if biznes:
            order = attrs.get('order')
            if order and order.biznes != biznes:
                raise serializers.ValidationError({"order": "Ushbu buyurtma sizning kompaniyangizga tegishli emas."})
            
            dokon = attrs.get('dokon')
            if dokon and dokon.biznes != biznes:
                raise serializers.ValidationError({"dokon": "Ushbu do'kon sizning kompaniyangizga tegishli emas."})
            


        return attrs

    def create(self, validated_data):
        elementlar_data = validated_data.pop('elementlar')

        request = self.context.get('request')
        biznes = None
        if request and request.user and hasattr(request.user, 'xodim'):
            biznes = request.user.xodim.biznes

        return_obj = SupplierOrderReturn.objects.create(biznes=biznes, **validated_data)

        for item_data in elementlar_data:
            SupplierOrderReturnItem.objects.create(
                return_obj=return_obj,
                mahsulot=item_data['mahsulot'],
                miqdori=item_data['miqdori'],
                kelish_narxi=item_data['kelish_narxi']
            )

        return return_obj
