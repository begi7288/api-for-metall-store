from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
import django_filters

from products.models import Transfer
from products.serializers import TransferSerializer
from user.permissions import IsAdminOrOmborchi
from .common import DynamicPagination

class TransferFilter(django_filters.FilterSet):
    jo_natish_sanasi = django_filters.DateFilter(field_name="yaratilgan_vaqt", lookup_expr='date')
    qabul_qilish_sanasi = django_filters.DateFilter(field_name="yangilangan_vaqt", lookup_expr='date')

    class Meta:
        model = Transfer
        fields = ['holat', 'dokondan', 'dokonga', 'jo_natish_sanasi', 'qabul_qilish_sanasi']


class TransferViewSet(viewsets.ModelViewSet):
    serializer_class = TransferSerializer
    permission_classes = [IsAdminOrOmborchi]
    pagination_class = DynamicPagination
    filterset_class = TransferFilter
    search_fields = ['id', 'nomi', 'dokondan__nomi', 'dokonga__nomi']
    ordering_fields = ['miqdori', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def get_queryset(self):
        user = self.request.user
        queryset = Transfer.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()

    def perform_create(self, serializer):
        biznes = None
        executor_xodim = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            executor_xodim = self.request.user.xodim
            biznes = executor_xodim.biznes
            
        try:
            transfer_obj = serializer.save(biznes=biznes, yaratgan_xodim=executor_xodim)
            from user.telegram_bot import notify_transfer
            notify_transfer(transfer_obj)
        except DjangoValidationError as e:
            if hasattr(e, 'message_dict'):
                raise DRFValidationError(e.message_dict)
            else:
                raise DRFValidationError({'detail': e.messages})
        
        try:
            transfer_obj.confirm_and_execute(executor_xodim=executor_xodim)
            transfer_obj.refresh_from_db()
        except Exception as e:
            raise DRFValidationError({'detail': str(e)})

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        transfer_obj = self.get_object()
        executor_xodim = None
        if request.user and hasattr(request.user, 'xodim'):
            executor_xodim = request.user.xodim
            
        try:
            transfer_obj.confirm_and_execute(executor_xodim=executor_xodim)
        except Exception as e:
            raise DRFValidationError({'detail': str(e)})
            
        return Response({
            'status': "Transfer muvaffaqiyatli yakunlandi.",
            'holat': transfer_obj.holat
        }, status=status.HTTP_200_OK)
