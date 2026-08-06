from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from .models import Sale
from .serializers import SaleSerializer
from user.permissions import IsEmployee
from products.views.common import DynamicPagination, generate_excel_response

class SaleFilter(django_filters.FilterSet):
    sana = django_filters.DateFilter(field_name="yaratilgan_vaqt", lookup_expr='date')
    dan = django_filters.DateFilter(field_name="yaratilgan_vaqt", lookup_expr='date__gte')
    gacha = django_filters.DateFilter(field_name="yaratilgan_vaqt", lookup_expr='date__lte')
    sana_dan = django_filters.DateFilter(field_name="yaratilgan_vaqt", lookup_expr='date__gte')
    sana_gacha = django_filters.DateFilter(field_name="yaratilgan_vaqt", lookup_expr='date__lte')

    class Meta:
        model = Sale
        fields = ['holat', 'dokon', 'mijoz', 'tolov_usuli', 'xodim', 'sana', 'dan', 'gacha', 'sana_dan', 'sana_gacha']

class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [IsEmployee]
    pagination_class = DynamicPagination
    filterset_class = SaleFilter
    search_fields = ['kod', 'mijoz__ism', 'mijoz__familiya', 'xodim__ism', 'xodim__familiya']
    ordering_fields = ['oraliq_jami', 'yakuniy_summa', 'tolangan_summa', 'nasiya_summa', 'yaratilgan_vaqt']

    def perform_create(self, serializer):
        sale = serializer.save()
        from user.telegram_bot import notify_sale
        notify_sale(sale)

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

        queryset = self.filter_queryset(self.get_queryset())
        completed_sales = queryset.filter(holat='yakunlangan')
        from django.db import models
        from decimal import Decimal
        jami_kirim = completed_sales.aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')

        from .models import SaleItem
        sold_cogs = SaleItem.objects.filter(sotuv__in=completed_sales).aggregate(
            total=models.Sum(models.F('miqdori') * models.F('kelish_narxi'))
        )['total'] or Decimal('0.00')
        jami_chiqim = sold_cogs

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['jami_kirim'] = str(jami_kirim)
            response.data['jamiKirim'] = str(jami_kirim)
            response.data['total_kirim'] = str(jami_kirim)
            response.data['totalKirim'] = str(jami_kirim)
            response.data['kirim_sum'] = str(jami_kirim)
            response.data['kirimSum'] = str(jami_kirim)
            response.data['kirim_total'] = str(jami_kirim)
            response.data['kirimTotal'] = str(jami_kirim)
            response.data['incomes_total'] = str(jami_kirim)
            response.data['total_income'] = str(jami_kirim)
            response.data['totalIncome'] = str(jami_kirim)
            response.data['income_total'] = str(jami_kirim)
            response.data['incomeTotal'] = str(jami_kirim)
            response.data['income_sum'] = str(jami_kirim)
            response.data['incomeSum'] = str(jami_kirim)

            response.data['jami_chiqim'] = str(jami_chiqim)
            response.data['jamiChiqim'] = str(jami_chiqim)
            response.data['total_chiqim'] = str(jami_chiqim)
            response.data['totalChiqim'] = str(jami_chiqim)
            response.data['chiqim_sum'] = str(jami_chiqim)
            response.data['chiqimSum'] = str(jami_chiqim)
            response.data['chiqim_total'] = str(jami_chiqim)
            response.data['chiqimTotal'] = str(jami_chiqim)
            response.data['cogs'] = str(jami_chiqim)
            response.data['total_cogs'] = str(jami_chiqim)
            response.data['totalCogs'] = str(jami_chiqim)
            response.data['sotilgan_tannarx'] = str(jami_chiqim)
            response.data['tannarx'] = str(jami_chiqim)
            response.data['chiqim'] = str(jami_chiqim)
            response.data['chiqim_summasi'] = str(jami_chiqim)
            response.data['chiqimSummasi'] = str(jami_chiqim)
            response.data['total_outcome'] = str(jami_chiqim)
            response.data['totalOutcome'] = str(jami_chiqim)
            response.data['outcome_total'] = str(jami_chiqim)
            response.data['outcomeTotal'] = str(jami_chiqim)
            response.data['outcome_sum'] = str(jami_chiqim)
            response.data['outcomeSum'] = str(jami_chiqim)
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'jami_kirim': str(jami_kirim),
            'jamiKirim': str(jami_kirim),
            'total_kirim': str(jami_kirim),
            'totalKirim': str(jami_kirim),
            'kirim_sum': str(jami_kirim),
            'kirimSum': str(jami_kirim),
            'kirim_total': str(jami_kirim),
            'kirimTotal': str(jami_kirim),
            'incomes_total': str(jami_kirim),
            'total_income': str(jami_kirim),
            'totalIncome': str(jami_kirim),
            'income_total': str(jami_kirim),
            'incomeTotal': str(jami_kirim),
            'income_sum': str(jami_kirim),
            'incomeSum': str(jami_kirim),

            'jami_chiqim': str(jami_chiqim),
            'jamiChiqim': str(jami_chiqim),
            'total_chiqim': str(jami_chiqim),
            'totalChiqim': str(jami_chiqim),
            'chiqim_sum': str(jami_chiqim),
            'chiqimSum': str(jami_chiqim),
            'chiqim_total': str(jami_chiqim),
            'chiqimTotal': str(jami_chiqim),
            'cogs': str(jami_chiqim),
            'total_cogs': str(jami_chiqim),
            'totalCogs': str(jami_chiqim),
            'sotilgan_tannarx': str(jami_chiqim),
            'tannarx': str(jami_chiqim),
            'chiqim': str(jami_chiqim),
            'chiqim_summasi': str(jami_chiqim),
            'chiqimSummasi': str(jami_chiqim),
            'total_outcome': str(jami_chiqim),
            'totalOutcome': str(jami_chiqim),
            'outcome_total': str(jami_chiqim),
            'outcomeTotal': str(jami_chiqim),
            'outcome_sum': str(jami_chiqim),
            'outcomeSum': str(jami_chiqim),
        })

    @action(detail=True, methods=['get'])
    def chek(self, request, pk=None):
        sale = self.get_object()
        items = []
        for item in sale.elementlar.all():
            items.append({
                'nomi': item.mahsulot.nomi,
                'shtrix_kod': item.mahsulot.shtrix_kodlar.first().kod if item.mahsulot.shtrix_kodlar.exists() else None,
                'olchov_birligi': str(item.mahsulot.olchov_birligi) if item.mahsulot.olchov_birligi else "",
                'miqdori': item.miqdori,
                'sotish_narxi': str(item.sotish_narxi),
                'is_ulgurji': item.is_ulgurji,
                'jami_summa': str(item.jami_summa)
            })
            
        from django.db.models import Sum
        from decimal import Decimal

        # Calculate customer qarz_summasi
        qarz_summasi = Decimal('0.00')
        if sale.mijoz:
            q = sale.mijoz.qarzlar.exclude(holat='tolangan').aggregate(total=Sum('qoldiq_summa'))['total'] or Decimal('0.00')
            if q == Decimal('0.00'):
                q = sale.mijoz.sotuvlar.filter(holat='yakunlangan', nasiya_summa__gt=0).aggregate(total=Sum('nasiya_summa'))['total'] or Decimal('0.00')
            qarz_summasi = q

        savdogacha_qarz = qarz_summasi - sale.nasiya_summa
        savdodan_sung_qarz = qarz_summasi

        # Translate/localize tolov_usuli display name
        tolov_map = {
            'naqd': 'НАҚД',
            'karta': 'КАРТА',
            'nasiya': 'НАСИЯ',
            'aralash': 'АРАЛАШ'
        }
        tolov_uz = tolov_map.get(sale.tolov_usuli, sale.tolov_usuli).upper()

        biznes = sale.biznes or (sale.xodim.biznes if sale.xodim else None)
        biznes_nomi = biznes.nomi if biznes else ""
        biznes_telefon = biznes.telefon if biznes else ""
        if biznes:
            from user.models import ChekSozlamalari
            chek_sozlama = ChekSozlamalari.objects.filter(biznes=biznes).first()
            if chek_sozlama and chek_sozlama.dokon_nomi_text:
                biznes_nomi = chek_sozlama.dokon_nomi_text

        data = {
            'chek_id': sale.id,
            'kod': sale.kod,
            'kompaniya_nomi': biznes_nomi,
            'biznes_nomi': biznes_nomi,
            'company_name': biznes_nomi,
            'telefon': biznes_telefon,
            'biznes_telefon': biznes_telefon,
            'phone': biznes_telefon,
            'holat': sale.holat,
            'sana': sale.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M") if sale.yaratilgan_vaqt else "",
            'dokon': {
                'id': sale.dokon.id if sale.dokon else None,
                'nomi': sale.dokon.nomi if sale.dokon else "",
                'tavsif': sale.dokon.tavsif if sale.dokon else ""
            },
            'xodim': {
                'id': sale.xodim.id if sale.xodim else None,
                'nomi': f"{sale.xodim.ism} {sale.xodim.familiya}" if sale.xodim else ""
            },
            'mijoz': {
                'id': sale.mijoz.id if sale.mijoz else None,
                'nomi': f"{sale.mijoz.ism} {sale.mijoz.familiya}" if sale.mijoz else "Anonim Mijoz",
                'telefon': sale.mijoz.telefon_raqam_1 if sale.mijoz else "",
                'qarz_summasi': str(qarz_summasi),
                'qarzSummasi': str(qarz_summasi),
                'savdogacha_qarz': str(savdogacha_qarz),
                'savdogachaQarz': str(savdogacha_qarz),
                'savdodan_sung_qarz': str(savdodan_sung_qarz),
                'savdodanSungQarz': str(savdodan_sung_qarz),
            },
            'elementlar': items,
            'oraliq_jami': str(sale.oraliq_jami),
            'chegirma_turi': sale.chegirma_turi,
            'chegirma_qiymati': str(sale.chegirma_qiymati),
            'chegirma_summasi': str(sale.chegirma_summasi),
            'yakuniy_summa': str(sale.yakuniy_summa),
            'tolangan_summa': str(sale.tolangan_summa),
            'nasiya_summa': str(sale.nasiya_summa),
            'tolov_usuli': sale.tolov_usuli,
            'tolov_usuli_uz': tolov_uz,
            'tolovUsuliUz': tolov_uz,
            'tolov_usuli_display': tolov_uz,
            'tolovUsuliDisplay': tolov_uz,
            'savdogacha_qarz': str(savdogacha_qarz),
            'savdogachaQarz': str(savdogacha_qarz),
            'savdodan_sung_qarz': str(savdodan_sung_qarz),
            'savdodanSungQarz': str(savdodan_sung_qarz),
            'eslatma': sale.eslatma or ""
        }

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        from django.db import models
        from decimal import Decimal
        
        queryset = self.filter_queryset(self.get_queryset())
        
        # Jami kirim: Total completed sales income
        completed_sales = queryset.filter(holat='yakunlangan')
        jami_kirim = completed_sales.aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')
        
        # Jami chiqim: Sotilgan tovarlarning jami tannarxi (COGS)
        from .models import SaleItem
        sold_cogs = SaleItem.objects.filter(sotuv__in=completed_sales).aggregate(
            total=models.Sum(models.F('miqdori') * models.F('kelish_narxi'))
        )['total'] or Decimal('0.00')
        
        jami_chiqim = sold_cogs

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'jami_kirim': str(jami_kirim),
            'jamiKirim': str(jami_kirim),
            'total_kirim': str(jami_kirim),
            'totalKirim': str(jami_kirim),
            'kirim_sum': str(jami_kirim),
            'kirimSum': str(jami_kirim),
            'kirim_total': str(jami_kirim),
            'kirimTotal': str(jami_kirim),
            'incomes_total': str(jami_kirim),
            'total_income': str(jami_kirim),
            'totalIncome': str(jami_kirim),
            'income_total': str(jami_kirim),
            'incomeTotal': str(jami_kirim),
            'income_sum': str(jami_kirim),
            'incomeSum': str(jami_kirim),

            'jami_chiqim': str(jami_chiqim),
            'jamiChiqim': str(jami_chiqim),
            'total_chiqim': str(jami_chiqim),
            'totalChiqim': str(jami_chiqim),
            'chiqim_sum': str(jami_chiqim),
            'chiqimSum': str(jami_chiqim),
            'chiqim_total': str(jami_chiqim),
            'chiqimTotal': str(jami_chiqim),
            'cogs': str(jami_chiqim),
            'total_cogs': str(jami_chiqim),
            'totalCogs': str(jami_chiqim),
            'sotilgan_tannarx': str(jami_chiqim),
            'tannarx': str(jami_chiqim),
            'chiqim': str(jami_chiqim),
            'chiqim_summasi': str(jami_chiqim),
            'chiqimSummasi': str(jami_chiqim),
            'total_outcome': str(jami_chiqim),
            'totalOutcome': str(jami_chiqim),
            'outcome_total': str(jami_chiqim),
            'outcomeTotal': str(jami_chiqim),
            'outcome_sum': str(jami_chiqim),
            'outcomeSum': str(jami_chiqim),
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def cheklar_stats(self, request):
        from django.db import models
        from decimal import Decimal
        from .models import SaleItem
        
        queryset = self.filter_queryset(self.get_queryset()).filter(holat='yakunlangan')
        
        chek_soni = queryset.count()
        items = SaleItem.objects.filter(sotuv__in=queryset)
        soni = items.aggregate(total=models.Sum('miqdori'))['total'] or 0
        jami = queryset.aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')

        return Response({
            'cheklar': chek_soni,
            'soni': soni,
            'jami': str(jami),
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        from django.db import models
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta, datetime
        from .models import SaleItem, Xarajat

        user = request.user
        base_sales = self.filter_queryset(self.get_queryset())
        completed_sales = base_sales.filter(holat='yakunlangan')

        start_date_str = (
            request.query_params.get('start_date') or
            request.query_params.get('dan') or
            request.query_params.get('from_date') or
            request.query_params.get('start')
        )
        end_date_str = (
            request.query_params.get('end_date') or
            request.query_params.get('gacha') or
            request.query_params.get('to_date') or
            request.query_params.get('end')
        )

        today = timezone.now().date()
        start_date = today
        end_date = today

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass

        period_sales_qs = completed_sales.filter(yaratilgan_vaqt__date__gte=start_date, yaratilgan_vaqt__date__lte=end_date)

        days_delta = (end_date - start_date).days + 1
        prev_start = start_date - timedelta(days=days_delta)
        prev_end = start_date - timedelta(days=1)
        prev_sales_qs = completed_sales.filter(yaratilgan_vaqt__date__gte=prev_start, yaratilgan_vaqt__date__lte=prev_end)
        prev_sales = prev_sales_qs.aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')

        sold_cogs = SaleItem.objects.filter(sotuv__in=period_sales_qs).aggregate(
            t=models.Sum(models.F('miqdori') * models.F('kelish_narxi'))
        )['t'] or Decimal('0.00')

        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes) else None
        bugungi_tolovlar = Decimal('0.00')
        if biznes:
            from user.models import MijozTolovi
            bugungi_tolovlar = MijozTolovi.objects.filter(
                biznes=biznes,
                yaratilgan_vaqt__date__gte=start_date,
                yaratilgan_vaqt__date__lte=end_date
            ).aggregate(total=models.Sum('summa'))['total'] or Decimal('0.00')

        bugungi_savdo = period_sales_qs.aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')

        sotuv_foydasi = bugungi_savdo - sold_cogs

        savdo_osish = 0.0
        if prev_sales > 0:
            savdo_osish = round(float((bugungi_savdo - prev_sales) / prev_sales * 100), 2)



        bugungi_xarajat = Decimal('0.00')
        jami_xarajat = Decimal('0.00')

        if biznes:
            from orders.models import SupplierOrder, SupplierOrderPayment
            from products.models import Import, Mahsulot
            xarajat_period = Xarajat.objects.filter(
                biznes=biznes, 
                yaratilgan_vaqt__date__gte=start_date, 
                yaratilgan_vaqt__date__lte=end_date
            ).filter(
                models.Q(kategoriya__nomi="Mahsulot kirimi", izoh__startswith="Yangi mahsulot kirimi:") |
                ~models.Q(kategoriya__nomi="Mahsulot kirimi")
            ).aggregate(t=models.Sum('miqdor'))['t'] or Decimal('0.00')
            paid_kirim_period = Import.objects.filter(biznes=biznes, import_turi='kirim', holat='yakunlangan', yaratilgan_vaqt__date__gte=start_date, yaratilgan_vaqt__date__lte=end_date).exclude(holat__in=['xatolik', 'kutilmoqda', 'bekor_qilingan']).exclude(tolov_turi__in=['nasiya', 'credit', 'qarz']).aggregate(t=models.Sum('kelish_summasi'))['t'] or Decimal('0.00')
            
            tovar_xarajati_period = paid_kirim_period
            bugungi_xarajat = xarajat_period + tovar_xarajati_period
 
            xarajat_all = Xarajat.objects.filter(biznes=biznes).filter(
                models.Q(kategoriya__nomi="Mahsulot kirimi", izoh__startswith="Yangi mahsulot kirimi:") |
                ~models.Q(kategoriya__nomi="Mahsulot kirimi")
            ).aggregate(t=models.Sum('miqdor'))['t'] or Decimal('0.00')
            paid_kirim_all = Import.objects.filter(biznes=biznes, import_turi='kirim', holat='yakunlangan').exclude(holat__in=['xatolik', 'kutilmoqda', 'bekor_qilingan']).exclude(tolov_turi__in=['nasiya', 'credit', 'qarz']).aggregate(t=models.Sum('kelish_summasi'))['t'] or Decimal('0.00')
            
            tovar_xarajati_all = paid_kirim_all
            jami_xarajat = xarajat_all + tovar_xarajati_all

        credit_sales_qs = period_sales_qs.filter(
            models.Q(tolov_usuli__in=['nasiya', 'qarzga', 'qarz', 'nasiyaga', 'credit']) |
            models.Q(nasiya_summa__gt=0)
        )
        original_nasiya = credit_sales_qs.aggregate(total=models.Sum('nasiya_summa'))['total'] or Decimal('0.00')
        nasiyaga_sotilgan = max(Decimal('0.00'), original_nasiya - bugungi_tolovlar)
        nasiya_buyurtmalar_soni = credit_sales_qs.count()

        # Calculate realized profit (profit from paid portion of sales)
        total_realized_from_sales = Decimal('0.00')
        for sale in period_sales_qs.prefetch_related('elementlar'):
            sale_cogs = sum(item.miqdori * item.kelish_narxi for item in sale.elementlar.all())
            sale_profit = sale.yakuniy_summa - sale_cogs
            if sale.yakuniy_summa > 0:
                pay_ratio = sale.tolangan_summa / sale.yakuniy_summa
                total_realized_from_sales += sale_profit * pay_ratio

        # Calculate realized profit from debt payments today (subtracting their original COGS)
        total_realized_from_payments = Decimal('0.00')
        if biznes:
            from user.models import MijozTolovi
            bugungi_tolovlar_qs = MijozTolovi.objects.filter(
                biznes=biznes,
                yaratilgan_vaqt__date__gte=start_date,
                yaratilgan_vaqt__date__lte=end_date
            ).select_related('qarz', 'qarz__sotuv', 'mijoz').prefetch_related('qarz__sotuv__elementlar')
            
            for payment in bugungi_tolovlar_qs:
                margin = None
                if payment.qarz and payment.qarz.sotuv:
                    sale = payment.qarz.sotuv
                    sale_cogs = sum(item.miqdori * item.kelish_narxi for item in sale.elementlar.all())
                    sale_profit = sale.yakuniy_summa - sale_cogs
                    if sale.yakuniy_summa > 0:
                        margin = sale_profit / sale.yakuniy_summa
                
                if margin is None and payment.mijoz:
                    from user.models import MijozQarzi
                    customer_debts = MijozQarzi.objects.filter(mijoz=payment.mijoz, sotuv__isnull=False).select_related('sotuv').prefetch_related('sotuv__elementlar')
                    if customer_debts.exists():
                        total_sale_sum = Decimal('0.00')
                        total_profit = Decimal('0.00')
                        for debt in customer_debts:
                            sale = debt.sotuv
                            sale_cogs = sum(item.miqdori * item.kelish_narxi for item in sale.elementlar.all())
                            sale_profit = sale.yakuniy_summa - sale_cogs
                            total_sale_sum += sale.yakuniy_summa
                            total_profit += sale_profit
                        if total_sale_sum > 0:
                            margin = total_profit / total_sale_sum

                if margin is None:
                    if bugungi_savdo > 0:
                        margin = sotuv_foydasi / bugungi_savdo
                    else:
                        margin = Decimal('0.15')

                total_realized_from_payments += payment.summa * margin

        sof_pul = total_realized_from_sales + total_realized_from_payments

        naqd_sales = period_sales_qs.filter(models.Q(tolov_usuli__in=['naqd', 'cash', 'naqd_pul', 'naqd pul']))
        karta_sales = period_sales_qs.filter(models.Q(tolov_usuli__in=['karta', 'card', 'uzcard', 'humo', 'visa', 'mastercard', 'sov. karta']))
        nasiya_sales = credit_sales_qs

        naqd_summa = naqd_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
        karta_summa = karta_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
        nasiya_summa = nasiya_sales.aggregate(t=models.Sum('nasiya_summa'))['t'] or nasiya_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')

        unspecified_sales = period_sales_qs.exclude(id__in=naqd_sales).exclude(id__in=karta_sales).exclude(id__in=nasiya_sales)
        unspecified_summa = unspecified_sales.aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
        if unspecified_summa > 0:
            naqd_summa += unspecified_summa

        total_payment_sum = naqd_summa + karta_summa + nasiya_summa
        if total_payment_sum <= 0 and bugungi_savdo > 0:
            total_payment_sum = bugungi_savdo
            naqd_summa = bugungi_savdo

        if total_payment_sum > 0:
            naqd_percent = round(float((naqd_summa / total_payment_sum) * 100), 1)
            karta_percent = round(float((karta_summa / total_payment_sum) * 100), 1)
            nasiya_percent = round(float((nasiya_summa / total_payment_sum) * 100), 1)
        else:
            naqd_percent = 0.0
            karta_percent = 0.0
            nasiya_percent = 0.0

        dinamikasi = []
        cur_date = start_date
        while cur_date <= end_date:
            day_sales = completed_sales.filter(yaratilgan_vaqt__date=cur_date).aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            day_exp = Decimal('0.00')
            if biznes:
                x_d = Xarajat.objects.filter(
                    biznes=biznes, 
                    yaratilgan_vaqt__date=cur_date
                ).filter(
                    models.Q(kategoriya__nomi="Mahsulot kirimi", izoh__startswith="Yangi mahsulot kirimi:") |
                    ~models.Q(kategoriya__nomi="Mahsulot kirimi")
                ).aggregate(t=models.Sum('miqdor'))['t'] or Decimal('0.00')
                paid_kirim_d = Import.objects.filter(biznes=biznes, import_turi='kirim', holat='yakunlangan', yaratilgan_vaqt__date=cur_date).exclude(holat__in=['xatolik', 'kutilmoqda', 'bekor_qilingan']).exclude(tolov_turi__in=['nasiya', 'credit', 'qarz']).aggregate(t=models.Sum('kelish_summasi'))['t'] or Decimal('0.00')
                day_exp = x_d + paid_kirim_d
            dinamikasi.append({
                "sana": cur_date.strftime("%Y-%m-%d"),
                "date": cur_date.strftime("%Y-%m-%d"),
                "savdo": str(day_sales),
                "xarajat": str(day_exp)
            })
            cur_date += timedelta(days=1)

        items = SaleItem.objects.filter(sotuv__in=period_sales_qs)
        top_items = items.values('mahsulot', 'mahsulot__nomi').annotate(
            jami_miqdor=models.Sum('miqdori'),
            jami_summa=models.Sum('jami_summa')
        ).order_by('-jami_miqdor')[:5]

        top_5_list = [
            {
                'mahsulot_id': item['mahsulot'],
                'nomi': item['mahsulot__nomi'],
                'miqdori': item['jami_miqdor'],
                'summa': str(item['jami_summa'])
            }
            for item in top_items
        ]

        recent_sales = base_sales[:5]
        recent_activities = [
            {
                'turi': 'Sotuv',
                'nomi': f"Sotuv #{sale.kod} amalga oshirildi",
                'summa': str(sale.yakuniy_summa),
                'vaqt': sale.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M") if sale.yaratilgan_vaqt else ""
            }
            for sale in recent_sales
        ]

        # 1. Customer debt (Qancha bizdan qarz)
        bizdan_qarz = Decimal('0.00')
        if biznes:
            from user.models import MijozQarzi
            bizdan_qarz = MijozQarzi.objects.filter(biznes=biznes).exclude(holat='tolangan').aggregate(t=models.Sum('qoldiq_summa'))['t'] or Decimal('0.00')
            if bizdan_qarz == Decimal('0.00'):
                bizdan_qarz = base_sales.filter(holat='yakunlangan', nasiya_summa__gt=0).aggregate(t=models.Sum('nasiya_summa'))['t'] or Decimal('0.00')

        # 2. Our debt to suppliers (Biz qancha qarzimiz)
        bizning_qarz = Decimal('0.00')
        taminotchilar_soni = 0
        if biznes:
            from orders.models import SupplierOrder
            bizning_qarz = SupplierOrder.objects.filter(biznes=biznes).exclude(holat='bekor_qilingan').aggregate(t=models.Sum('nasiya_summa'))['t'] or Decimal('0.00')
            taminotchilar_soni = SupplierOrder.objects.filter(biznes=biznes, nasiya_summa__gt=0).exclude(holat='bekor_qilingan').values('taminotchi').distinct().count()

        # 3. Discounts (Chegirmalar)
        chegirmalar_summasi = period_sales_qs.aggregate(t=models.Sum('chegirma_summasi'))['t'] or Decimal('0.00')
        chegirmali_sotuvlar_soni = period_sales_qs.filter(chegirma_summasi__gt=0).count()

        # 4. Live Ombor Stock Statistics (Ombordagi jonli o'zgarishlar)
        ombor_tovar_qiymati = Decimal('0.00')
        ombor_sotish_summasi = Decimal('0.00')
        ombor_tovarlar_soni = 0
        tovarlar_turlari_soni = 0
        if biznes:
            from products.models import Mahsulot
            m_active = Mahsulot.objects.filter(biznes=biznes, is_active=True)
            tovarlar_turlari_soni = m_active.count()
            ombor_tovarlar_soni = m_active.aggregate(t=models.Sum('miqdori'))['t'] or 0
            ombor_tovar_qiymati = m_active.aggregate(t=models.Sum(models.F('miqdori') * models.F('kelish_narxi')))['t'] or Decimal('0.00')
            ombor_sotish_summasi = m_active.aggregate(t=models.Sum(models.F('miqdori') * models.F('sotish_narxi')))['t'] or Decimal('0.00')

        return Response({
            'foyda': str(sotuv_foydasi),
            'profit': str(sotuv_foydasi),
            'today_profit': str(sotuv_foydasi),
            'todayProfit': str(sotuv_foydasi),
            'sotuv_foydasi': str(sotuv_foydasi),
            'foyda_summasi': str(sotuv_foydasi),
            'bugungi_savdo': str(bugungi_savdo),
            'today_sales': str(bugungi_savdo),
            'todaySales': str(bugungi_savdo),
            'savdo_summasi': str(bugungi_savdo),
            'savdo_osish': savdo_osish,
            'savdoOsish': savdo_osish,
            'bugungi_xarajat': str(bugungi_xarajat),
            'today_expenses': str(bugungi_xarajat),
            'todayExpenses': str(bugungi_xarajat),
            'xarajat_summasi': str(bugungi_xarajat),
            'jami_xarajat': str(jami_xarajat),
            'total_expenses': str(jami_xarajat),
            'sof_pul': str(sof_pul),
            'net_cash': str(sof_pul),
            'netCash': str(sof_pul),
            'kassa_holati': str(sof_pul),
            'kassaHolati': str(sof_pul),
            'nasiyaga_sotilgan': str(nasiyaga_sotilgan),
            'credit_sales': str(nasiyaga_sotilgan),
            'creditSales': str(nasiyaga_sotilgan),
            'nasiya_buyurtmalar_soni': nasiya_buyurtmalar_soni,

            # Jonli Ombor Statistikasi
            'ombor_tovar_qiymati': str(ombor_tovar_qiymati),
            'ombor_qiymati': str(ombor_tovar_qiymati),
            'inventory_cost': str(ombor_tovar_qiymati),
            'ombor_sotish_summasi': str(ombor_sotish_summasi),
            'inventory_sale_value': str(ombor_sotish_summasi),
            'ombor_tovarlar_soni': ombor_tovarlar_soni,
            'total_stock_quantity': ombor_tovarlar_soni,
            'tovarlar_turlari_soni': tovarlar_turlari_soni,
            'kassaHolati': str(sof_pul),
            'nasiyaga_sotilgan': str(nasiyaga_sotilgan),
            'credit_sales': str(nasiyaga_sotilgan),
            'creditSales': str(nasiyaga_sotilgan),
            'nasiya_buyurtmalar_soni': nasiya_buyurtmalar_soni,

            # Qarzlar statistikasi
            'bizdan_qarz': str(bizdan_qarz),
            'mijozlar_qarzi': str(bizdan_qarz),
            'customers_debt': str(bizdan_qarz),

            'bizning_qarz': str(bizning_qarz),
            'taminotchilar_qarzi': str(bizning_qarz),
            'our_debt': str(bizning_qarz),
            'suppliers_debt': str(bizning_qarz),
            'olingan_nasiya': str(bizning_qarz),
            'taminotchi_qarzi': str(bizning_qarz),
            'supplier_debts': str(bizning_qarz),

            'taminotchilar_soni': taminotchilar_soni,
            'suppliers_count': taminotchilar_soni,
            'supplier_count': taminotchilar_soni,
            'active_suppliers_count': taminotchilar_soni,
            'debt_suppliers_count': taminotchilar_soni,

            # Chegirmalar statistikasi
            'chegirmalar_summasi': str(chegirmalar_summasi),
            'jami_chegirma': str(chegirmalar_summasi),
            'discounts_total': str(chegirmalar_summasi),
            'chegirmali_sotuvlar_soni': chegirmali_sotuvlar_soni,

            'tolov_turlari': {
                'naqd': naqd_percent,
                'karta': karta_percent,
                'nasiya': nasiya_percent,
                'naqd_percent': naqd_percent,
                'karta_percent': karta_percent,
                'nasiya_percent': nasiya_percent,
                'naqd_summa': str(naqd_summa),
                'karta_summa': str(karta_summa),
                'nasiya_summa': str(nasiya_summa),
            },

            'savdo_xarajat_dinamikasi': dinamikasi,
            'dinamika': dinamikasi,
            'dynamics': dinamikasi,

            'top_5_mahsulot': top_5_list,
            'top_products': top_5_list,
            'topProducts': top_5_list,

            'oxirgi_harakatlar': recent_activities,
            'recent_activities': recent_activities,
            'recentActivities': recent_activities,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='payments-history')
    def payments_history(self, request):
        from user.models import MijozTolovi
        from orders.models import SupplierOrderPayment
        from django.db import models

        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes) else None

        c_payments = MijozTolovi.objects.all().order_by('-yaratilgan_vaqt')
        s_payments = SupplierOrderPayment.objects.all().order_by('-yaratilgan_vaqt')

        if biznes:
            c_payments = c_payments.filter(biznes=biznes)
            s_payments = s_payments.filter(order__biznes=biznes)

        history = []
        for cp in c_payments[:50]:
            history.append({
                "id": f"c_{cp.id}",
                "turi": "Mijoz to'lovi",
                "shaxs": f"{cp.mijoz.ism} {cp.mijoz.familiya}" if cp.mijoz else "",
                "summa": str(cp.summa),
                "tolov_usuli": cp.get_tolov_usuli_display(),
                "xodim": f"{cp.xodim.ism} {cp.xodim.familiya}" if cp.xodim else "",
                "sana": cp.yaratilgan_vaqt
            })

        for sp in s_payments[:50]:
            history.append({
                "id": f"s_{sp.id}",
                "turi": "Ta'minotchi to'lovi",
                "shaxs": sp.order.taminotchi.nomi if (sp.order and sp.order.taminotchi) else "",
                "summa": str(sp.tolangan_summa),
                "tolov_usuli": sp.get_tolov_turi_display(),
                "xodim": f"{sp.xodim.ism} {sp.xodim.familiya}" if sp.xodim else "",
                "sana": sp.yaratilgan_vaqt
            })

        history.sort(key=lambda x: x['sana'], reverse=True)
        return Response(history, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='tolovlar-tarixi')
    def tolovlar_tarixi(self, request):
        return self.payments_history(request)

    @action(detail=False, methods=['get'])
    def top_products(self, request):
        from django.db import models
        from .models import SaleItem

        completed_sales = self.filter_queryset(self.get_queryset()).filter(holat='yakunlangan')
        items = SaleItem.objects.filter(sotuv__in=completed_sales)
        top_items = items.values('mahsulot', 'mahsulot__nomi').annotate(
            jami_miqdor=models.Sum('miqdori'),
            jami_summa=models.Sum('jami_summa')
        ).order_by('-jami_miqdor')[:5]

        data = [
            {
                'mahsulot_id': item['mahsulot'],
                'nomi': item['mahsulot__nomi'],
                'miqdori': item['jami_miqdor'],
                'summa': str(item['jami_summa'])
            }
            for item in top_items
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def recent_activities(self, request):
        sales = self.filter_queryset(self.get_queryset())[:10]
        data = [
            {
                'turi': 'Sotuv',
                'nomi': f"Sotuv #{sale.kod} amalga oshirildi",
                'summa': str(sale.yakuniy_summa),
                'vaqt': sale.yaratilgan_vaqt.strftime("%d.%m.%Y %H:%M") if sale.yaratilgan_vaqt else ""
            }
            for sale in sales
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def cashflow(self, request):
        from django.db import models
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta, datetime
        from .models import Sale, Xarajat, XarajatKategoriyasi
        from orders.models import SupplierOrderPayment
        from products.models import WriteOff

        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes) else None

        start_date_str = (
            request.query_params.get('start_date') or
            request.query_params.get('dan') or
            request.query_params.get('from_date') or
            request.query_params.get('start')
        )
        end_date_str = (
            request.query_params.get('end_date') or
            request.query_params.get('gacha') or
            request.query_params.get('to_date') or
            request.query_params.get('end')
        )

        today = timezone.now().date()
        start_date = today - timedelta(days=6)
        end_date = today

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass

        daily_list = []
        cur_date = start_date
        while cur_date <= end_date:
            kirim = Sale.objects.filter(biznes=biznes, holat='yakunlangan', yaratilgan_vaqt__date=cur_date).aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')
            x_val = Xarajat.objects.filter(
                biznes=biznes, 
                yaratilgan_vaqt__date=cur_date
            ).filter(
                models.Q(kategoriya__nomi="Mahsulot kirimi", izoh__startswith="Yangi mahsulot kirimi:") |
                ~models.Q(kategoriya__nomi="Mahsulot kirimi")
            ).aggregate(total=models.Sum('miqdor'))['total'] or Decimal('0.00')
            
            from orders.models import SupplierOrder, SupplierOrderPayment
            from products.models import Import
            
            paid_kirim_val = Import.objects.filter(biznes=biznes, import_turi='kirim', holat='yakunlangan', yaratilgan_vaqt__date=cur_date).exclude(holat__in=['xatolik', 'kutilmoqda', 'bekor_qilingan']).exclude(tolov_turi__in=['nasiya', 'credit', 'qarz']).aggregate(total=models.Sum('kelish_summasi'))['total'] or Decimal('0.00')
            
            chiqim = x_val + paid_kirim_val

            sof = kirim - chiqim

            daily_list.append({
                'sana': cur_date.strftime("%Y-%m-%d"),
                'date': cur_date.strftime("%Y-%m-%d"),
                'kirim': str(kirim),
                'income': str(kirim),
                'chiqim': str(chiqim),
                'expense': str(chiqim),
                'sof_pul': str(sof),
                'net_cash': str(sof)
            })
            cur_date += timedelta(days=1)

        cat_list = []
        categories = XarajatKategoriyasi.objects.filter(models.Q(biznes=biznes) | models.Q(biznes__isnull=True))
        for cat in categories:
            total_exp = Xarajat.objects.filter(
                biznes=biznes,
                kategoriya=cat,
                yaratilgan_vaqt__date__gte=start_date,
                yaratilgan_vaqt__date__lte=end_date
            ).aggregate(total=models.Sum('miqdor'))['total'] or Decimal('0.00')
            cat_list.append({
                'id': cat.id,
                'nomi': cat.nomi,
                'summa': str(total_exp)
            })

        if not cat_list:
            default_names = ["Ijara", "Tr", "Oylik", "Kom", "Boshqa"]
            for idx, name in enumerate(default_names, 1):
                cat_list.append({
                    'id': idx,
                    'nomi': name,
                    'summa': '0.00'
                })

        return Response({
            'dinamika': daily_list,
            'kirim_chiqim_dinamikasi': daily_list,
            'cashflow_dynamics': daily_list,
            'chiqim_kategoriyalari': cat_list,
            'expense_categories': cat_list,
            'kunlik_pul_oqimi': daily_list,
            'daily_cash_flow': daily_list
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def monthly(self, request):
        from django.db import models
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta, datetime
        from .models import Sale

        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes) else None

        start_date_str = (
            request.query_params.get('start_date') or
            request.query_params.get('dan') or
            request.query_params.get('from_date') or
            request.query_params.get('start')
        )
        end_date_str = (
            request.query_params.get('end_date') or
            request.query_params.get('gacha') or
            request.query_params.get('to_date') or
            request.query_params.get('end')
        )

        today = timezone.now().date()
        start_date = today - timedelta(days=6)
        end_date = today

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass

        first_of_this_month = today.replace(day=1)
        first_of_last_month = (first_of_this_month - timedelta(days=1)).replace(day=1)
        end_of_last_month = first_of_this_month - timedelta(days=1)

        joriy_oy_sum = Sale.objects.filter(biznes=biznes, holat='yakunlangan', yaratilgan_vaqt__date__gte=first_of_this_month).aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')
        otgan_oy_sum = Sale.objects.filter(biznes=biznes, holat='yakunlangan', yaratilgan_vaqt__date__gte=first_of_last_month, yaratilgan_vaqt__date__lte=end_of_last_month).aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')

        dinamika = []
        best_day = {'sana': '-', 'date': '-', 'summa': Decimal('0.00')}
        worst_day = {'sana': '-', 'date': '-', 'summa': Decimal('999999999.00')}

        month_names_uz = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Iyun',
            7: 'Iyul', 8: 'Avg', 9: 'Sep', 10: 'Okt', 11: 'Noy', 12: 'Dek'
        }

        cur_date = start_date
        has_sales = False
        while cur_date <= end_date:
            s_sum = Sale.objects.filter(biznes=biznes, holat='yakunlangan', yaratilgan_vaqt__date=cur_date).aggregate(t=models.Sum('yakuniy_summa'))['t'] or Decimal('0.00')
            formatted_date_str = f"{cur_date.day}-{month_names_uz.get(cur_date.month, 'Iyul')}"

            day_obj = {
                'sana': formatted_date_str,
                'date': cur_date.strftime("%Y-%m-%d"),
                'summa': str(s_sum)
            }
            dinamika.append(day_obj)

            if s_sum > best_day['summa']:
                best_day = {'sana': formatted_date_str, 'date': cur_date.strftime("%Y-%m-%d"), 'summa': s_sum}
                has_sales = True

            if s_sum < worst_day['summa']:
                worst_day = {'sana': formatted_date_str, 'date': cur_date.strftime("%Y-%m-%d"), 'summa': s_sum}

            cur_date += timedelta(days=1)

        if not has_sales:
            best_day_res = {'sana': f"{today.day}-{month_names_uz.get(today.month, 'Iyul')}", 'summa': '0'}
            worst_day_res = {'sana': f"{today.day}-{month_names_uz.get(today.month, 'Iyul')}", 'summa': '0'}
        else:
            best_day_res = {'sana': best_day['sana'], 'date': best_day['date'], 'summa': str(best_day['summa'])}
            worst_day_res = {'sana': worst_day['sana'], 'date': worst_day['date'], 'summa': str(worst_day['summa'])}

        return Response({
            'otgan_oy': str(otgan_oy_sum),
            'last_month': str(otgan_oy_sum),
            'otganOy': str(otgan_oy_sum),
            'joriy_oy': str(joriy_oy_sum),
            'current_month': str(joriy_oy_sum),
            'joriyOy': str(joriy_oy_sum),
            'eng_yaxshi_kun': best_day_res,
            'best_day': best_day_res,
            'eng_sust_kun': worst_day_res,
            'worst_day': worst_day_res,
            'dinamika': dinamika,
            'oylik_samaradorlik_dinamikasi': dinamika
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def products_analytics(self, request):
        import traceback
        try:
            from django.db import models
            from .models import SaleItem
            from decimal import Decimal

            completed_sales = self.filter_queryset(self.get_queryset()).filter(holat='yakunlangan')
            items = SaleItem.objects.filter(sotuv__in=completed_sales)

            sort_param = request.query_params.get('sort_by') or request.query_params.get('sort') or 'sotuv_summasi'

            top_items = items.values('mahsulot', 'mahsulot__nomi').annotate(
                jami_miqdor=models.Sum('miqdori'),
                jami_summa=models.Sum('jami_summa')
            )

            if 'miqdor' in sort_param.lower():
                top_items = top_items.order_by('-jami_miqdor')
            else:
                top_items = top_items.order_by('-jami_summa')

            data = []
            for item in top_items:
                qty = item['jami_miqdor'] or 1
                summa = item['jami_summa'] or Decimal('0.00')
                avg = (summa / qty).quantize(Decimal('0.01')) if qty > 0 else Decimal('0.00')
                data.append({
                    'mahsulot_id': item['mahsulot'],
                    'nomi': item['mahsulot__nomi'],
                    'mahsulot_nomi': item['mahsulot__nomi'],
                    'miqdor': item['jami_miqdor'],
                    'miqdori': item['jami_miqdor'],
                    'sotuv_summasi': str(summa),
                    'summa': str(summa),
                    'ortacha_narx': str(avg),
                    'ortachaNarx': str(avg)
                })
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            try:
                with open('error_log.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Exception in products_analytics: {str(e)}\nTraceback: {traceback.format_exc()}\n")
            except Exception:
                pass
            raise

    @action(detail=False, methods=['get'])
    def debts_analytics(self, request):
        from user.models import MijozQarzi, MijozTolovi
        from django.utils import timezone
        from decimal import Decimal
        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes) else None

        qarzlar = MijozQarzi.objects.filter(biznes=biznes) if biznes else MijozQarzi.objects.none()
        tolovlar = MijozTolovi.objects.filter(biznes=biznes).order_by('-yaratilgan_vaqt')[:5] if biznes else MijozTolovi.objects.none()

        recent_payments = [
            {
                'ismlar': f"{t.mijoz.ism} {t.mijoz.familiya}" if t.mijoz else "Anonim",
                'mijoz': f"{t.mijoz.ism} {t.mijoz.familiya}" if t.mijoz else "Anonim",
                'mijoz_nomi': f"{t.mijoz.ism} {t.mijoz.familiya}" if t.mijoz else "Anonim",
                'customerName': f"{t.mijoz.ism} {t.mijoz.familiya}" if t.mijoz else "Anonim",
                'customer_name': f"{t.mijoz.ism} {t.mijoz.familiya}" if t.mijoz else "Anonim",
                'name': f"{t.mijoz.ism} {t.mijoz.familiya}" if t.mijoz else "Anonim",
                'summa': str(getattr(t, 'summa', getattr(t, 'tolangan_summa', Decimal('0.00')))),
                'sana': t.yaratilgan_vaqt.strftime("%d.%m.%Y") if t.yaratilgan_vaqt else ""
            }
            for t in tolovlar
        ]

        today = timezone.now().date()
        aging = {'0-30': Decimal('0.00'), '31-60': Decimal('0.00'), '61-90': Decimal('0.00'), '90+': Decimal('0.00')}

        for q in qarzlar:
            ref_date = q.muddati or q.yaratilgan_vaqt.date()
            days = (today - ref_date).days
            val = q.qoldiq_summa
            if days <= 30:
                aging['0-30'] += val
            elif days <= 60:
                aging['31-60'] += val
            elif days <= 90:
                aging['61-90'] += val
            else:
                aging['90+'] += val

        aging_res = {k: str(v) for k, v in aging.items()}

        debtors_table = []
        for q in qarzlar[:20]:
            ref_date = q.muddati or q.yaratilgan_vaqt.date()
            overdue_days = max(0, (today - ref_date).days)
            last_pay = q.tolovlar.order_by('-yaratilgan_vaqt').first()
            last_pay_date = last_pay.yaratilgan_vaqt.strftime("%d.%m.%Y") if last_pay else "-"
            debtors_table.append({
                'mijoz': f"{q.mijoz.ism} {q.mijoz.familiya}" if q.mijoz else "Mijoz",
                'mijoz_nomi': f"{q.mijoz.ism} {q.mijoz.familiya}" if q.mijoz else "Mijoz",
                'umumiy_qarz': str(q.qoldiq_summa),
                'qarz_summasi': str(q.qoldiq_summa),
                'muddati_otgan': overdue_days,
                'overdue_days': overdue_days,
                'oxirgi_tolov': last_pay_date,
                'holat': q.get_holat_display()
            })

        return Response({
            'aging': aging_res,
            'qarzdorlik_yosh_tahlili': aging_res,
            'oxirgi_tolovlar': recent_payments,
            'recent_payments': recent_payments,
            'qarzdorlar_royxati': debtors_table,
            'debtors_table': debtors_table
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def abc_xyz(self, request):
        from django.db import models
        from decimal import Decimal
        from products.models import Mahsulot

        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes) else None

        products = Mahsulot.objects.filter(biznes=biznes) if biznes else Mahsulot.objects.none()

        # Debug logging to identify empty queryset
        try:
            with open('error_log.txt', 'a', encoding='utf-8') as f:
                f.write(f"abc_xyz: user={user}, authenticated={user.is_authenticated}, hasattr_xodim={hasattr(user, 'xodim')}, biznes={biznes}, count={products.count()}\n")
        except Exception:
            pass

        categories_def = {
            'AX': {
                'code': 'AX',
                'label': 'AX - Faol Liderlar',
                'nomi': 'AX - Faol Liderlar',
                'count': 0,
                'xulosa': 'Ushbu mahsulotlar sizga eng yuqori daromadni olib keladi va talab juda barqaror. Ular biznesingiz tayanchidir.',
                'tavsiya': 'Zaxira hech qachon tugamasligi shart. Sug\'urta zaxirasini ushlab turing va yetkazib beruvchilar bilan eng yaxshi shartlar ustida ishlang.',
                'strategik_tavsiya': 'Zaxira hech qachon tugamasligi shart. Sug\'urta zaxirasini ushlab turing va yetkazib beruvchilar bilan eng yaxshi shartlar ustida ishlang.'
            },
            'AY': {
                'code': 'AY',
                'label': 'AY - Mavsumiy',
                'nomi': 'AY - Mavsumiy',
                'count': 0,
                'xulosa': 'Yuqori daromadli, lekin talab mavsumiylik va aksiyalarga bog\'liq.',
                'tavsiya': 'Mavsumiy talab piki kelishidan oldin xaridlarni rejalashtiring.',
                'strategik_tavsiya': 'Mavsumiy talab piki kelishidan oldin xaridlarni rejalashtiring.'
            },
            'AZ': {
                'code': 'AZ',
                'label': 'AZ - Katta Tavakkal',
                'nomi': 'AZ - Katta Tavakkal',
                'count': 0,
                'xulosa': 'Sotilsa katta kassa qiladi, lekin qachon sotilishi noaniq.',
                'tavsiya': 'Omborda ko\'p zaxira tutmang, buyurtma asosida ishlang.',
                'strategik_tavsiya': 'Omborda ko\'p zaxira tutmang, buyurtma asosida ishlang.'
            },
            'BX': {
                'code': 'BX',
                'label': 'BX - Barqaror O\'rtacha',
                'nomi': 'BX - Barqaror O\'rtacha',
                'count': 0,
                'xulosa': 'O\'rtacha daromad keltiruvchi, barqaror sotiladigan mahsulotlar.',
                'tavsiya': 'Optimal zaxira darajasini saqlab turing.',
                'strategik_tavsiya': 'Optimal zaxira darajasini saqlab turing.'
            },
            'BY': {
                'code': 'BY',
                'label': 'BY - O\'rtacha O\'zgaruvchan',
                'nomi': 'BY - O\'rtacha O\'zgaruvchan',
                'count': 0,
                'xulosa': 'O\'rtacha daromadli va o\'zgaruvchan talabli mahsulotlar.',
                'tavsiya': 'Talab o\'zgarishini muntazam monitoring qiling.',
                'strategik_tavsiya': 'Talab o\'zgarishini muntazam monitoring qiling.'
            },
            'BZ': {
                'code': 'BZ',
                'label': 'BZ - Noaniq O\'rtacha',
                'nomi': 'BZ - Noaniq O\'rtacha',
                'count': 0,
                'xulosa': 'O\'rtacha daromad, lekin sotuv jadvali noaniq.',
                'tavsiya': 'Minimal hajmda xarid qiling.',
                'strategik_tavsiya': 'Minimal hajmda xarid qiling.'
            },
            'CX': {
                'code': 'CX',
                'label': 'CX - Past Barqaror',
                'nomi': 'CX - Past Barqaror',
                'count': 0,
                'xulosa': 'Kam daromadli, ammo doimiy xarid qilinadigan tovarlar.',
                'tavsiya': 'Avtomatik minimal buyurtma nuqtasini sozlang.',
                'strategik_tavsiya': 'Avtomatik minimal buyurtma nuqtasini sozlang.'
            },
            'CY': {
                'code': 'CY',
                'label': 'CY - Past O\'zgaruvchan',
                'nomi': 'CY - Past O\'zgaruvchan',
                'count': 0,
                'xulosa': 'Kam daromadli va beqaror talabli mahsulotlar.',
                'tavsiya': 'Zaxira hajmini kamaytiring.',
                'strategik_tavsiya': 'Zaxira hajmini kamaytiring.'
            },
            'CZ': {
                'code': 'CZ',
                'label': 'CZ - O\'lik Kapital',
                'nomi': 'CZ - O\'lik Kapital',
                'count': 0,
                'xulosa': 'Past aylanma va noaniq talab. Pul muzlab qolgan.',
                'tavsiya': 'Aksiya qilib sotib yuboring yoki sotuvdan chiqaring.',
                'strategik_tavsiya': 'Aksiya qilib sotib yuboring yoki sotuvdan chiqaring.'
            },
        }

        products_data = []
        for p in products:
            items = p.sotuv_elementlari.filter(sotuv__holat='yakunlangan')
            aylanma = items.aggregate(total=models.Sum('jami_summa'))['total'] or Decimal('0.00')
            qty = items.aggregate(total=models.Sum('miqdori'))['total'] or 0

            if aylanma > Decimal('1000000.00'):
                cat = 'AX' if qty >= 10 else ('AY' if qty >= 5 else 'AZ')
            elif aylanma > Decimal('200000.00'):
                cat = 'BX' if qty >= 10 else ('BY' if qty >= 5 else 'BZ')
            else:
                cat = 'CX' if qty >= 10 else ('CY' if qty >= 5 else 'CZ')

            categories_def[cat]['count'] += 1

            products_data.append({
                'id': p.id,
                'mahsulot_nomi': p.nomi,
                'nomi': p.nomi,
                'toifa': cat,
                'toifa_nomi': categories_def[cat]['label'],
                'ombor_qoldigi': p.miqdori,
                'omborQoldigi': p.miqdori,
                'aylanma': str(aylanma),
                'sof_foyda': str(round(aylanma * Decimal('0.2'), 2)),
                'sofFoyda': str(round(aylanma * Decimal('0.2'), 2)),
                'tavsiya': categories_def[cat]['tavsiya']
            })

        toifa_param = request.query_params.get('toifa') or request.query_params.get('category') or 'AX'
        limit_param = request.query_params.get('limit') or request.query_params.get('qatorlar_soni') or request.query_params.get('page_size') or '8'

        try:
            limit = int(limit_param)
        except ValueError:
            limit = 8

        selected_cat_info = categories_def.get(toifa_param.upper(), categories_def['AX'])

        filtered_products = [p for p in products_data if p['toifa'] == selected_cat_info['code']]

        toifalar_list = [
            {
                'code': k,
                'label': f"{v['label']} ({v['count']} ta)",
                'nomi': v['label'],
                'count': v['count'],
                'xulosa': v['xulosa'],
                'tavsiya': v['tavsiya'],
                'strategik_tavsiya': v['strategik_tavsiya']
            }
            for k, v in categories_def.items()
        ]

        matrix = {
            k: {
                'count': v['count'],
                'label': v['label'],
                'nomi': v['label'],
                'xulosa': v['xulosa'],
                'tavsiya': v['tavsiya'],
                'strategik_tavsiya': v['strategik_tavsiya']
            }
            for k, v in categories_def.items()
        }

        return Response({
            'summary': {
                'AX': categories_def['AX']['count'],
                'AY': categories_def['AY']['count'],
                'AZ': categories_def['AZ']['count'],
                'BX': categories_def['BX']['count'],
                'BY': categories_def['BY']['count'],
                'BZ': categories_def['BZ']['count'],
                'CX': categories_def['CX']['count'],
                'CY': categories_def['CY']['count'],
                'CZ': categories_def['CZ']['count'],
                'kassa_generatorlari': categories_def['AX']['count'],
                'kassaGeneratorlari': categories_def['AX']['count'],
                'olik_kapital': categories_def['CZ']['count'],
                'olikKapital': categories_def['CZ']['count'],
                'mavsumiy': categories_def['AY']['count']
            },
            'tanlangan_toifa': selected_cat_info,
            'selected_category': selected_cat_info,
            'toifalar_royxati': toifalar_list,
            'categories_list': toifalar_list,
            'matrix': matrix,
            'products': products_data,
            'barcha_mahsulotlar': products_data,
            'mahsulotlar': products_data
        }, status=status.HTTP_200_OK)

    def get_queryset(self):
        user = self.request.user
        queryset = Sale.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()


class XarajatKategoriyasiViewSet(viewsets.ModelViewSet):
    from .serializers import XarajatKategoriyasiSerializer
    from .models import XarajatKategoriyasi
    serializer_class = XarajatKategoriyasiSerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        from .models import XarajatKategoriyasi
        user = self.request.user
        queryset = XarajatKategoriyasi.objects.all()
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                biznes = user.xodim.biznes
                from django.db import models
                return queryset.filter(models.Q(biznes=biznes) | models.Q(biznes__isnull=True))
            return queryset.none()
        return queryset

    def perform_create(self, serializer):
        biznes = self.request.user.xodim.biznes if (self.request.user.is_authenticated and hasattr(self.request.user, 'xodim')) else None
        serializer.save(biznes=biznes)

    def list(self, request, *args, **kwargs):
        from .models import XarajatKategoriyasi
        queryset = self.filter_queryset(self.get_queryset())
        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None

        if not queryset.exists():
            default_names = ['Ijara', 'Transport', 'Oylik', 'Kommunal', 'Boshqa']
            created = []
            for name in default_names:
                obj = XarajatKategoriyasi.objects.create(nomi=name, biznes=biznes)
                created.append(obj)
            serializer = self.get_serializer(created, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return super().list(request, *args, **kwargs)


class XarajatFilter(django_filters.FilterSet):
    sana = django_filters.DateFilter(field_name="sana")
    dan = django_filters.DateFilter(field_name="sana", lookup_expr='gte')
    gacha = django_filters.DateFilter(field_name="sana", lookup_expr='lte')
    tolov_turi = django_filters.CharFilter(method='filter_tolov_turi')
    kategoriya = django_filters.CharFilter(method='filter_kategoriya')

    class Meta:
        from .models import Xarajat
        model = Xarajat
        fields = ['kategoriya', 'tolov_turi', 'sana', 'dan', 'gacha']

    def filter_tolov_turi(self, queryset, name, value):
        if not value or str(value).lower().strip() in ['barchasi', 'all', 'any', 'barchasi (to\'lov turi)', 'barchasi (to’lov turi)', '']:
            return queryset
        return queryset.filter(tolov_turi=value)

    def filter_kategoriya(self, queryset, name, value):
        if not value or str(value).lower().strip() in ['barchasi', 'all', 'any', 'barchasi (kategoriya)', '']:
            return queryset
        try:
            return queryset.filter(kategoriya_id=int(value))
        except (ValueError, TypeError):
            return queryset


class XarajatViewSet(viewsets.ModelViewSet):
    from .serializers import XarajatSerializer
    from .models import Xarajat
    serializer_class = XarajatSerializer
    permission_classes = [IsEmployee]
    pagination_class = DynamicPagination
    filterset_class = XarajatFilter
    search_fields = ['izoh', 'kategoriya__nomi', 'taminotchi__nomi']

    def get_queryset(self):
        from .models import Xarajat
        user = self.request.user
        queryset = Xarajat.objects.all().order_by('-sana', '-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        import traceback
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                try:
                    with open('error_log.txt', 'a', encoding='utf-8') as f:
                        f.write(f"Payload: {request.data}\nErrors: {serializer.errors}\n")
                except Exception:
                    pass
            return super().create(request, *args, **kwargs)
        except Exception as e:
            try:
                with open('error_log.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}\n")
            except Exception:
                pass
            raise

    def perform_create(self, serializer):
        biznes = None
        xodim = None
        if self.request.user.is_authenticated and hasattr(self.request.user, 'xodim'):
            xodim = self.request.user.xodim
            biznes = xodim.biznes
        serializer.save(biznes=biznes, xodim=xodim)
