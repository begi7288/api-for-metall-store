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

    customer_name = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)
    first_name = serializers.SerializerMethodField(read_only=True)
    last_name = serializers.SerializerMethodField(read_only=True)

    # Common aliases for UI compatibility
    umumiySumma = serializers.DecimalField(source='umumiy_summa', max_digits=15, decimal_places=2, read_only=True)
    tolanganSumma = serializers.DecimalField(source='tolangan_summa', max_digits=15, decimal_places=2, read_only=True)
    qoldiqSumma = serializers.DecimalField(source='qoldiq_summa', max_digits=15, decimal_places=2, read_only=True)
    qoldiq = serializers.DecimalField(source='qoldiq_summa', max_digits=15, decimal_places=2, read_only=True)
    qarz = serializers.DecimalField(source='qoldiq_summa', max_digits=15, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(source='qoldiq_summa', max_digits=15, decimal_places=2, read_only=True)
    amount = serializers.DecimalField(source='qoldiq_summa', max_digits=15, decimal_places=2, read_only=True)
    shop = serializers.SerializerMethodField(read_only=True)
    store = serializers.SerializerMethodField(read_only=True)
    dokon = serializers.SerializerMethodField(read_only=True)
    due_date = serializers.SerializerMethodField(read_only=True)
    sana = serializers.SerializerMethodField(read_only=True)
    oxirgi_tolov = serializers.SerializerMethodField(read_only=True)
    oxirgiTolov = serializers.SerializerMethodField(read_only=True)
    lastPaymentDate = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MijozQarzi
        fields = [
            'id', 'biznes', 'mijoz', 'mijoz_nomi', 'mijoz_telefon',
            'customerName', 'phone', 'sotuv',
            'customer_name', 'name', 'first_name', 'last_name',
            'umumiy_summa', 'tolangan_summa', 'qoldiq_summa', 'holat', 'muddati', 'eslatma',
            'totalDebt', 'paidAmount', 'remainingAmount', 'status', 'dueDate', 'createdAt',
            'yaratilgan_vaqt', 'yangilangan_vaqt',
            'umumiySumma', 'tolanganSumma', 'qoldiqSumma', 'qoldiq', 'qarz', 'balance', 'amount',
            'shop', 'store', 'dokon', 'due_date', 'sana',
            'oxirgi_tolov', 'oxirgiTolov', 'lastPaymentDate'
        ]
        read_only_fields = ['biznes', 'qoldiq_summa', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def get_oxirgi_tolov(self, obj):
        if obj.mijoz:
            last_pay = obj.mijoz.tolovlar.order_by('-yaratilgan_vaqt').first()
            if last_pay and last_pay.yaratilgan_vaqt:
                return last_pay.yaratilgan_vaqt.strftime("%d.%m.%Y")
        return "-"

    def get_oxirgiTolov(self, obj):
        return self.get_oxirgi_tolov(obj)

    def get_lastPaymentDate(self, obj):
        return self.get_oxirgi_tolov(obj)

    def get_shop(self, obj):
        if obj.sotuv and obj.sotuv.dokon:
            return obj.sotuv.dokon.nomi
        return ""

    def get_store(self, obj):
        return self.get_shop(obj)

    def get_dokon(self, obj):
        return self.get_shop(obj)

    def get_due_date(self, obj):
        return obj.muddati.strftime("%d.%m.%Y") if obj.muddati else None

    def get_sana(self, obj):
        return obj.yaratilgan_vaqt.strftime("%d.%m.%Y") if obj.yaratilgan_vaqt else ""

    def get_mijoz_nomi(self, obj):
        return f"{obj.mijoz.ism} {obj.mijoz.familiya or ''}".strip() if obj.mijoz else "Noma'lum"

    def get_customerName(self, obj):
        return self.get_mijoz_nomi(obj)

    def get_mijoz_telefon(self, obj):
        return obj.mijoz.telefon_raqam_1 if obj.mijoz else ""

    def get_phone(self, obj):
        return self.get_mijoz_telefon(obj)

    def get_customer_name(self, obj):
        return self.get_mijoz_nomi(obj)

    def get_name(self, obj):
        return self.get_mijoz_nomi(obj)

    def get_first_name(self, obj):
        return obj.mijoz.ism if obj.mijoz else ""

    def get_last_name(self, obj):
        return obj.mijoz.familiya if obj.mijoz else ""

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        from django.db.models import Sum
        from decimal import Decimal
        
        if instance.mijoz:
            qarzlar = instance.mijoz.qarzlar.all()
            total_debt = qarzlar.aggregate(t=Sum('umumiy_summa'))['t'] or Decimal('0.00')
            paid_amount = qarzlar.aggregate(t=Sum('tolangan_summa'))['t'] or Decimal('0.00')
            remaining_amount = qarzlar.aggregate(t=Sum('qoldiq_summa'))['t'] or Decimal('0.00')
        else:
            total_debt = instance.umumiy_summa
            paid_amount = instance.tolangan_summa
            remaining_amount = instance.qoldiq_summa
            
        from django.utils import timezone
        today = timezone.now().date()
        
        has_overdue = False
        overdue_days = 0
        if instance.mijoz:
            active_debts_with_muddati = instance.mijoz.qarzlar.exclude(holat='tolangan').filter(muddati__isnull=False)
            for d in active_debts_with_muddati:
                if d.muddati < today:
                    has_overdue = True
                    days = (today - d.muddati).days
                    if days > overdue_days:
                        overdue_days = days
        else:
            if instance.muddati and instance.muddati < today and remaining_amount > 0:
                has_overdue = True
                overdue_days = (today - instance.muddati).days

        if remaining_amount <= 0:
            status_value = 'xavfsiz'
            orig_status = 'xavfsiz'
        elif has_overdue:
            status_value = 'xavfli'
            orig_status = 'xavfli'
        elif paid_amount > 0:
            status_value = 'yaxshi'
            orig_status = 'yaxshi'
        else:
            status_value = 'normal'
            orig_status = 'normal'
        
        debt_fields = ['umumiy_summa', 'umumiySumma', 'totalDebt']
        paid_fields = ['tolangan_summa', 'tolanganSumma', 'paidAmount']
        rem_fields = ['qoldiq_summa', 'qoldiqSumma', 'remainingAmount', 'qoldiq', 'qarz', 'balance', 'amount']
        
        for f in debt_fields:
            if f in ret:
                ret[f] = str(total_debt)
        for f in paid_fields:
            if f in ret:
                ret[f] = str(paid_amount)
        for f in rem_fields:
            if f in ret:
                ret[f] = str(remaining_amount)
                
        ret['holat'] = orig_status
        ret['status'] = status_value
        ret['muddati_otgan'] = overdue_days
        ret['overdue_days'] = overdue_days
        ret['overdueDays'] = overdue_days
        return ret





class MijozToloviSerializer(serializers.ModelSerializer):
    mijoz_nomi = serializers.SerializerMethodField(read_only=True)
    xodim_nomi = serializers.SerializerMethodField(read_only=True)
    ismlar = serializers.SerializerMethodField(read_only=True)
    customerName = serializers.SerializerMethodField(read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MijozTolovi
        fields = [
            'id', 'biznes', 'mijoz', 'mijoz_nomi', 'qarz', 'summa',
            'tolov_usuli', 'xodim', 'xodim_nomi', 'eslatma',
            'yaratilgan_vaqt', 'yangilangan_vaqt',
            'ismlar', 'customerName', 'customer_name', 'name'
        ]
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']

    def get_mijoz_nomi(self, obj):
        return f"{obj.mijoz.ism} {obj.mijoz.familiya or ''}".strip() if obj.mijoz else "Noma'lum"

    def get_ismlar(self, obj):
        return self.get_mijoz_nomi(obj)

    def get_customerName(self, obj):
        return self.get_mijoz_nomi(obj)

    def get_customer_name(self, obj):
        return self.get_mijoz_nomi(obj)

    def get_name(self, obj):
        return self.get_mijoz_nomi(obj)

    def get_xodim_nomi(self, obj):
        return f"{obj.xodim.ism} {obj.xodim.familiya}".strip() if obj.xodim else ""

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.mijoz:
            ret['mijoz'] = f"{instance.mijoz.ism} {instance.mijoz.familiya or ''}".strip()
            ret['mijoz_id'] = instance.mijoz.id
        return ret

    def to_internal_value(self, data):
        data = data.copy()
        if 'mijoz' not in data:
            for alias in ['customer', 'customer_id', 'customerId', 'mijoz_id']:
                if alias in data:
                    data['mijoz'] = data[alias]
                    break
        if 'mijoz' in data:
            if isinstance(data['mijoz'], dict):
                data['mijoz'] = data['mijoz'].get('id')
            elif data['mijoz'] == '' or data['mijoz'] == 'null' or data['mijoz'] is None:
                data['mijoz'] = None
            
        if 'qarz' not in data:
            for alias in ['qarz_id', 'debt', 'debt_id', 'debtId']:
                if alias in data:
                    data['qarz'] = data[alias]
                    break
        if 'qarz' in data:
            if isinstance(data['qarz'], dict):
                data['qarz'] = data['qarz'].get('id')
            elif data['qarz'] == '' or data['qarz'] == 'null' or data['qarz'] is None:
                data['qarz'] = None
            
        if 'tolov_usuli' not in data:
            for alias in ['payment_method', 'paymentMethod', 'tolov_turi', 'tolovTuri', 'payment_type', 'paymentType', 'type']:
                if alias in data:
                    data['tolov_usuli'] = data[alias]
                    break
        if 'tolov_usuli' in data:
            val = str(data['tolov_usuli']).lower().strip()
            if val in ('plastik_karta', 'card', 'plastik', 'karta', 'plastic_card', 'plastic', 'plastik karta', 'plastik-karta'):
                data['tolov_usuli'] = 'karta'
            elif val in ('naqd', 'cash', 'naqd_pul', 'naqd pul', 'naqd_pul', 'cash_payment'):
                data['tolov_usuli'] = 'naqd'
            elif val in ('click', 'payme', 'apelsin', 'uzum'):
                data['tolov_usuli'] = 'click'

        if 'summa' in data and data['summa'] is not None:
            # Strip any spaces, commas, or currency symbols from summa
            val = str(data['summa']).replace(' ', '').replace(',', '').replace('\xa0', '').replace('UZS', '').strip()
            data['summa'] = val
                
        return super().to_internal_value(data)


class DebtorsViewSet(viewsets.ModelViewSet):
    serializer_class = MijozQarziSerializer
    permission_classes = [IsEmployee]
    search_fields = ['mijoz__ism', 'mijoz__familiya', 'mijoz__telefon_raqam_1', 'eslatma']

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = self.kwargs[lookup_url_kwarg]
        latest_debt = MijozQarzi.objects.filter(mijoz_id=pk).order_by('-yaratilgan_vaqt').first()
        if latest_debt:
            return latest_debt
        return super().get_object()

    def get_queryset(self):
        user = self.request.user
        queryset = MijozQarzi.objects.all().order_by('-yaratilgan_vaqt')
        
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                queryset = queryset.filter(biznes=user.xodim.biznes)
            else:
                return queryset.none()

        # Customer filter
        mijoz_id = self.request.query_params.get('mijoz') or self.request.query_params.get('mijoz_id') or self.request.query_params.get('customer') or self.request.query_params.get('customer_id') or self.request.query_params.get('customerId')
        if mijoz_id:
            queryset = queryset.filter(mijoz_id=mijoz_id)

        # Group by customer: get the latest MijozQarzi record for each customer

        # Group by customer: get the latest MijozQarzi record for each customer
        from django.db.models import Max
        latest_ids = queryset.values('mijoz').annotate(latest_id=Max('id')).values('latest_id')
        queryset = MijozQarzi.objects.filter(id__in=latest_ids).order_by('-yaratilgan_vaqt')

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
                if mapped_status == 'tolanmagan':
                    queryset = queryset.filter(mijoz__qarzlar__qoldiq_summa__gt=0).distinct()
                elif mapped_status == 'tolangan':
                    queryset = queryset.exclude(mijoz__qarzlar__qoldiq_summa__gt=0).distinct()
                elif mapped_status == 'qisman_tolangan':
                    queryset = queryset.filter(mijoz__qarzlar__tolangan_summa__gt=0, mijoz__qarzlar__qoldiq_summa__gt=0).distinct()
                else:
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
        stats_data = {
            'qarzlar_summasi': str(qarzlar_summasi),
            'tolovlar_summasi': str(tolovlar_summasi),
            'tizimli_tolovlar': str(tizimli_tolovlar),
            'qarzlar_qoldiqi': str(qarzlar_qoldiqi),
            'qarzdorlar_soni': qarzdorlar_soni,
            'tolanganlar': tolanganlar_count,
            'tolanmaganlar': tolanmaganlar_count,
            'muddati_otganlar': muddati_otganlar_count,

            # Frontend keys mapping compatibility
            'total_debt': str(qarzlar_summasi),
            'total_paid': str(tolovlar_summasi),
            'system_paid': str(tizimli_tolovlar),
            'tizimli': str(tizimli_tolovlar),
            'balance': str(qarzlar_qoldiqi),

            # CamelCase aliases
            'qarzlarSummasi': str(qarzlar_summasi),
            'tolovlarSummasi': str(tolovlar_summasi),
            'tizimliTolovlar': str(tizimli_tolovlar),
            'qarzlarQoldiqi': str(qarzlar_qoldiqi),
            'qarzdorlarSoni': qarzdorlar_soni,
            'muddatiOtganlar': muddati_otganlar_count,
        }

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            for k, v in stats_data.items():
                response.data[k] = v
            response.data['stats'] = stats_data
            return response

        serializer = self.get_serializer(queryset, many=True)
        resp_data = {
            'count': len(serializer.data),
            'results': serializer.data,
            'stats': stats_data
        }
        for k, v in stats_data.items():
            resp_data[k] = v
        return Response(resp_data, status=status.HTTP_200_OK)

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
        qarzdorlar_soni = base_qs.values('mijoz').distinct().count()
        tolanganlar_count = base_qs.filter(holat='tolangan').count()
        tolanmaganlar_count = base_qs.filter(holat='tolanmagan').count()
        muddati_otganlar_count = base_qs.filter(holat='muddati_otgan').count()

        stats_data = {
            'qarzlar_summasi': str(qarzlar_summasi),
            'tolovlar_summasi': str(tolovlar_summasi),
            'tizimli_tolovlar': str(tolovlar_summasi),
            'qarzlar_qoldiqi': str(qarzlar_qoldiqi),
            'qarzdorlar_soni': qarzdorlar_soni,
            'tolanganlar': tolanganlar_count,
            'tolanmaganlar': tolanmaganlar_count,
            'muddati_otganlar': muddati_otganlar_count,

            # Frontend keys mapping compatibility
            'total_debt': str(qarzlar_summasi),
            'total_paid': str(tolovlar_summasi),
            'system_paid': str(tolovlar_summasi),
            'tizimli': str(tolovlar_summasi),
            'balance': str(qarzlar_qoldiqi),

            # CamelCase aliases
            'qarzlarSummasi': str(qarzlar_summasi),
            'tolovlarSummasi': str(tolovlar_summasi),
            'tizimliTolovlar': str(tolovlar_summasi),
            'qarzlarQoldiqi': str(qarzlar_qoldiqi),
            'qarzdorlarSoni': qarzdorlar_soni,
            'muddatiOtganlar': muddati_otganlar_count,
        }

        return Response(stats_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='bulk-payment')
    def bulk_payment(self, request):
        summa = Decimal(str(request.data.get('summa', '0.00')))
        mijoz_id = request.data.get('mijoz') or request.data.get('mijoz_id') or request.data.get('customer') or request.data.get('customer_id') or request.data.get('customerId')
        if isinstance(mijoz_id, dict):
            mijoz_id = mijoz_id.get('id')
            
        tolov_usuli = request.data.get('tolov_usuli') or request.data.get('payment_method') or request.data.get('paymentMethod') or 'naqd'

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
            
            # Update linked Sale
            if debt.sotuv:
                debt.sotuv.tolangan_summa += pay
                debt.sotuv.nasiya_summa = max(Decimal('0.00'), debt.sotuv.nasiya_summa - pay)
                debt.sotuv.save(update_fields=['tolangan_summa', 'nasiya_summa'])
                
            debt.save()
            remaining -= pay

        return Response({
            'detail': "To'lov muvaffaqiyatli qabul qilindi.",
            'tolov_id': tolov.id,
            'qolgan_summa': str(remaining)
        }, status=status.HTTP_200_OK)


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
        payment = serializer.save(biznes=biznes)
        
        mijoz = payment.mijoz
        summa = payment.summa
        if mijoz and summa > 0:
            if payment.qarz and payment.qarz.qoldiq_summa > 0:
                debt = payment.qarz
                pay = min(debt.qoldiq_summa, summa)
                debt.tolangan_summa += pay
                debt.qoldiq_summa = max(Decimal('0.00'), debt.umumiy_summa - debt.tolangan_summa)
                if debt.qoldiq_summa <= 0:
                    debt.holat = 'tolangan'
                else:
                    debt.holat = 'qisman_tolangan'
                
                # Update linked Sale
                if debt.sotuv:
                    debt.sotuv.tolangan_summa += pay
                    debt.sotuv.nasiya_summa = max(Decimal('0.00'), debt.sotuv.nasiya_summa - pay)
                    debt.sotuv.save(update_fields=['tolangan_summa', 'nasiya_summa'])
                
                debt.save()
            else:
                unpaid_debts = MijozQarzi.objects.filter(mijoz=mijoz).exclude(holat='tolangan').order_by('yaratilgan_vaqt')
                remaining = summa
                for debt in unpaid_debts:
                    if remaining <= 0:
                        break
                    pay = min(debt.qoldiq_summa, remaining)
                    debt.tolangan_summa += pay
                    debt.qoldiq_summa = max(Decimal('0.00'), debt.umumiy_summa - debt.tolangan_summa)
                    if debt.qoldiq_summa <= 0:
                        debt.holat = 'tolangan'
                    else:
                        debt.holat = 'qisman_tolangan'
                    
                    # Update linked Sale
                    if debt.sotuv:
                        debt.sotuv.tolangan_summa += pay
                        debt.sotuv.nasiya_summa = max(Decimal('0.00'), debt.sotuv.nasiya_summa - pay)
                        debt.sotuv.save(update_fields=['tolangan_summa', 'nasiya_summa'])
                    
                    debt.save()
                    remaining -= pay
