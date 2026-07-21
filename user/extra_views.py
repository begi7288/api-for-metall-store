from rest_framework import serializers, viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from products.models import Mahsulot, MahsulotToifasi, OlchovBirligi
from user.models import Xodim, XodimRoli
from products.serializers import MahsulotSerializer

# ============================================================
# Serializers
# ============================================================

class MahsulotToifasiSerializer(serializers.ModelSerializer):
    nomi = serializers.CharField(required=False)
    name = serializers.CharField(required=False)

    class Meta:
        model = MahsulotToifasi
        fields = ['id', 'biznes', 'nomi', 'name']
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
        fields = ['id', 'biznes', 'nomi', 'name', 'short_name', 'shortName', 'qisqa_nom', 'qisqaNom']
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
    is_admin = (role_id == 'admin')
    return {
        key: {
            "view": True,
            "create": is_admin,
            "edit": is_admin,
            "delete": is_admin
        }
        for key in DEFAULT_PAGE_KEYS
    }

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

        huquqlar = attrs.get('huquqlar')
        if not huquqlar:
            attrs['huquqlar'] = get_default_huquqlar(role_id)
        return attrs


# ============================================================
# ViewSets (with auto-population fallbacks)
# ============================================================

class CategoriesViewSet(viewsets.ModelViewSet):
    serializer_class = MahsulotToifasiSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not hasattr(user, 'xodim') or not user.xodim.biznes:
            return MahsulotToifasi.objects.none()
        
        biznes = user.xodim.biznes
        queryset = MahsulotToifasi.objects.filter(biznes=biznes).order_by('nomi')
        
        if not queryset.exists():
            existing_cats = Mahsulot.objects.filter(biznes=biznes).exclude(toifa__isnull=True).exclude(toifa="").values_list('toifa', flat=True).distinct()
            cats_to_create = list(existing_cats)
            if not cats_to_create:
                cats_to_create = ["Sement", "Armatura", "Taxta"]
            
            toifalar = [MahsulotToifasi(biznes=biznes, nomi=cat) for cat in cats_to_create]
            MahsulotToifasi.objects.bulk_create(toifalar)
            queryset = MahsulotToifasi.objects.filter(biznes=biznes).order_by('nomi')
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(biznes=self.request.user.xodim.biznes)


class UnitsViewSet(viewsets.ModelViewSet):
    serializer_class = OlchovBirligiSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not hasattr(user, 'xodim') or not user.xodim.biznes:
            return OlchovBirligi.objects.none()
        
        biznes = user.xodim.biznes
        defaults = [
            ("Kilogramm", "kg"),
            ("Dona", "dona"),
            ("Metr", "metr"),
            ("Litr", "litr")
        ]
        for nomi, short_name in defaults:
            if not OlchovBirligi.objects.filter(biznes=biznes, short_name=short_name).exists():
                OlchovBirligi.objects.create(biznes=biznes, nomi=nomi, short_name=short_name)
        
        queryset = OlchovBirligi.objects.filter(biznes=biznes).order_by('id')
        return queryset

    def perform_create(self, serializer):
        serializer.save(biznes=self.request.user.xodim.biznes)


class RolesViewSet(viewsets.ModelViewSet):
    serializer_class = XodimRoliSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not hasattr(user, 'xodim') or not user.xodim.biznes:
            return XodimRoli.objects.none()
        
        biznes = user.xodim.biznes
        queryset = XodimRoli.objects.filter(biznes=biznes).order_by('id')
        
        if not queryset.exists():
            defaults = [
                ("Administrator", "admin"),
                ("Omborchi", "omborchi"),
                ("Sotuvchi", "sotuvchi")
            ]
            roles = [XodimRoli(biznes=biznes, nomi=d[0], role_id=d[1]) for d in defaults]
            XodimRoli.objects.bulk_create(roles)
            queryset = XodimRoli.objects.filter(biznes=biznes).order_by('id')
            
        return queryset

    def get_object(self):
        user = self.request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None
        
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        
        # Ensure default roles exist if we are looking up by string and it's a default role name
        if biznes and not str(lookup_value).isdigit() and lookup_value in ('admin', 'omborchi', 'sotuvchi'):
            if not XodimRoli.objects.filter(biznes=biznes, role_id=lookup_value).exists():
                defaults = [
                    ("Administrator", "admin"),
                    ("Omborchi", "omborchi"),
                    ("Sotuvchi", "sotuvchi")
                ]
                roles_to_create = []
                for nomi, rid in defaults:
                    if not XodimRoli.objects.filter(biznes=biznes, role_id=rid).exists():
                        roles_to_create.append(XodimRoli(biznes=biznes, nomi=nomi, role_id=rid))
                if roles_to_create:
                    XodimRoli.objects.bulk_create(roles_to_create)

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

        return Response(archive_items, status=status.HTTP_200_OK)
