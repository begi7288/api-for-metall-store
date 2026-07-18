from rest_framework import serializers
from django.core.exceptions import ValidationError
from decimal import Decimal
from products.models import WriteOff, WriteOffItem, Dokon, DokonQoldiq, Mahsulot
from user.serializers import XSSSanitizerMixin

class WriteOffItemSerializer(serializers.ModelSerializer):
    mahsulot_nomi = serializers.ReadOnlyField(source='mahsulot.nomi')
    mahsulot_shtrix_kod = serializers.SerializerMethodField()

    class Meta:
        model = WriteOffItem
        fields = ['id', 'mahsulot', 'mahsulot_nomi', 'mahsulot_shtrix_kod', 'miqdori', 'kelish_narxi', 'sotish_narxi']
        read_only_fields = ['kelish_narxi', 'sotish_narxi']

    def get_mahsulot_shtrix_kod(self, obj):
        return obj.mahsulot.shtrix_kod if obj.mahsulot else None

    def validate(self, attrs):
        mahsulot = attrs.get('mahsulot')
        write_off = attrs.get('write_off')
        if not write_off and self.instance:
            write_off = self.instance.write_off
        
        if write_off and mahsulot:
            if not DokonQoldiq.objects.filter(mahsulot=mahsulot, dokon=write_off.dokon).exists():
                raise serializers.ValidationError({"mahsulot": f"'{mahsulot.nomi}' mahsuloti ushbu do'konda mavjud emas."})
        return attrs


class WriteOffSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    elementlar = WriteOffItemSerializer(many=True, required=False)
    dokon_nomi = serializers.ReadOnlyField(source='dokon.nomi')
    sababi_display = serializers.CharField(source='get_sababi_display', read_only=True)
    yaratgan_xodim_nomi = serializers.SerializerMethodField()
    tasdiqlagan_xodim_nomi = serializers.SerializerMethodField()
    tugash_sanasi = serializers.ReadOnlyField(source='yangilangan_vaqt')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            self.fields['dokon'].queryset = Dokon.objects.filter(biznes=biznes)

    class Meta:
        model = WriteOff
        fields = [
            'id', 'biznes', 'dokon', 'dokon_nomi', 'nomi', 'sababi', 'sababi_display',
            'holat', 'miqdori', 'kelish_summasi', 'sotish_summasi', 'fayl', 'fayldan_hisobdan_chiqarish',
            'elementlar', 'yaratgan_xodim', 'yaratgan_xodim_nomi',
            'tasdiqlagan_xodim', 'tasdiqlagan_xodim_nomi', 'yaratilgan_vaqt', 'yangilangan_vaqt', 'tugash_sanasi'
        ]
        read_only_fields = [
            'biznes', 'holat', 'miqdori', 'kelish_summasi', 'sotish_summasi',
            'yaratgan_xodim', 'tasdiqlagan_xodim', 'yaratilgan_vaqt', 'yangilangan_vaqt', 'tugash_sanasi'
        ]

    def get_yaratgan_xodim_nomi(self, obj):
        if obj.yaratgan_xodim:
            return f"{obj.yaratgan_xodim.ism} {obj.yaratgan_xodim.familiya}"
        return ""

    def get_tasdiqlagan_xodim_nomi(self, obj):
        if obj.tasdiqlagan_xodim:
            return f"{obj.tasdiqlagan_xodim.ism} {obj.tasdiqlagan_xodim.familiya}"
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

        fayldan = attrs.get('fayldan_hisobdan_chiqarish', self.instance.fayldan_hisobdan_chiqarish if self.instance else False)
        fayl = attrs.get('fayl')
        if fayldan and not fayl and not (self.instance and self.instance.fayl):
            raise serializers.ValidationError({"fayl": "Fayldan hisobdan chiqarish tanlanganda fayl yuklanishi shart."})

        return attrs

    def create(self, validated_data):
        elementlar_data = validated_data.pop('elementlar', [])
        fayl = validated_data.pop('fayl', None)
        fayldan = validated_data.get('fayldan_hisobdan_chiqarish', False)

        request = self.context.get('request')
        biznes = None
        yaratgan_xodim = None
        if request and request.user and hasattr(request.user, 'xodim'):
            yaratgan_xodim = request.user.xodim
            biznes = yaratgan_xodim.biznes

        write_off = WriteOff.objects.create(biznes=biznes, yaratgan_xodim=yaratgan_xodim, **validated_data)

        if fayldan and fayl:
            write_off.fayl = fayl
            write_off.save()
            self._parse_and_save_elements_from_file(fayl, write_off, biznes)
        elif not fayldan and elementlar_data:
            for item_data in elementlar_data:
                mahsulot = item_data['mahsulot']
                if biznes and mahsulot.biznes != biznes:
                    raise serializers.ValidationError({"elementlar": f"'{mahsulot.nomi}' mahsuloti sizning biznesingizga tegishli emas."})
                WriteOffItem.objects.create(
                    write_off=write_off,
                    mahsulot=mahsulot,
                    miqdori=item_data['miqdori'],
                    kelish_narxi=mahsulot.kelish_narxi or Decimal('0.00'),
                    sotish_narxi=mahsulot.sotish_narxi or Decimal('0.00')
                )

        return write_off

    def update(self, instance, validated_data):
        if instance.holat != 'qoralama':
            raise serializers.ValidationError({"detail": "Faqat qoralama holatidagi hujjatni tahrirlash mumkin."})

        elementlar_data = validated_data.pop('elementlar', None)
        fayl = validated_data.pop('fayl', None)
        fayldan = validated_data.get('fayldan_hisobdan_chiqarish', instance.fayldan_hisobdan_chiqarish)

        request = self.context.get('request')
        biznes = None
        if request and request.user and hasattr(request.user, 'xodim'):
            biznes = request.user.xodim.biznes

        instance = super().update(instance, validated_data)

        if fayldan and fayl:
            instance.fayl = fayl
            instance.save()
            instance.elementlar.all().delete()
            self._parse_and_save_elements_from_file(fayl, instance, biznes)
        elif not fayldan and elementlar_data is not None:
            instance.elementlar.all().delete()
            for item_data in elementlar_data:
                mahsulot = item_data['mahsulot']
                if biznes and mahsulot.biznes != biznes:
                    raise serializers.ValidationError({"elementlar": f"'{mahsulot.nomi}' mahsuloti sizning biznesingizga tegishli emas."})
                WriteOffItem.objects.create(
                    write_off=instance,
                    mahsulot=mahsulot,
                    miqdori=item_data['miqdori'],
                    kelish_narxi=mahsulot.kelish_narxi or Decimal('0.00'),
                    sotish_narxi=mahsulot.sotish_narxi or Decimal('0.00')
                )

        return instance

    def _parse_and_save_elements_from_file(self, file_obj, write_off, biznes):
        import csv
        import openpyxl
        from io import BytesIO
        
        file_name = file_obj.name
        file_obj.seek(0)
        content = file_obj.read()

        rows = []
        if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            wb = openpyxl.load_workbook(filename=BytesIO(content), data_only=True)
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
            elif any(k in h for k in ['shtrix', 'barcode', 'kod', 'код']):
                col_mapping['shtrix_kod'] = idx
            elif any(k in h for k in ['miqdor', 'qty', 'kol', 'hisobdan']):
                col_mapping['miqdori'] = idx
            elif any(k in h for k in ['kelish', 'cost', 'поставки']):
                col_mapping['kelish_narxi'] = idx

        if 'nomi' not in col_mapping and len(headers) > 0: col_mapping['nomi'] = 0
        if 'shtrix_kod' not in col_mapping and len(headers) > 1: col_mapping['shtrix_kod'] = 1
        if 'miqdori' not in col_mapping and len(headers) > 2: col_mapping['miqdori'] = 2
        if 'kelish_narxi' not in col_mapping and len(headers) > 3: col_mapping['kelish_narxi'] = 3

        for idx, row in enumerate(rows[1:], start=2):
            nomi = row[col_mapping['nomi']].strip() if 'nomi' in col_mapping and len(row) > col_mapping['nomi'] else ""
            if not nomi:
                continue

            shtrix_kod = row[col_mapping['shtrix_kod']].strip() if 'shtrix_kod' in col_mapping and len(row) > col_mapping['shtrix_kod'] else ""
            
            miqdori_str = row[col_mapping['miqdori']].strip() if 'miqdori' in col_mapping and len(row) > col_mapping['miqdori'] else "0"
            try:
                miqdori = int(float(miqdori_str))
            except ValueError:
                miqdori = 0

            if miqdori <= 0:
                raise serializers.ValidationError(f"Qator {idx}: Hisobdan chiqariladigan miqdor 0 dan katta bo'lishi shart.")

            kelish_str = row[col_mapping['kelish_narxi']].strip() if 'kelish_narxi' in col_mapping and len(row) > col_mapping['kelish_narxi'] else ""
            try:
                kelish_narxi = Decimal(kelish_str) if kelish_str else None
            except (ValueError, TypeError):
                kelish_narxi = None

            product = None
            if shtrix_kod:
                product = Mahsulot.objects.filter(biznes=biznes, shtrix_kodlar__kod=shtrix_kod).first()
            if not product:
                product = Mahsulot.objects.filter(biznes=biznes, nomi=nomi).first()

            if not product:
                raise serializers.ValidationError(f"Qator {idx}: Mahsulot bazada topilmadi (Nomi: '{nomi}', Shtrix-kod: '{shtrix_kod}').")

            qoldiq = DokonQoldiq.objects.filter(mahsulot=product, dokon=write_off.dokon).first()
            if not qoldiq or qoldiq.miqdori < miqdori:
                stock_qty = qoldiq.miqdori if qoldiq else 0
                raise serializers.ValidationError(f"Qator {idx}: '{product.nomi}' uchun do'konda yetarli qoldiq yo'q. Do'kondagi qoldiq: {stock_qty}, So'ralgan: {miqdori}.")

            WriteOffItem.objects.create(
                write_off=write_off,
                mahsulot=product,
                miqdori=miqdori,
                kelish_narxi=kelish_narxi or product.kelish_narxi or Decimal('0.00'),
                sotish_narxi=product.sotish_narxi or Decimal('0.00')
            )
