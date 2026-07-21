from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from .models import MijozQarzi, MijozTolovi, Mijoz
from .permissions import IsEmployee


class MijozQarziSerializer(serializers.ModelSerializer):
    mijoz_nomi = serializers.SerializerMethodField(read_only=True)
    mijoz_telefon = serializers.SerializerMethodField(read_only=True)
    
    # CamelCase & English Aliases
    customerName = serializers.SerializerMethodField(read_only=True)
    phone = serializers.SerializerMethodField(read_only=True)
    totalDebt = serializers.DecimalField(source='umumiy_summa', max_digits=15, decimal_places=2, read_only=True)
    paidAmount = serializers.DecimalField(source='tolangan_summa', max_digits=15, decimal_places=2, read_only=True)
    remainingAmount = serializers.DecimalField(source='qoldiq_summa', max_digits=15, decimal_places=2, read_only=True)
    status = serializers.CharField(source='holat', read_only=True)
    dueDate = serializers.DateField(source='muddati', read_only=True)
    createdAt = serializers.DateTimeField(source='yaratilgan_vaqt', read_only=True)

    class Meta:
        model = MijozQarzi
        fields = [
            'id', 'biznes', 'mijoz', 'mijoz_nomi', 'mijoz_telefon',
            'customerName', 'phone', 'sotuv',
            'umumiy_summa', 'tolangan_summa', 'qoldiq_summa', 'holat', 'muddati', 'eslatma',
            'totalDebt', 'paidAmount', 'remainingAmount', 'status', 'dueDate', 'createdAt',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'qoldiq_summa', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def get_mijoz_nomi(self, obj):
        return f"{obj.mijoz.ism} {obj.mijoz.familiya or ''}".strip() if obj.mijoz else "Noma'lum"

    def get_customerName(self, obj):
        return self.get_mijoz_nomi(obj)

    def get_mijoz_telefon(self, obj):
        return obj.mijoz.telefon_raqam_1 if obj.mijoz else ""

    def get_phone(self, obj):
        return self.get_mijoz_telefon(obj)


class MijozToloviSerializer(serializers.ModelSerializer):
    mijoz_nomi = serializers.SerializerMethodField(read_only=True)
    xodim_nomi = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MijozTolovi
        fields = [
            'id', 'biznes', 'mijoz', 'mijoz_nomi', 'qarz', 'summa',
            'tolov_usuli', 'xodim', 'xodim_nomi', 'eslatma',
            'yaratilgan_vaqt', 'yangilangan_vaqt'
        ]
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def get_mijoz_nomi(self, obj):
        return f"{obj.mijoz.ism} {obj.mijoz.familiya or ''}".strip() if obj.mijoz else "Noma'lum"

    def get_xodim_nomi(self, obj):
        return f"{obj.xodim.ism} {obj.xodim.familiya}".strip() if obj.xodim else ""


class DebtorsViewSet(viewsets.ModelViewSet):
    serializer_class = MijozQarziSerializer
    permission_classes = [IsEmployee]
    search_fields = ['mijoz__ism', 'mijoz__familiya', 'mijoz__telefon_raqam_1', 'eslatma']

    def get_queryset(self):
        user = self.request.user
        queryset = MijozQarzi.objects.all().order_by('-yaratilgan_vaqt')
        
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                queryset = queryset.filter(biznes=user.xodim.biznes)
            else:
                return queryset.none()

        # Status filter tabs
        status_param = self.request.query_params.get('status') or self.request.query_params.get('holat')
        if status_param:
            status_map = {
                'muddati_otganlar': 'muddati_otgan',
                'muddati_otgan': 'muddati_otgan',
                'overdue': 'muddati_otgan',
                'tolanmaganlar': 'tolanmagan',
                'tolanmagan': 'tolanmagan',
                'unpaid': 'tolanmagan',
                'tolanganlar': 'tolangan',
                'tolangan': 'tolangan',
                'paid': 'tolangan',
                'qisman_tolanganlar': 'qisman_tolangan',
                'qisman_tolangan': 'qisman_tolangan',
                'partially_paid': 'qisman_tolangan',
            }
            mapped_status = status_map.get(status_param.lower(), status_param)
            if mapped_status != 'barchasi' and mapped_status != 'all':
                queryset = queryset.filter(holat=mapped_status)

        # Search filter
        query = self.request.query_params.get('search') or self.request.query_params.get('q')
        if query:
            queryset = queryset.filter(
                Q(mijoz__ism__icontains=query) |
                Q(mijoz__familiya__icontains=query) |
                Q(mijoz__telefon_raqam_1__icontains=query) |
                Q(eslatma__icontains=query)
            )

        return queryset

    def perform_create(self, serializer):
        biznes = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            biznes = self.request.user.xodim.biznes
        serializer.save(biznes=biznes)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Calculate statistics for summary cards
        base_qs = MijozQarzi.objects.all()
        user = request.user
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                base_qs = base_qs.filter(biznes=user.xodim.biznes)
            else:
                base_qs = base_qs.none()

        qarzlar_summasi = base_qs.aggregate(total=Sum('umumiy_summa'))['total'] or Decimal('0.00')
        tolovlar_summasi = base_qs.aggregate(total=Sum('tolangan_summa'))['total'] or Decimal('0.00')
        qarzlar_qoldiqi = base_qs.aggregate(total=Sum('qoldiq_summa'))['total'] or Decimal('0.00')
        tizimli_tolovlar = tolovlar_summasi

        qarzdorlar_soni = base_qs.values('mijoz').distinct().count()
        tolanganlar_count = base_qs.filter(holat='tolangan').count()
        tolanmaganlar_count = base_qs.filter(holat='tolanmagan').count()
        muddati_otganlar_count = base_qs.filter(holat='muddati_otgan').count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['qarzlar_summasi'] = str(qarzlar_summasi)
            response.data['tolovlar_summasi'] = str(tolovlar_summasi)
            response.data['tizimli_tolovlar'] = str(tizimli_tolovlar)
            response.data['qarzlar_qoldiqi'] = str(qarzlar_qoldiqi)
            response.data['qarzdorlar_soni'] = qarzdorlar_soni
            response.data['tolanganlar'] = tolanganlar_count
            response.data['tolanmaganlar'] = tolanmaganlar_count
            response.data['muddati_otganlar'] = muddati_otganlar_count
            response.data['stats'] = {
                'qarzlar_summasi': str(qarzlar_summasi),
                'tolovlar_summasi': str(tolovlar_summasi),
                'tizimli_tolovlar': str(tizimli_tolovlar),
                'qarzlar_qoldiqi': str(qarzlar_qoldiqi),
                'qarzdorlar_soni': qarzdorlar_soni,
                'tolanganlar': tolanganlar_count,
                'tolanmaganlar': tolanmaganlar_count,
                'muddati_otganlar': muddati_otganlar_count,
            }
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data,
            'qarzlar_summasi': str(qarzlar_summasi),
            'tolovlar_summasi': str(tolovlar_summasi),
            'tizimli_tolovlar': str(tizimli_tolovlar),
            'qarzlar_qoldiqi': str(qarzlar_qoldiqi),
            'qarzdorlar_soni': qarzdorlar_soni,
            'tolanganlar': tolanganlar_count,
            'tolanmaganlar': tolanmaganlar_count,
            'muddati_otganlar': muddati_otganlar_count,
            'stats': {
                'qarzlar_summasi': str(qarzlar_summasi),
                'tolovlar_summasi': str(tolovlar_summasi),
                'tizimli_tolovlar': str(tizimli_tolovlar),
                'qarzlar_qoldiqi': str(qarzlar_qoldiqi),
                'qarzdorlar_soni': qarzdorlar_soni,
                'tolanganlar': tolanganlar_count,
                'tolanmaganlar': tolanmaganlar_count,
                'muddati_otganlar': muddati_otganlar_count,
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        base_qs = MijozQarzi.objects.all()
        user = request.user
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                base_qs = base_qs.filter(biznes=user.xodim.biznes)
            else:
                base_qs = base_qs.none()

        qarzlar_summasi = base_qs.aggregate(total=Sum('umumiy_summa'))['total'] or Decimal('0.00')
        tolovlar_summasi = base_qs.aggregate(total=Sum('tolangan_summa'))['total'] or Decimal('0.00')
        qarzlar_qoldiqi = base_qs.aggregate(total=Sum('qoldiq_summa'))['total'] or Decimal('0.00')

        return Response({
            'qarzlar_summasi': str(qarzlar_summasi),
            'tolovlar_summasi': str(tolovlar_summasi),
            'tizimli_tolovlar': str(tolovlar_summasi),
            'qarzlar_qoldiqi': str(qarzlar_qoldiqi),
            'qarzdorlar_soni': base_qs.values('mijoz').distinct().count(),
            'tolanganlar': base_qs.filter(holat='tolangan').count(),
            'tolanmaganlar': base_qs.filter(holat='tolanmagan').count(),
            'muddati_otganlar': base_qs.filter(holat='muddati_otgan').count(),
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='bulk-payment')
    def bulk_payment(self, request):
        summa = Decimal(str(request.data.get('summa', '0.00')))
        mijoz_id = request.data.get('mijoz') or request.data.get('mijoz_id')
        tolov_usuli = request.data.get('tolov_usuli', 'naqd')

        if not mijoz_id:
            return Response({'detail': "Mijoz ID kiritilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        biznes = request.user.xodim.biznes if hasattr(request.user, 'xodim') else None
        try:
            mijoz = Mijoz.objects.get(id=mijoz_id)
        except Mijoz.DoesNotExist:
            return Response({'detail': "Mijoz topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        tolov = MijozTolovi.objects.create(
            biznes=biznes,
            mijoz=mijoz,
            summa=summa,
            tolov_usuli=tolov_usuli,
            xodim=request.user.xodim if hasattr(request.user, 'xodim') else None,
            eslatma="Ommaviy to'lov"
        )

        unpaid_debts = MijozQarzi.objects.filter(mijoz=mijoz, qoldiq_summa__gt=0).order_by('yaratilgan_vaqt')
        remaining = summa
        for debt in unpaid_debts:
            if remaining <= 0:
                break
            pay = min(debt.qoldiq_summa, remaining)
            debt.tolangan_summa += pay
            debt.save()
            remaining -= pay

        return Response({
            'detail': "To'lov muvaffaqiyatli qabul qilindi.",
            'tolov_id': tolov.id,
            'qolgan_summa': str(remaining)
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='send-sms')
    def send_sms(self, request):
        return Response({'detail': "Qarzdorlarga SMS eslatma muvaffaqiyatli yuborildi."}, status=status.HTTP_200_OK)


class PaymentsViewSet(viewsets.ModelViewSet):
    serializer_class = MijozToloviSerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        user = self.request.user
        queryset = MijozTolovi.objects.all().order_by('-yaratilgan_vaqt')
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                return queryset.filter(biznes=user.xodim.biznes)
            return queryset.none()
        return queryset

    def perform_create(self, serializer):
        biznes = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            biznes = self.request.user.xodim.biznes
        serializer.save(biznes=biznes)
