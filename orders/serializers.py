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

    def create(self, validated_data):
        dastlabki_qarz = validated_data.pop('dastlabki_qarz', None)
        dastlabki_qarz_camel = validated_data.pop('dastlabkiQarz', None)
        
        initial_debt = dastlabki_qarz or dastlabki_qarz_camel or Decimal('0.00')
        
        taminotchi = super().create(validated_data)
        
        if initial_debt > Decimal('0.00'):
            from orders.models import SupplierOrder
            from products.models import Dokon
            from django.utils.timezone import now
            
            dokon = Dokon.objects.filter(biznes=taminotchi.biznes).first()
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

    class Meta:
        model = SupplierOrderItem
        fields = ['id', 'mahsulot', 'mahsulot_nomi', 'shtrix_kod', 'miqdori', 'kelish_narxi', 'ustama', 'sotish_narxi', 'ulgurji_narx']

    def get_shtrix_kod(self, obj):
        if obj.mahsulot and obj.mahsulot.shtrix_kodlar.exists():
            return obj.mahsulot.shtrix_kodlar.first().kod
        return ""

class SupplierOrderSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    nomi = serializers.CharField(required=False, allow_blank=True)
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
        payments = list(obj.to_lovlar.all())
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

    def validate(self, attrs):
        request = self.context.get('request')
        biznes = None
        if request and request.user and hasattr(request.user, 'xodim'):
            biznes = request.user.xodim.biznes

        if biznes:

            
            dokon = attrs.get('dokon')
            if dokon and dokon.biznes != biznes:
                raise serializers.ValidationError({"dokon": "Tanlangan do'kon sizning kompaniyangizga tegishli emas."})

        elementlar_data = attrs.get('elementlar', [])
        fayl = attrs.get('fayl') or (self.instance and self.instance.fayl)
        if not elementlar_data and not fayl and not self.instance:
            raise serializers.ValidationError({"elementlar": "Buyurtmada kamida bitta mahsulot bo'lishi shart yoki Excel fayli yuklanishi lozim."})

        for idx, item in enumerate(elementlar_data):
            mahsulot = item.get('mahsulot')
            if biznes and mahsulot.biznes != biznes:
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
                    kelish_narxi=item_data.get('kelish_narxi', mahsulot.kelish_narxi or Decimal('0.00')),
                    ustama=item_data.get('ustama', mahsulot.ustama or Decimal('0.00')),
                    sotish_narxi=item_data.get('sotish_narxi', mahsulot.sotish_narxi or Decimal('0.00')),
                    ulgurji_narx=item_data.get('ulgurji_narx', mahsulot.ulgurji_narx or Decimal('0.00'))
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
                    kelish_narxi=item_data.get('kelish_narxi', mahsulot.kelish_narxi or Decimal('0.00')),
                    ustama=item_data.get('ustama', mahsulot.ustama or Decimal('0.00')),
                    sotish_narxi=item_data.get('sotish_narxi', mahsulot.sotish_narxi or Decimal('0.00')),
                    ulgurji_narx=item_data.get('ulgurji_narx', mahsulot.ulgurji_narx or Decimal('0.00'))
                )

        return instance

    def _parse_and_save_elements_from_file(self, file_obj, order, biznes):
        file_name = file_obj.name
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
            try:
                decoded = content.decode('utf-8')
            except UnicodeDecodeError:
                decoded = content.decode('latin-1')
            reader = csv.reader(decoded.splitlines())
            for row in reader:
                if any(x != "" for x in row):
                    rows.append(row)

        if not rows:
            raise serializers.ValidationError("Fayl bo'sh yoki uni o'qib bo'lmadi.")

        headers = [str(h).lower().strip() for h in rows[0]]
        col_mapping = {}
        for idx, h in enumerate(headers):
            if any(k in h for k in ['nomi', 'name', 'наименование', 'tovar']):
                col_mapping['nomi'] = idx
            elif any(k in h for k in ['shtrix', 'barcode', 'баркод', 'kod', 'код']):
                col_mapping['shtrix_kod'] = idx
            elif any(k in h for k in ['miqdor', 'qty', 'kol', 'кол', 'buyurtmaga']):
                col_mapping['miqdori'] = idx
            elif any(k in h for k in ['kelish', 'cost', 'поставки']):
                col_mapping['kelish_narxi'] = idx
            elif any(k in h for k in ['ustama', 'markup', 'наценка']):
                col_mapping['ustama'] = idx
            elif any(k in h for k in ['sotish', 'retail', 'sotuv', 'продажи', 'розничная']):
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

        for row in rows[1:]:
            nomi = row[col_mapping['nomi']].strip() if 'nomi' in col_mapping and len(row) > col_mapping['nomi'] else ""
            if not nomi:
                continue

            shtrix_kod = row[col_mapping['shtrix_kod']].strip() if 'shtrix_kod' in col_mapping and len(row) > col_mapping['shtrix_kod'] else ""
            
            miqdori_str = row[col_mapping['miqdori']].strip() if 'miqdori' in col_mapping and len(row) > col_mapping['miqdori'] else "0"
            try:
                miqdori = int(float(miqdori_str))
            except ValueError:
                miqdori = 0

            kelish_str = row[col_mapping['kelish_narxi']].strip() if 'kelish_narxi' in col_mapping and len(row) > col_mapping['kelish_narxi'] else "0"
            try:
                kelish_narxi = Decimal(kelish_str)
            except (ValueError, TypeError):
                kelish_narxi = Decimal('0.00')

            ustama_str = row[col_mapping['ustama']].strip() if 'ustama' in col_mapping and len(row) > col_mapping['ustama'] else "0"
            try:
                ustama = Decimal(ustama_str)
            except (ValueError, TypeError):
                ustama = Decimal('0.00')

            sotish_str = row[col_mapping['sotish_narxi']].strip() if 'sotish_narxi' in col_mapping and len(row) > col_mapping['sotish_narxi'] else "0"
            try:
                sotish_narxi = Decimal(sotish_str)
            except (ValueError, TypeError):
                sotish_narxi = Decimal('0.00')

            ulgurji_str = row[col_mapping['ulgurji_narx']].strip() if 'ulgurji_narx' in col_mapping and len(row) > col_mapping['ulgurji_narx'] else "0"
            try:
                ulgurji_narx = Decimal(ulgurji_str)
            except (ValueError, TypeError):
                ulgurji_narx = Decimal('0.00')

            product = None
            if shtrix_kod:
                try:
                    product = Mahsulot.objects.filter(biznes=biznes, shtrix_kodlar__kod=shtrix_kod).first()
                except Exception:
                    pass
            if not product:
                product = Mahsulot.objects.filter(biznes=biznes, nomi=nomi).first()

            if not product:
                if biznes and biznes.tarif:
                    limit = biznes.tarif.mahsulot_limiti
                    if Mahsulot.objects.filter(biznes=biznes).count() >= limit:
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
                if shtrix_kod:
                    MahsulotShtrixKod.objects.create(mahsulot=product, kod=shtrix_kod)

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
