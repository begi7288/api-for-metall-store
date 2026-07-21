from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal

from .models import SodiqlikDasturi, SodiqlikDarajasi
from .permissions import IsEmployee


class SodiqlikDarajasiSerializer(serializers.ModelSerializer):
    nomi = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(source='nomi', required=False, allow_blank=True)
    xaridlar_summasi = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    minPurchaseAmount = serializers.DecimalField(source='xaridlar_summasi', max_digits=15, decimal_places=2, required=False)
    chegirma = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    discount = serializers.DecimalField(source='chegirma', max_digits=5, decimal_places=2, required=False)

    class Meta:
        model = SodiqlikDarajasi
        fields = [
            'id', 'biznes', 'nomi', 'name', 'xaridlar_summasi', 'minPurchaseAmount',
            'chegirma', 'discount', 'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def validate(self, attrs):
        if 'nomi' not in attrs:
            if self.instance and hasattr(self.instance, 'nomi'):
                attrs['nomi'] = self.instance.nomi
            else:
                attrs['nomi'] = "Chegirma"
        return attrs


class SodiqlikDasturiSerializer(serializers.ModelSerializer):
    turi_display = serializers.CharField(source='get_turi_display', read_only=True)
    darajalar = SodiqlikDarajasiSerializer(many=True, read_only=True, source='biznes.sodiqlik_darajalari')

    class Meta:
        model = SodiqlikDasturi
        fields = [
            'id', 'biznes', 'turi', 'turi_display', 'is_active', 'darajalar',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']


class LoyaltyViewSet(viewsets.ModelViewSet):
    serializer_class = SodiqlikDarajasiSerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        user = self.request.user
        queryset = SodiqlikDarajasi.objects.all().order_by('xaridlar_summasi')
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                return queryset.filter(biznes=user.xodim.biznes)
            return queryset.none()
        return queryset

    def create(self, request, *args, **kwargs):
        biznes = request.user.xodim.biznes if (request.user.is_authenticated and hasattr(request.user, 'xodim')) else None
        
        # Check if program type is passed
        turi = request.data.get('turi')
        if turi and biznes:
            dastur, _ = SodiqlikDasturi.objects.get_or_create(biznes=biznes)
            dastur.turi = turi
            dastur.save()

        # Handle list of tiers or payload containing 'darajalar' or 'tiers'
        tiers_data = None
        if isinstance(request.data, list):
            tiers_data = request.data
        elif isinstance(request.data, dict):
            if 'darajalar' in request.data:
                tiers_data = request.data['darajalar']
            elif 'tiers' in request.data:
                tiers_data = request.data['tiers']

        if tiers_data is not None:
            created_tiers = []
            if biznes:
                SodiqlikDarajasi.objects.filter(biznes=biznes).delete()
                for item in tiers_data:
                    nomi = item.get('nomi') or item.get('name') or 'Chegirma'
                    xaridlar = Decimal(str(item.get('xaridlar_summasi') or item.get('minPurchaseAmount') or '0.00'))
                    chegirma = Decimal(str(item.get('chegirma') or item.get('discount') or '0.00'))
                    tier = SodiqlikDarajasi.objects.create(
                        biznes=biznes,
                        nomi=nomi,
                        xaridlar_summasi=xaridlar,
                        chegirma=chegirma
                    )
                    created_tiers.append(tier)
            serializer = self.get_serializer(created_tiers, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        biznes = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            biznes = self.request.user.xodim.biznes
        serializer.save(biznes=biznes)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None
        dastur, _ = SodiqlikDasturi.objects.get_or_create(biznes=biznes) if biznes else (None, False)

        return Response({
            'turi': dastur.turi if dastur else 'chegirma',
            'turi_display': dastur.get_turi_display() if dastur else 'Chegirma tizimi',
            'is_active': dastur.is_active if dastur else True,
            'results': serializer.data,
            'count': len(serializer.data),
            'darajalar': serializer.data
        }, status=status.HTTP_200_OK)
