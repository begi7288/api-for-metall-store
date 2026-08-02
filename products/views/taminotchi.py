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
    filterset_fields = ['is_active']
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
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                queryset = queryset.filter(biznes=user.xodim.biznes)
            else:
                return queryset.none()

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
        biznes = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            biznes = self.request.user.xodim.biznes
        serializer.save(biznes=biznes)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response({"detail": "Ta'minotchi muvaffaqiyatli arxivlandi."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        user = request.user
        base_qs = Taminotchi.objects.all()
        if not user.is_superuser and user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            base_qs = base_qs.filter(biznes=user.xodim.biznes)
        instance = base_qs.filter(pk=pk).first()
        if not instance:
            return Response({"detail": "Ta'minotchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        instance.is_active = True
        instance.save(update_fields=['is_active'])
        return Response({"detail": "Ta'minotchi muvaffaqiyatli tiklandi."}, status=status.HTTP_200_OK)

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
    def card(self, request, pk=None):
        taminotchi = self.get_object()
        serializer = self.get_serializer(taminotchi)
        data = serializer.data
        dash_resp = self.dashboard(request, pk=pk)
        data['dashboard'] = dash_resp.data
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def kartochka(self, request, pk=None):
        return self.card(request, pk=pk)

    @action(detail=True, methods=['get'], url_path='detail-card')
    def detail_card(self, request, pk=None):
        return self.card(request, pk=pk)

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
            "tolanganBuyurtmalarCount": paid_count,
            "tolanmagan_buyurtmalar_count": unpaid_count,
            "tolanmaganBuyurtmalarCount": unpaid_count,
            "buyurtmalar_summasi": str(buyurtmalar_summasi),
            "buyurtmalarSummasi": str(buyurtmalar_summasi),
            "tolovlar_summasi": str(tolovlar_summasi),
            "tolovlarSummasi": str(tolovlar_summasi),
            "qarz_summasi": str(qarz_summasi),
            "qarzSummasi": str(qarz_summasi),
            "buyurtma_qilingan_mahsulotlar": ordered_qty,
            "buyurtmaQilinganMahsulotlar": ordered_qty,
            "qabul_qilingan_mahsulotlar": received_qty,
            "qabulQilinganMahsulotlar": received_qty,
            "buyurtmalar_tezligi": speed,
            "buyurtmalarTezligi": speed,
            "qaytarish_summasi": str(qaytarish_summasi),
            "qaytarilgan_tolovlar_summasi": str(qaytarilgan_tolovlar_summasi)
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='payments')
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
                    p.order.nomi if p.order else "",
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
                "order_id": p.order.id if p.order else None,
                "order_nomi": p.order.nomi if p.order else "",
                "orderNomi": p.order.nomi if p.order else "",
                "tolangan_summa": str(p.tolangan_summa),
                "tolanganSumma": str(p.tolangan_summa),
                "tolov_summasi": str(p.tolangan_summa),
                "summa": str(p.tolangan_summa),
                "tolov_turi": p.get_tolov_turi_display(),
                "tolovTuri": p.get_tolov_turi_display(),
                "tolov_turi_raw": p.tolov_turi,
                "xodim_id": p.xodim.id if p.xodim else None,
                "xodim_nomi": f"{p.xodim.ism} {p.xodim.familiya}" if p.xodim else "",
                "xodimNomi": f"{p.xodim.ism} {p.xodim.familiya}" if p.xodim else "",
                "yaratilgan_vaqt": p.yaratilgan_vaqt,
                "sana": p.yaratilgan_vaqt,
                "vaqt": p.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M:%S") if p.yaratilgan_vaqt else ""
            })

        page = self.paginate_queryset(data)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        return self.payments(request, pk)

    @action(detail=True, methods=['get'], url_path='tolovlar')
    def tolovlar(self, request, pk=None):
        return self.payments(request, pk)

    @action(detail=True, methods=['get'], url_path='orders')
    def orders(self, request, pk=None):
        taminotchi = self.get_object()
        from orders.models import SupplierOrder
        from orders.serializers import SupplierOrderSerializer
        from django.db import models

        queryset = SupplierOrder.objects.filter(
            taminotchi=taminotchi
        ).order_by('-yaratilgan_vaqt')

        holat_param = request.query_params.get('holat')
        if holat_param and holat_param.lower() != 'barchasi':
            queryset = queryset.filter(holat=holat_param)

        status_param = (
            request.query_params.get('payment_status') or
            request.query_params.get('to_lov_status') or
            request.query_params.get('tolov_status')
        )
        if status_param and status_param.lower() != 'barchasi':
            if status_param == 'tolanmagan':
                queryset = queryset.filter(tolangan_summa=0)
            elif status_param == 'qisman_tolangan':
                queryset = queryset.filter(
                    tolangan_summa__gt=0,
                    tolangan_summa__lt=models.F('umumiy_summa')
                )
            elif status_param == 'tolangan':
                queryset = queryset.filter(
                    tolangan_summa=models.F('umumiy_summa'),
                    umumiy_summa__gt=0
                )

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(nomi__icontains=search) | models.Q(id__icontains=search)
            )

        if request.query_params.get('export') == 'excel':
            headers = ["ID", "Nomi", "Yetkazib beruvchi", "Do'kon", "Sana", "Holat", "Jami summa", "To'langan summa", "Nasiya summasi"]
            rows = []
            for item in queryset:
                rows.append([
                    item.id,
                    item.nomi,
                    item.taminotchi.nomi if item.taminotchi else "",
                    item.dokon.nomi if item.dokon else "",
                    item.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M") if item.yaratilgan_vaqt else "",
                    item.get_holat_display(),
                    str(item.umumiy_summa),
                    str(item.tolangan_summa),
                    str(item.nasiya_summa)
                ])
            return generate_excel_response(f"orders_{taminotchi.id}", headers, rows)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SupplierOrderSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = SupplierOrderSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='buyurtmalar')
    def buyurtmalar(self, request, pk=None):
        return self.orders(request, pk)

    @action(detail=True, methods=['get'], url_path='order-stats')
    def order_stats(self, request, pk=None):
        taminotchi = self.get_object()
        from orders.models import SupplierOrder
        from django.db import models
        qs = SupplierOrder.objects.filter(taminotchi=taminotchi)

        barchasi = qs.count()
        tolanmagan = qs.filter(tolangan_summa=0).count()
        qisman_tolangan = qs.filter(tolangan_summa__gt=0, tolangan_summa__lt=models.F('umumiy_summa')).count()
        tolangan = qs.filter(tolangan_summa=models.F('umumiy_summa'), umumiy_summa__gt=0).count()

        return Response({
            "barchasi": barchasi,
            "tolanmagan": tolanmagan,
            "qisman_tolangan": qisman_tolangan,
            "qismanTolangan": qisman_tolangan,
            "tolangan": tolangan
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='orders-stats')
    def orders_stats(self, request, pk=None):
        return self.order_stats(request, pk)

    @action(detail=True, methods=['get'], url_path='products')
    def products(self, request, pk=None):
        taminotchi = self.get_object()
        from products.models import Mahsulot
        from products.serializers import MahsulotSerializer
        from django.db import models

        queryset = Mahsulot.objects.filter(
            models.Q(taminotchi=taminotchi) | models.Q(xarid_elementlari__order__taminotchi=taminotchi)
        ).distinct().order_by('-yaratilgan_vaqt')

        if request.query_params.get('export') == 'excel':
            headers = ["ID", "Nomi", "Kelish narxi", "Sotish narxi", "Miqdori", "O'lchov birligi"]
            rows = []
            for item in queryset:
                rows.append([
                    item.id,
                    item.nomi,
                    str(item.kelish_narxi),
                    str(item.sotish_narxi),
                    item.miqdori,
                    item.olchov_birligi
                ])
            return generate_excel_response(f"products_{taminotchi.id}", headers, rows)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MahsulotSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = MahsulotSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='mahsulotlar')
    def mahsulotlar(self, request, pk=None):
        return self.products(request, pk)

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
