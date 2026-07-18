from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from decimal import Decimal

from products.models import Taminotchi
from products.serializers import TaminotchiSerializer
from user.permissions import IsAdminOrOmborchiOrReadOnly
from .common import DynamicPagination, generate_excel_response

class TaminotchiViewSet(viewsets.ModelViewSet):
    serializer_class = TaminotchiSerializer
    permission_classes = [IsAdminOrOmborchiOrReadOnly]
    pagination_class = DynamicPagination
    search_fields = ['=id', 'nomi', 'telefon_raqam']
    ordering_fields = ['nomi', 'balans', 'yaratilgan_vaqt']

    def list(self, request, *args, **kwargs):
        if request.query_params.get('export') == 'excel':
            queryset = self.filter_queryset(self.get_queryset())
            headers = ["ID", "Nomi", "Qarz summasi", "Buyurtmalar summasi", "To'lovlar summasi", "Tovarlar soni", "Telefon", "Balans"]
            rows = []
            for item in queryset:
                serializer = self.get_serializer(item)
                rows.append([
                    item.id,
                    item.nomi,
                    str(serializer.data.get('qarz_summasi', '0.00')),
                    str(serializer.data.get('buyurtmalar_summasi', '0.00')),
                    str(serializer.data.get('tolovlar_summasi', '0.00')),
                    serializer.data.get('tovarlar_soni', 0),
                    item.telefon_raqam or "",
                    str(item.balans)
                ])
            return generate_excel_response("taminotchilar", headers, rows)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = Taminotchi.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()

    def perform_create(self, serializer):
        biznes = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            biznes = self.request.user.xodim.biznes
        serializer.save(biznes=biznes)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        taminotchi = self.get_object()
        amount = request.data.get('amount')
        tolov_turi = request.data.get('tolov_turi')

        if not amount or not tolov_turi:
            return Response({"detail": "amount va tolov_turi kiritilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount_decimal = Decimal(str(amount))
        except Exception:
            return Response({"detail": "amount noto'g'ri formatda."}, status=status.HTTP_400_BAD_REQUEST)

        if amount_decimal <= 0:
            return Response({"detail": "To'lov summasi noldan katta bo'lishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        employee = request.user.xodim if hasattr(request.user, 'xodim') else None

        orders = taminotchi.xarid_buyurtmalari.filter(
            holat__in=['rasmiylashtirilgan', 'qabul_qilingan'],
            nasiya_summa__gt=0
        ).order_by('yaratilgan_vaqt')

        remaining = amount_decimal

        from django.db import transaction
        try:
            with transaction.atomic():
                for order in orders:
                    if remaining <= 0:
                        break
                    pay_to_order = min(order.nasiya_summa, remaining)
                    order.add_payment(pay_to_order, tolov_turi, employee)
                    remaining -= pay_to_order

                if remaining > 0:
                    taminotchi.balans += remaining
                    taminotchi.save()
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "To'lov muvaffaqiyatli amalga oshirildi.",
            "tolangan_summa": str(amount_decimal),
            "taminotchi_balansi": str(taminotchi.balans)
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        taminotchi = self.get_object()
        from django.db.models import Sum
        from django.utils.timezone import now
        from datetime import timedelta

        balans = taminotchi.balans

        paid_count = taminotchi.xarid_buyurtmalari.filter(
            holat__in=['rasmiylashtirilgan', 'qabul_qilingan'], 
            nasiya_summa=0
        ).count()

        unpaid_count = taminotchi.xarid_buyurtmalari.filter(
            holat__in=['rasmiylashtirilgan', 'qabul_qilingan'], 
            nasiya_summa__gt=0
        ).count()

        sums = taminotchi.xarid_buyurtmalari.exclude(holat='bekor_qilingan').aggregate(
            buyurtmalar=Sum('umumiy_summa'),
            tolovlar=Sum('tolangan_summa'),
            qarz=Sum('nasiya_summa')
        )
        buyurtmalar_summasi = sums['buyurtmalar'] or Decimal('0.00')
        tolovlar_summasi = sums['tolovlar'] or Decimal('0.00')
        qarz_summasi = sums['qarz'] or Decimal('0.00')

        ordered_qty = taminotchi.xarid_buyurtmalari.filter(
            holat__in=['qoralama', 'rasmiylashtirilgan']
        ).aggregate(total=Sum('elementlar__miqdori'))['total'] or 0

        received_qty = taminotchi.xarid_buyurtmalari.filter(
            holat='qabul_qilingan'
        ).aggregate(total=Sum('elementlar__miqdori'))['total'] or 0

        last_30_days = now() - timedelta(days=30)
        speed = taminotchi.xarid_buyurtmalari.exclude(
            holat='bekor_qilingan'
        ).filter(yaratilgan_vaqt__gte=last_30_days).count()

        qaytarish_summasi = taminotchi.xarid_qaytarishlari.exclude(
            holat='bekor_qilingan'
        ).aggregate(total=Sum('qaytarish_summasi'))['total'] or Decimal('0.00')

        qaytarilgan_tolovlar_summasi = taminotchi.xarid_qaytarishlari.filter(
            holat='yakunlangan'
        ).aggregate(total=Sum('qaytarish_summasi'))['total'] or Decimal('0.00')

        return Response({
            "balans": str(balans),
            "tolangan_buyurtmalar_count": paid_count,
            "tolanmagan_buyurtmalar_count": unpaid_count,
            "buyurtmalar_summasi": str(buyurtmalar_summasi),
            "tolovlar_summasi": str(tolovlar_summasi),
            "qarz_summasi": str(qarz_summasi),
            "buyurtma_qilingan_mahsulotlar": ordered_qty,
            "qabul_qilingan_mahsulotlar": received_qty,
            "buyurtmalar_tezligi": speed,
            "qaytarish_summasi": str(qaytarish_summasi),
            "qaytarilgan_tolovlar_summasi": str(qaytarilgan_tolovlar_summasi)
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        taminotchi = self.get_object()
        from orders.models import SupplierOrderPayment
        payments = SupplierOrderPayment.objects.filter(
            order__taminotchi=taminotchi
        ).order_by('-yaratilgan_vaqt')
        
        if request.query_params.get('export') == 'excel':
            headers = ["ID", "Buyurtma", "To'lov summasi", "To'lov turi", "Xodim", "Vaqt"]
            rows = []
            for p in payments:
                rows.append([
                    p.id,
                    p.order.nomi,
                    str(p.tolangan_summa),
                    p.get_tolov_turi_display(),
                    f"{p.xodim.ism} {p.xodim.familiya}" if p.xodim else "",
                    p.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M:%S") if p.yaratilgan_vaqt else ""
                ])
            return generate_excel_response(f"payments_{taminotchi.id}", headers, rows)
            
        data = []
        for p in payments:
            data.append({
                "id": p.id,
                "order_id": p.order.id,
                "order_nomi": p.order.nomi,
                "tolangan_summa": str(p.tolangan_summa),
                "tolov_turi": p.get_tolov_turi_display(),
                "tolov_turi_raw": p.tolov_turi,
                "xodim_nomi": f"{p.xodim.ism} {p.xodim.familiya}" if p.xodim else "",
                "yaratilgan_vaqt": p.yaratilgan_vaqt
            })
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        
        from django.db.models import Sum
        from orders.models import SupplierOrder
        
        taminotchi_ids = queryset.values_list('id', flat=True)
        
        orders = SupplierOrder.objects.filter(
            taminotchi_id__in=taminotchi_ids
        ).exclude(holat='bekor_qilingan')
        
        sums = orders.aggregate(
            buyurtmalar=Sum('umumiy_summa'),
            tolovlar=Sum('tolangan_summa'),
            qarz=Sum('nasiya_summa')
        )
        
        return Response({
            "yetkazib_beruvchilar_soni": queryset.count(),
            "umumiy_buyurtmalar_summasi": str(sums['buyurtmalar'] or Decimal('0.00')),
            "umumiy_tolovlar_summasi": str(sums['tolovlar'] or Decimal('0.00')),
            "umumiy_qarz_summasi": str(sums['qarz'] or Decimal('0.00'))
        }, status=status.HTTP_200_OK)
