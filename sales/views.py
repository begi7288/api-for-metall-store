from rest_framework import viewsets
from django_filters import rest_framework as django_filters
from .models import Sale
from .serializers import SaleSerializer
from user.permissions import IsEmployee
from products.views.common import DynamicPagination, generate_excel_response

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

    def list(self, request, *args, **kwargs):
        if request.query_params.get('export') == 'excel':
            queryset = self.filter_queryset(self.get_queryset())
            headers = ["ID/Kod", "Mijoz", "Do'kon", "Sotuvchi", "Sana", "Oraliq jami", "Chegirma summasi", "Yakuniy summa", "Eslatma"]
            rows = []
            for item in queryset:
                rows.append([
                    item.kod,
                    f"{item.mijoz.ism} {item.mijoz.familiya}" if item.mijoz else "Anonim Mijoz",
                    item.dokon.nomi if item.dokon else "",
                    f"{item.xodim.ism} {item.xodim.familiya}" if item.xodim else "",
                    item.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M") if item.yaratilgan_vaqt else "",
                    str(item.oraliq_jami),
                    str(item.chegirma_summasi),
                    str(item.yakuniy_summa),
                    item.eslatma or ""
                ])
            return generate_excel_response("sotuvlar", headers, rows)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = Sale.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()
