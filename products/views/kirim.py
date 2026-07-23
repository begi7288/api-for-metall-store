from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from decimal import Decimal

from ..models import Import, Dokon, Taminotchi
from ..serializers.kirim import KirimSerializer
from user.permissions import IsAdminOrOmborchi, IsEmployee

class KirimViewSet(viewsets.ModelViewSet):
    """
    Omborga kirim (Warehouse Manual Stock Inward) ViewSet.
    Provides API for manual stock entry form, listing inward entries, confirmation, and statistics.
    """
    queryset = Import.objects.filter(import_turi='kirim')
    serializer_class = KirimSerializer
    permission_classes = [IsAuthenticated, IsEmployee]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['dokon', 'taminotchi', 'tolov_turi', 'holat']
    search_fields = ['nomi', 'chek_raqami', 'elementlar__nomi', 'taminotchi__nomi']
    ordering_fields = ['yaratilgan_vaqt', 'kelish_summasi', 'miqdori']
    ordering = ['-yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        qs = Import.objects.filter(import_turi='kirim')
        if hasattr(user, 'xodim') and user.xodim.biznes:
            qs = qs.filter(biznes=user.xodim.biznes)
        elif not user.is_superuser:
            return qs.none()
        return qs.select_related('biznes', 'dokon', 'taminotchi', 'yaratgan_xodim', 'yakunlagan_xodim')

    def perform_create(self, serializer):
        user = self.request.user
        biznes = None
        executor_xodim = None
        if hasattr(user, 'xodim'):
            executor_xodim = user.xodim
            biznes = user.xodim.biznes

        dokon_id = self.request.data.get('dokon')
        dokon = None
        if dokon_id:
            try:
                dokon = Dokon.objects.get(id=dokon_id, biznes=biznes)
            except Dokon.DoesNotExist:
                pass
        if not dokon and hasattr(executor_xodim, 'dokon') and executor_xodim.dokon:
            dokon = executor_xodim.dokon

        try:
            kirim_obj = serializer.save(
                biznes=biznes,
                dokon=dokon,
                yaratgan_xodim=executor_xodim
            )
        except DjangoValidationError as e:
            if hasattr(e, 'message_dict'):
                raise DRFValidationError(e.message_dict)
            else:
                raise DRFValidationError({'detail': e.messages})

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        kirim_obj = self.get_object()
        if kirim_obj.holat == 'yakunlangan':
            return Response({
                'status': "Omborga kirim allaqachon yakunlangan.",
                'holat': kirim_obj.holat
            }, status=status.HTTP_200_OK)

        executor_xodim = request.user.xodim if hasattr(request.user, 'xodim') else None

        try:
            kirim_obj.confirm_and_execute(executor_xodim=executor_xodim)
            
            # If supplier & payment method is 'nasiya', track supplier debt
            if kirim_obj.taminotchi and kirim_obj.tolov_turi == 'nasiya':
                kirim_obj.taminotchi.balans += kirim_obj.kelish_summasi
                kirim_obj.taminotchi.save(update_fields=['balans'])

        except Exception as e:
            raise DRFValidationError({'detail': str(e)})

        return Response({
            'status': "Omborga kirim muvaffaqiyatli yakunlandi.",
            'holat': kirim_obj.holat
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        kirim_obj = self.get_object()
        if kirim_obj.holat == 'yakunlangan':
            raise DRFValidationError({'detail': "Yakunlangan kirimni bekor qilib bo'lmaydi."})

        kirim_obj.holat = 'bekor_qilingan'
        kirim_obj.save(update_fields=['holat'])

        return Response({
            'status': "Kirim bekor qilindi.",
            'holat': kirim_obj.holat
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        cheklar = queryset.count()
        soni = queryset.aggregate(total=Sum('miqdori'))['total'] or 0
        jami = queryset.aggregate(total=Sum('kelish_summasi'))['total'] or Decimal('0.00')

        return Response({
            'cheklar': cheklar,
            'soni': soni,
            'jami': str(jami)
        }, status=status.HTTP_200_OK)
