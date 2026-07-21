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
            raise serializers.ValidationError({'nomi': "Nomi kiritilishi shart."})
        attrs['nomi'] = nomi
        attrs.pop('name', None)
        return attrs

class OlchovBirligiSerializer(serializers.ModelSerializer):
    nomi = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    short_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    shortName = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = OlchovBirligi
        fields = ['id', 'biznes', 'nomi', 'name', 'short_name', 'shortName']
        read_only_fields = ['biznes']

    def validate(self, attrs):
        nomi = attrs.get('nomi') or attrs.get('name')
        if not nomi:
            raise serializers.ValidationError({'nomi': "Nomi kiritilishi shart."})
        attrs['nomi'] = nomi
        attrs.pop('name', None)

        short_name = attrs.get('short_name') or attrs.get('shortName')
        attrs['short_name'] = short_name
        attrs.pop('shortName', None)
        return attrs

class XodimRoliSerializer(serializers.ModelSerializer):
    nomi = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    role_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    roleId = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = XodimRoli
        fields = ['id', 'biznes', 'nomi', 'name', 'role_id', 'roleId']
        read_only_fields = ['biznes']

    def validate(self, attrs):
        nomi = attrs.get('nomi') or attrs.get('name')
        if not nomi:
            raise serializers.ValidationError({'nomi': "Nomi kiritilishi shart."})
        attrs['nomi'] = nomi
        attrs.pop('name', None)

        role_id = attrs.get('role_id') or attrs.get('roleId')
        attrs['role_id'] = role_id
        attrs.pop('roleId', None)
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
        queryset = OlchovBirligi.objects.filter(biznes=biznes).order_by('id')
        
        if not queryset.exists():
            defaults = [
                ("Kilogramm", "kg"),
                ("Dona", "dona"),
                ("Metr", "metr"),
                ("Litr", "litr")
            ]
            units = [OlchovBirligi(biznes=biznes, nomi=d[0], short_name=d[1]) for d in defaults]
            OlchovBirligi.objects.bulk_create(units)
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

    def perform_create(self, serializer):
        serializer.save(biznes=self.request.user.xodim.biznes)


# ============================================================
# GET-only archive view
# ============================================================

class ArchiveListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        queryset = Mahsulot.objects.filter(is_active=False).prefetch_related('qoldiqlar', 'shtrix_kodlar').order_by('-yangilangan_vaqt')
        if user.is_superuser:
            pass
        elif hasattr(user, 'xodim') and user.xodim.biznes:
            queryset = queryset.filter(biznes=user.xodim.biznes)
        else:
            queryset = queryset.none()
            
        serializer = MahsulotSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
