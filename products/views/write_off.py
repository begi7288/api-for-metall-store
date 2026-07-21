from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
import django_filters
import openpyxl
from django.http import HttpResponse

from products.models import WriteOff
from products.serializers import WriteOffSerializer
from user.permissions import IsAdminOrOmborchi
from .common import DynamicPagination, generate_excel_response

class WriteOffFilter(django_filters.FilterSet):
    sana = django_filters.DateFilter(field_name="yaratilgan_vaqt", lookup_expr='date')

    class Meta:
        model = WriteOff
        fields = ['holat', 'sababi', 'dokon', 'sana']


class WriteOffViewSet(viewsets.ModelViewSet):
    serializer_class = WriteOffSerializer
    permission_classes = [IsAdminOrOmborchi]
    pagination_class = DynamicPagination
    filterset_class = WriteOffFilter
    search_fields = ['=id', 'nomi', 'dokon__nomi']
    ordering_fields = ['miqdori', 'kelish_summasi', 'sotish_summasi', 'yaratgan_vaqt']

    def list(self, request, *args, **kwargs):
        if request.query_params.get('export') == 'excel':
            queryset = self.filter_queryset(self.get_queryset())
            headers = ["ID", "Sababi", "Do'kon", "Sana", "Jami qiymati", "Tugash sanasi", "Yaratgan xodim"]
            rows = []
            for item in queryset:
                rows.append([
                    item.id,
                    item.get_sababi_display() if hasattr(item, 'get_sababi_display') else item.sababi,
                    item.dokon.nomi if item.dokon else "",
                    item.sana.strftime("%d.%m.%Y") if item.sana else "",
                    str(item.sotish_summasi),
                    item.yangilangan_vaqt.strftime("%d.%m.%Y %H:%M:%S") if item.yangilangan_vaqt else "",
                    f"{item.yaratgan_xodim.ism} {item.yaratgan_xodim.familiya}" if item.yaratgan_xodim else ""
                ])
            return generate_excel_response("hisobdan_chiqarishlar", headers, rows)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = WriteOff.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.holat != 'qoralama':
            return Response(
                {"detail": "Faqat qoralama holatidagi hisobdan chiqarishlarni o'zgartirish mumkin."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.holat != 'qoralama':
            return Response(
                {"detail": "Faqat qoralama holatidagi hisobdan chiqarishlarni o'chirish mumkin."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        write_off_obj = self.get_object()
        xodim = request.user.xodim if hasattr(request.user, 'xodim') else None
        try:
            write_off_obj.confirm_and_execute(executor_xodim=xodim)
            from user.telegram_bot import notify_write_off
            notify_write_off(write_off_obj)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'detail': str(e)})
        return Response({
            'status': "Muvaffaqiyatli hisobdan chiqarildi.",
            'holat': write_off_obj.holat
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        write_off_obj = self.get_object()
        try:
            write_off_obj.bekor_qilish()
        except DjangoValidationError as e:
            raise serializers.ValidationError({'detail': str(e)})
        return Response({
            'status': "Hisobdan chiqarish bekor qilindi.",
            'holat': write_off_obj.holat
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def template(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Shablon"
        
        headers = ["Nomi", "Shtrix-kod", "Miqdori", "Kelish narxi"]
        ws.append(headers)
        ws.append(["Armatura", "9948493123", "5", "40000"])
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=hisobdan_chiqarish_shablon.xlsx'
        wb.save(response)
        return response
