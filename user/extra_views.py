from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from products.models import Mahsulot, MahsulotToifasi, OlchovBirligi, Taminotchi, MahsulotBrend
from user.models import Xodim, XodimRoli
from products.serializers import MahsulotSerializer

# ============================================================
# Serializers
# ============================================================

class MahsulotBrendSerializer(serializers.ModelSerializer):
    nomi = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    brend = serializers.CharField(source='nomi', read_only=True)
    brand = serializers.CharField(source='nomi', read_only=True)

    class Meta:
        model = MahsulotBrend
        fields = ['id', 'biznes', 'nomi', 'name', 'brend', 'brand', 'is_active']
        read_only_fields = ['biznes']

    def validate(self, attrs):
        nomi = attrs.get('nomi') or attrs.get('name') or self.initial_data.get('brend') or self.initial_data.get('brand')
        if not nomi:
            if self.instance and hasattr(self.instance, 'nomi'):
                nomi = self.instance.nomi
            else:
                raise serializers.ValidationError({'nomi': "Nomi kiritilishi shart."})
        
        # Prevent duplicates (case-insensitive) for this business
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            qs = MahsulotBrend.objects.filter(biznes=biznes, nomi__iexact=nomi.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'nomi': "Bunday nomli brend allaqachon mavjud."})

        attrs['nomi'] = nomi.strip()
        attrs.pop('name', None)
        return attrs

class MahsulotToifasiSerializer(serializers.ModelSerializer):
    nomi = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    kategoriya = serializers.CharField(source='nomi', read_only=True)
    category = serializers.CharField(source='nomi', read_only=True)

    class Meta:
        model = MahsulotToifasi
        fields = ['id', 'biznes', 'nomi', 'name', 'kategoriya', 'category', 'is_active']
        read_only_fields = ['biznes']

    def validate(self, attrs):
        nomi = attrs.get('nomi') or attrs.get('name') or self.initial_data.get('kategoriya') or self.initial_data.get('category')
        if not nomi:
            if self.instance and hasattr(self.instance, 'nomi'):
                nomi = self.instance.nomi
            else:
                raise serializers.ValidationError({'nomi': "Nomi kiritilishi shart."})

        # Prevent duplicates (case-insensitive) for this business
        request = self.context.get('request')
        if request and request.user and hasattr(request.user, 'xodim') and request.user.xodim.biznes:
            biznes = request.user.xodim.biznes
            qs = MahsulotToifasi.objects.filter(biznes=biznes, nomi__iexact=nomi.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'nomi': "Bunday nomli kategoriya allaqachon mavjud."})

        attrs['nomi'] = nomi.strip()
        attrs.pop('name', None)
        return attrs

class OlchovBirligiSerializer(serializers.ModelSerializer):
    nomi = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    short_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    shortName = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    qisqa_nom = serializers.CharField(source='short_name', required=False, allow_null=True, allow_blank=True)
    qisqaNom = serializers.CharField(source='short_name', required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = OlchovBirligi
        fields = ['id', 'biznes', 'nomi', 'name', 'short_name', 'shortName', 'qisqa_nom', 'qisqaNom', 'is_active']
        read_only_fields = ['biznes']

    def validate(self, attrs):
        nomi = attrs.get('nomi') or attrs.get('name')
        if not nomi:
            if self.instance and hasattr(self.instance, 'nomi'):
                nomi = self.instance.nomi
            else:
                raise serializers.ValidationError({'nomi': "Nomi kiritilishi shart."})
        attrs['nomi'] = nomi
        attrs.pop('name', None)

        short_name = attrs.get('short_name') or attrs.get('shortName') or self.initial_data.get('qisqa_nom') or self.initial_data.get('qisqaNom')
        if short_name is None and self.instance and hasattr(self.instance, 'short_name'):
            short_name = self.instance.short_name
        attrs['short_name'] = short_name
        attrs.pop('shortName', None)
        return attrs

DEFAULT_PAGE_KEYS = [
    "dashboard", "sotuv_pos", "sotuvlar", "cheklar", "ombor", "kirimlar",
    "sozlamalar", "sales_panel", "taminotchilar", "kategoriyalar", "xodimlar",
    "lavozimlar", "olchov_birliklari", "mijozlar"
]

def get_default_huquqlar(role_id='admin'):
    role_id = str(role_id).lower().strip()
    res = {}
    for key in DEFAULT_PAGE_KEYS:
        view = False
        create = False
        edit = False
        delete = False
        
        if role_id == 'admin':
            view = create = edit = delete = True
        elif role_id == 'sotuvchi':
            if key in ('sotuv_pos', 'sotuvlar', 'mijozlar', 'cheklar'):
                view = create = edit = delete = True
        elif role_id == 'omborchi':
            if key in ('ombor', 'kirimlar', 'taminotchilar', 'kategoriyalar', 'olchov_birliklari'):
                view = create = edit = delete = True
                
        res[key] = {
            "view": view,
            "create": create,
            "edit": edit,
            "delete": delete
        }
    return res

class XodimRoliSerializer(serializers.ModelSerializer):
    nomi = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    role_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    roleId = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    huquqlar = serializers.JSONField(required=False, allow_null=True)
    permissions = serializers.JSONField(source='huquqlar', required=False, allow_null=True)

    class Meta:
        model = XodimRoli
        fields = ['id', 'biznes', 'nomi', 'name', 'role_id', 'roleId', 'huquqlar', 'permissions']
        read_only_fields = ['biznes']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['name'] = instance.nomi or ""
        ret['roleId'] = instance.role_id or ""
        if not ret.get('huquqlar'):
            ret['huquqlar'] = get_default_huquqlar(instance.role_id)
        ret['permissions'] = ret['huquqlar']
        return ret

    def validate(self, attrs):
        nomi = attrs.get('nomi') or attrs.get('name')
        if not nomi:
            if self.instance and hasattr(self.instance, 'nomi'):
                nomi = self.instance.nomi
            else:
                raise serializers.ValidationError({'nomi': "Nomi kiritilishi shart."})
        attrs['nomi'] = nomi
        attrs.pop('name', None)

        role_id = attrs.get('role_id') or attrs.get('roleId')
        if role_id is None and self.instance and hasattr(self.instance, 'role_id'):
            role_id = self.instance.role_id
        if not role_id:
            role_id = nomi.lower().replace(' ', '_')
        attrs['role_id'] = role_id
        attrs.pop('roleId', None)

        if 'huquqlar' in attrs:
            huquqlar = attrs.get('huquqlar')
            if not huquqlar:
                attrs['huquqlar'] = get_default_huquqlar(role_id)
        else:
            if not self.instance or not getattr(self.instance, 'huquqlar', None):
                attrs['huquqlar'] = get_default_huquqlar(role_id)
        return attrs


# ============================================================
# ViewSets
# ============================================================

class CategoriesViewSet(viewsets.ModelViewSet):
    serializer_class = MahsulotToifasiSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not hasattr(user, 'xodim') or not user.xodim.biznes:
            return MahsulotToifasi.objects.none()
        
        biznes = user.xodim.biznes
        if getattr(self, 'action', None) in ['destroy', 'retrieve', 'update', 'partial_update']:
            return MahsulotToifasi.objects.filter(biznes=biznes)

        queryset = MahsulotToifasi.objects.filter(biznes=biznes).order_by('nomi')
        if not queryset.exists() and not MahsulotToifasi.objects.filter(biznes=biznes).exists():
            existing_cats = Mahsulot.objects.filter(biznes=biznes).exclude(toifa__isnull=True).exclude(toifa="").values_list('toifa', flat=True).distinct()
            seen = set()
            for cat in existing_cats:
                cat_clean = cat.strip() if cat else ""
                if cat_clean and cat_clean.lower() not in seen:
                    seen.add(cat_clean.lower())
                    if not MahsulotToifasi.objects.filter(biznes=biznes, nomi__iexact=cat_clean).exists():
                        MahsulotToifasi.objects.get_or_create(biznes=biznes, nomi=cat_clean)
            queryset = MahsulotToifasi.objects.filter(biznes=biznes).order_by('nomi')

        is_active_param = self.request.query_params.get('is_active')
        archive_param = self.request.query_params.get('archive')
        if is_active_param is not None:
            val = is_active_param.lower() in ('true', '1', 'yes', 't')
            queryset = queryset.filter(is_active=val)
        elif archive_param is not None:
            val = archive_param.lower() in ('true', '1', 'yes', 't')
            queryset = queryset.filter(is_active=not val)
        else:
            queryset = queryset.filter(is_active=True)

        return queryset

    def perform_create(self, serializer):
        serializer.save(biznes=self.request.user.xodim.biznes)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response({"detail": "Kategoriya muvaffaqiyatli arxivlandi."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        user = request.user
        base_qs = MahsulotToifasi.objects.all()
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes and not user.is_superuser:
            base_qs = base_qs.filter(biznes=user.xodim.biznes)
        instance = base_qs.filter(pk=pk).first()
        if not instance:
            return Response({"detail": "Kategoriya topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        instance.is_active = True
        instance.save(update_fields=['is_active'])
        return Response({"detail": "Kategoriya muvaffaqiyatli tiklandi."}, status=status.HTTP_200_OK)


class BrandsViewSet(viewsets.ModelViewSet):
    serializer_class = MahsulotBrendSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']
    search_fields = ['nomi']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not hasattr(user, 'xodim') or not user.xodim.biznes:
            return MahsulotBrend.objects.none()
        
        biznes = user.xodim.biznes
        queryset = MahsulotBrend.objects.filter(biznes=biznes).order_by('nomi')
        if not queryset.exists() and not MahsulotBrend.objects.filter(biznes=biznes).exists():
            existing_brands = Mahsulot.objects.filter(biznes=biznes).exclude(brend__isnull=True).values_list('brend__nomi', flat=True).distinct()
            seen = set()
            for b in existing_brands:
                b_clean = b.strip() if b else ""
                if b_clean and b_clean.lower() not in seen:
                    seen.add(b_clean.lower())
                    if not MahsulotBrend.objects.filter(biznes=biznes, nomi__iexact=b_clean).exists():
                        MahsulotBrend.objects.get_or_create(biznes=biznes, nomi=b_clean)
            queryset = MahsulotBrend.objects.filter(biznes=biznes).order_by('nomi')

        is_active_param = self.request.query_params.get('is_active')
        archive_param = self.request.query_params.get('archive')
        if is_active_param is not None:
            val = is_active_param.lower() in ('true', '1', 'yes', 't')
            queryset = queryset.filter(is_active=val)
        elif archive_param is not None:
            val = archive_param.lower() in ('true', '1', 'yes', 't')
            queryset = queryset.filter(is_active=not val)
        else:
            queryset = queryset.filter(is_active=True)

        return queryset

    def perform_create(self, serializer):
        serializer.save(biznes=self.request.user.xodim.biznes)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response({"detail": "Brend muvaffaqiyatli arxivlandi."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        user = request.user
        base_qs = MahsulotBrend.objects.all()
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes and not user.is_superuser:
            base_qs = base_qs.filter(biznes=user.xodim.biznes)
        instance = base_qs.filter(pk=pk).first()
        if not instance:
            return Response({"detail": "Brend topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        instance.is_active = True
        instance.save(update_fields=['is_active'])
        return Response({"detail": "Brend muvaffaqiyatli tiklandi."}, status=status.HTTP_200_OK)


class UnitsViewSet(viewsets.ModelViewSet):
    serializer_class = OlchovBirligiSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not hasattr(user, 'xodim') or not user.xodim.biznes:
            return OlchovBirligi.objects.none()
        
        biznes = user.xodim.biznes
        if getattr(self, 'action', None) in ['destroy', 'retrieve', 'update', 'partial_update']:
            return OlchovBirligi.objects.filter(biznes=biznes)

        queryset = OlchovBirligi.objects.filter(biznes=biznes).order_by('id')

        is_active_param = self.request.query_params.get('is_active')
        archive_param = self.request.query_params.get('archive')
        if is_active_param is not None:
            val = is_active_param.lower() in ('true', '1', 'yes', 't')
            queryset = queryset.filter(is_active=val)
        elif archive_param is not None:
            val = archive_param.lower() in ('true', '1', 'yes', 't')
            queryset = queryset.filter(is_active=not val)
        else:
            queryset = queryset.filter(is_active=True)

        return queryset

    def perform_create(self, serializer):
        serializer.save(biznes=self.request.user.xodim.biznes)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response({"detail": "O'lchov birligi muvaffaqiyatli arxivlandi."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        user = request.user
        base_qs = OlchovBirligi.objects.all()
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes and not user.is_superuser:
            base_qs = base_qs.filter(biznes=user.xodim.biznes)
        instance = base_qs.filter(pk=pk).first()
        if not instance:
            return Response({"detail": "O'lchov birligi topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        instance.is_active = True
        instance.save(update_fields=['is_active'])
        return Response({"detail": "O'lchov birligi muvaffaqiyatli tiklandi."}, status=status.HTTP_200_OK)


class RolesViewSet(viewsets.ModelViewSet):
    serializer_class = XodimRoliSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not hasattr(user, 'xodim') or not user.xodim.biznes:
            return XodimRoli.objects.none()
        
        biznes = user.xodim.biznes
        return XodimRoli.objects.filter(biznes=biznes).order_by('id')

    def get_object(self):
        user = self.request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None
        
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        queryset = self.filter_queryset(self.get_queryset())
        
        from django.shortcuts import get_object_or_404
        if str(lookup_value).isdigit():
            filter_kwargs = {self.lookup_field: lookup_value}
        else:
            filter_kwargs = {'role_id': lookup_value}
            
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        serializer.save(biznes=self.request.user.xodim.biznes)


# ============================================================
# GET-only archive view
# ============================================================

class ArchiveListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes) else None
        
        archive_items = []

        # Debug logging to identify archive list behavior
        with open('c:/Temir Dokon/temirdokon_v1/error_log.txt', 'a', encoding='utf-8') as f:
            f.write(f"ArchiveListAPIView request by {user}: authenticated={user.is_authenticated}, hasattr_xodim={hasattr(user, 'xodim')}, biznes={biznes}\n")
        
        # Inactive Products
        products = Mahsulot.objects.filter(is_active=False).prefetch_related('qoldiqlar', 'shtrix_kodlar').order_by('-yangilangan_vaqt')
        if user.is_superuser:
            pass
        elif biznes:
            products = products.filter(biznes=biznes)
        else:
            products = products.none()

        search = request.query_params.get('search')
        if search:
            from django.db import models
            products = products.filter(
                models.Q(nomi__icontains=search) |
                models.Q(shtrix_kodlar__kod__icontains=search)
            ).distinct()

        for p in products:
            archive_items.append({
                "id": p.id,
                "tur": "Mahsulot",
                "type": "Mahsulot",
                "nomi": p.nomi,
                "name": p.nomi,
                "sana": p.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if p.yangilangan_vaqt else "",
                "date": p.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if p.yangilangan_vaqt else "",
                "holat": "O'chirilgan",
                "status": "O'chirilgan"
            })

        # Inactive Suppliers (Ta'minotchilar)
        suppliers = Taminotchi.objects.filter(is_active=False).order_by('-yangilangan_vaqt')
        if user.is_superuser:
            pass
        elif biznes:
            suppliers = suppliers.filter(biznes=biznes)
        else:
            suppliers = suppliers.none()

        if search:
            from django.db import models
            suppliers = suppliers.filter(
                models.Q(nomi__icontains=search) |
                models.Q(telefon_raqam__icontains=search)
            )

        for s in suppliers:
            archive_items.append({
                "id": s.id,
                "tur": "Ta'minotchi",
                "type": "Ta'minotchi",
                "nomi": s.nomi,
                "name": s.nomi,
                "boshliq": s.yuridik_nomi or "",
                "manzil": s.yuridik_manzil or "",
                "telefon": s.telefon_raqam or "",
                "phone": s.telefon_raqam or "",
                "sana": s.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if s.yangilangan_vaqt else "",
                "date": s.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if s.yangilangan_vaqt else "",
                "holat": "O'chirilgan",
                "status": "O'chirilgan"
            })

        # Inactive Categories (Kategoriyalar)
        categories = MahsulotToifasi.objects.filter(is_active=False).order_by('-yangilangan_vaqt')
        if user.is_superuser:
            pass
        elif biznes:
            categories = categories.filter(biznes=biznes)
        else:
            categories = categories.none()

        if search:
            from django.db import models
            categories = categories.filter(models.Q(nomi__icontains=search))

        for c in categories:
            archive_items.append({
                "id": c.id,
                "tur": "Kategoriya",
                "type": "Kategoriya",
                "nomi": c.nomi,
                "name": c.nomi,
                "sana": c.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if c.yangilangan_vaqt else "",
                "date": c.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if c.yangilangan_vaqt else "",
                "holat": "O'chirilgan",
                "status": "O'chirilgan"
            })

        # Inactive Brands (Brendlar)
        brands = MahsulotBrend.objects.filter(is_active=False).order_by('-yangilangan_vaqt')
        if user.is_superuser:
            pass
        elif biznes:
            brands = brands.filter(biznes=biznes)
        else:
            brands = brands.none()

        if search:
            from django.db import models
            brands = brands.filter(models.Q(nomi__icontains=search))

        for b in brands:
            archive_items.append({
                "id": b.id,
                "tur": "Brend",
                "type": "Brend",
                "nomi": b.nomi,
                "name": b.nomi,
                "sana": b.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if b.yangilangan_vaqt else "",
                "date": b.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if b.yangilangan_vaqt else "",
                "holat": "O'chirilgan",
                "status": "O'chirilgan"
            })

        # Inactive Units (O'lchov birliklari)
        units = OlchovBirligi.objects.filter(is_active=False).order_by('-yangilangan_vaqt')
        if user.is_superuser:
            pass
        elif biznes:
            units = units.filter(biznes=biznes)
        else:
            units = units.none()

        if search:
            from django.db import models
            units = units.filter(models.Q(nomi__icontains=search) | models.Q(short_name__icontains=search))

        for u in units:
            archive_items.append({
                "id": u.id,
                "tur": "O'lchov birligi",
                "type": "O'lchov birligi",
                "nomi": u.nomi,
                "name": u.nomi,
                "sana": u.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if u.yangilangan_vaqt else "",
                "date": u.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M") if u.yangilangan_vaqt else "",
                "holat": "O'chirilgan",
                "status": "O'chirilgan"
            })

        tur_param = (request.query_params.get('tur') or request.query_params.get('type') or request.query_params.get('entity') or '').lower()
        if tur_param:
            if tur_param in ['mahsulot', 'product', 'products']:
                archive_items = [i for i in archive_items if i.get('tur') == 'Mahsulot']
            elif tur_param in ['taminotchi', 'supplier', 'suppliers', 'taminotchilar']:
                archive_items = [i for i in archive_items if i.get('tur') == "Ta'minotchi"]
            elif tur_param in ['kategoriya', 'category', 'categories', 'kategoriyalar']:
                archive_items = [i for i in archive_items if i.get('tur') == 'Kategoriya']
            elif tur_param in ['brend', 'brand', 'brands', 'brendlar']:
                archive_items = [i for i in archive_items if i.get('tur') == 'Brend']
            elif tur_param in ['olchov', 'unit', 'units', 'olchov_birligi', 'olchov_birliklari', 'olchov-birliklari']:
                archive_items = [i for i in archive_items if i.get('tur') == "O'lchov birligi"]

        return Response(archive_items, status=status.HTTP_200_OK)
