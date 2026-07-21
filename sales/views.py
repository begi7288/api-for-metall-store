from rest_framework import viewsets
from django_filters import rest_framework as django_filters
from .models import Sale
from .serializers import SaleSerializer
from user.permissions import IsEmployee
from products.views.common import DynamicPagination

class SaleFilter(django_filters.FilterSet):
    sana = django_filters.DateFilter(field_name="yaratilgan_vaqt", lookup_expr='date')

    class Meta:
        model = Sale
        fields = ['holat', 'dokon', 'mijoz', 'tolov_usuli', 'xodim', 'sana']

class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [IsEmployee]
    pagination_class = DynamicPagination
    filterset_class = SaleFilter
    search_fields = ['kod', 'mijoz__ism', 'mijoz__familiya', 'xodim__ism', 'xodim__familiya']
    ordering_fields = ['oraliq_jami', 'yakuniy_summa', 'tolangan_summa', 'nasiya_summa', 'yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        queryset = Sale.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()
