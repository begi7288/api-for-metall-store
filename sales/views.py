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
        return super().list(request, *args, **kwargs)

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
            
        data = {
            'chek_id': sale.id,
            'kod': sale.kod,
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
                'telefon': sale.mijoz.telefon_raqam_1 if sale.mijoz else ""
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
        
        # Jami chiqim: Total supplier payments + write-offs cost in the same business/date range
        user = request.user
        jami_chiqim = Decimal('0.00')
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            biznes = user.xodim.biznes
            from orders.models import SupplierOrderPayment
            from products.models import WriteOff
            
            p_qs = SupplierOrderPayment.objects.filter(order__biznes=biznes)
            w_qs = WriteOff.objects.filter(biznes=biznes, holat='yakunlangan')
            
            dan = request.query_params.get('dan') or request.query_params.get('sana_dan')
            gacha = request.query_params.get('gacha') or request.query_params.get('sana_gacha')
            
            if dan:
                p_qs = p_qs.filter(yaratilgan_vaqt__date__gte=dan)
                w_qs = w_qs.filter(yaratilgan_vaqt__date__gte=dan)
            if gacha:
                p_qs = p_qs.filter(yaratilgan_vaqt__date__lte=gacha)
                w_qs = w_qs.filter(yaratilgan_vaqt__date__lte=gacha)
                
            supplier_payments_sum = p_qs.aggregate(total=models.Sum('tolangan_summa'))['total'] or Decimal('0.00')
            write_offs_sum = w_qs.aggregate(total=models.Sum('kelish_summasi'))['total'] or Decimal('0.00')
            jami_chiqim = supplier_payments_sum + write_offs_sum

        return Response({
            'jami_kirim': str(jami_kirim),
            'jami_chiqim': str(jami_chiqim),
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
        from datetime import timedelta
        from .models import SaleItem

        user = request.user
        base_sales = self.filter_queryset(self.get_queryset())
        completed_sales = base_sales.filter(holat='yakunlangan')

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        today_sales_qs = completed_sales.filter(yaratilgan_vaqt__date=today)
        bugungi_savdo = today_sales_qs.aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')

        yesterday_sales_qs = completed_sales.filter(yaratilgan_vaqt__date=yesterday)
        yesterday_sales = yesterday_sales_qs.aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')

        savdo_osish = 0.0
        if yesterday_sales > 0:
            savdo_osish = round(float((bugungi_savdo - yesterday_sales) / yesterday_sales * 100), 2)

        bugungi_xarajat = Decimal('0.00')
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            biznes = user.xodim.biznes
            from orders.models import SupplierOrderPayment
            from products.models import WriteOff
            sp_today = SupplierOrderPayment.objects.filter(order__biznes=biznes, yaratilgan_vaqt__date=today).aggregate(total=models.Sum('tolangan_summa'))['total'] or Decimal('0.00')
            wo_today = WriteOff.objects.filter(biznes=biznes, holat='yakunlangan', yaratilgan_vaqt__date=today).aggregate(total=models.Sum('kelish_summasi'))['total'] or Decimal('0.00')
            bugungi_xarajat = sp_today + wo_today

        sof_pul = max(Decimal('0.00'), bugungi_savdo - bugungi_xarajat)

        credit_sales_qs = base_sales.filter(yaratilgan_vaqt__date=today, nasiya_summa__gt=0)
        nasiyaga_sotilgan = credit_sales_qs.aggregate(total=models.Sum('nasiya_summa'))['total'] or Decimal('0.00')
        nasiya_buyurtmalar_soni = credit_sales_qs.count()

        total_sales_count = completed_sales.count()
        naqd_count = completed_sales.filter(tolov_usuli='naqd').count()
        karta_count = completed_sales.filter(tolov_usuli='karta').count()
        nasiya_count = completed_sales.filter(tolov_usuli='nasiya').count()

        naqd_percent = round((naqd_count / total_sales_count * 100), 1) if total_sales_count > 0 else 0.0
        karta_percent = round((karta_count / total_sales_count * 100), 1) if total_sales_count > 0 else 0.0
        nasiya_percent = round((nasiya_count / total_sales_count * 100), 1) if total_sales_count > 0 else 0.0

        items = SaleItem.objects.filter(sotuv__in=completed_sales)
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

        return Response({
            'bugungi_savdo': str(bugungi_savdo),
            'today_sales': str(bugungi_savdo),
            'todaySales': str(bugungi_savdo),
            'savdo_osish': savdo_osish,
            'bugungi_xarajat': str(bugungi_xarajat),
            'today_expenses': str(bugungi_xarajat),
            'todayExpenses': str(bugungi_xarajat),
            'sof_pul': str(sof_pul),
            'net_cash': str(sof_pul),
            'netCash': str(sof_pul),
            'nasiyaga_sotilgan': str(nasiyaga_sotilgan),
            'credit_sales': str(nasiyaga_sotilgan),
            'creditSales': str(nasiyaga_sotilgan),
            'nasiya_buyurtmalar_soni': nasiya_buyurtmalar_soni,

            'tolov_turlari': {
                'naqd': naqd_percent,
                'karta': karta_percent,
                'nasiya': nasiya_percent,
            },

            'top_5_mahsulot': top_5_list,
            'top_products': top_5_list,
            'topProducts': top_5_list,

            'oxirgi_harakatlar': recent_activities,
            'recent_activities': recent_activities,
            'recentActivities': recent_activities,
        }, status=status.HTTP_200_OK)

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
        from datetime import timedelta
        from .models import Xarajat, XarajatKategoriyasi

        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None

        today = timezone.now().date()
        daily_list = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            kirim = Sale.objects.filter(biznes=biznes, holat='yakunlangan', yaratilgan_vaqt__date=day).aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')
            chiqim = Xarajat.objects.filter(biznes=biznes, sana=day).aggregate(total=models.Sum('miqdor'))['total'] or Decimal('0.00')
            sof = max(Decimal('0.00'), kirim - chiqim)
            daily_list.append({
                'sana': day.strftime("%d.%m.%Y"),
                'date': day.strftime("%Y-%m-%d"),
                'kirim': str(kirim),
                'income': str(kirim),
                'chiqim': str(chiqim),
                'expense': str(chiqim),
                'sof_pul': str(sof),
                'net_cash': str(sof)
            })

        cat_list = []
        categories = XarajatKategoriyasi.objects.filter(models.Q(biznes=biznes) | models.Q(biznes__isnull=True))
        for cat in categories:
            total_exp = Xarajat.objects.filter(biznes=biznes, kategoriya=cat).aggregate(total=models.Sum('miqdor'))['total'] or Decimal('0.00')
            cat_list.append({
                'id': cat.id,
                'nomi': cat.nomi,
                'summa': str(total_exp)
            })

        return Response({
            'dinamika': daily_list,
            'chiqim_kategoriyalari': cat_list,
            'kunlik_pul_oqimi': daily_list,
            'daily_cash_flow': daily_list
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def monthly(self, request):
        from django.db import models
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta

        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None

        today = timezone.now().date()
        first_of_this_month = today.replace(day=1)
        first_of_last_month = (first_of_this_month - timedelta(days=1)).replace(day=1)
        end_of_last_month = first_of_this_month - timedelta(days=1)

        joriy_oy_sum = Sale.objects.filter(biznes=biznes, holat='yakunlangan', yaratilgan_vaqt__date__gte=first_of_this_month).aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')
        otgan_oy_sum = Sale.objects.filter(biznes=biznes, holat='yakunlangan', yaratilgan_vaqt__date__gte=first_of_last_month, yaratilgan_vaqt__date__lte=end_of_last_month).aggregate(total=models.Sum('yakuniy_summa'))['total'] or Decimal('0.00')

        return Response({
            'otgan_oy': str(otgan_oy_sum),
            'last_month': str(otgan_oy_sum),
            'joriy_oy': str(joriy_oy_sum),
            'current_month': str(joriy_oy_sum),
            'eng_yaxshi_kun': {'sana': '-', 'summa': '0.00'},
            'eng_sust_kun': {'sana': '-', 'summa': '0.00'},
            'dinamika': []
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def products_analytics(self, request):
        from django.db import models
        from .models import SaleItem

        completed_sales = self.filter_queryset(self.get_queryset()).filter(holat='yakunlangan')
        items = SaleItem.objects.filter(sotuv__in=completed_sales)
        top_items = items.values('mahsulot', 'mahsulot__nomi').annotate(
            jami_miqdor=models.Sum('miqdori'),
            jami_summa=models.Sum('jami_summa')
        ).order_by('-jami_summa')

        data = []
        for item in top_items:
            qty = item['jami_miqdor'] or 1
            summa = item['jami_summa'] or Decimal('0.00')
            data.append({
                'mahsulot_id': item['mahsulot'],
                'nomi': item['mahsulot__nomi'],
                'miqdor': item['jami_miqdor'],
                'sotuv_summasi': str(summa),
                'ortacha_narx': str(round(summa / qty, 2))
            })
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def debts_analytics(self, request):
        from user.models import MijozQarzi, MijozTolovi
        user = request.user
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None

        qarzlar = MijozQarzi.objects.filter(biznes=biznes) if biznes else MijozQarzi.objects.none()
        tolovlar = MijozTolovi.objects.filter(biznes=biznes).order_by('-yaratilgan_vaqt')[:5] if biznes else MijozTolovi.objects.none()

        recent_payments = [
            {
                'ismlar': f"{t.mijoz.ism} {t.mijoz.familiya}" if t.mijoz else "Anonim",
                'summa': str(t.tolangan_summa),
                'sana': t.yaratilgan_vaqt.strftime("%d.%m.%Y") if t.yaratilgan_vaqt else ""
            }
            for t in tolovlar
        ]

        debtors_table = [
            {
                'mijoz': f"{q.mijoz.ism} {q.mijoz.familiya}" if q.mijoz else "Mijoz",
                'umumiy_qarz': str(q.qoldiq_summa),
                'muddati_otgan': 0,
                'oxirgi_tolov': '-',
                'holat': q.get_holat_display()
            }
            for q in qarzlar[:10]
        ]

        return Response({
            'aging': {'0-30': 0, '31-60': 0, '61-90': 0, '90+': 0},
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
        biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None

        products = Mahsulot.objects.filter(biznes=biznes) if biznes else Mahsulot.objects.none()

        categories_def = {
            'AX': {'count': 0, 'label': 'AX - Kassa Generatorlari', 'xulosa': 'Juda yuqori aylanma va barqaror talab.', 'tavsiya': 'Doimiy ombor qoldig\'ini ta\'minlang.'},
            'AY': {'count': 0, 'label': 'AY - Mavsumiy', 'xulosa': 'Yuqori aylanma, lekin talab mavsumiy o\'zgaradi.', 'tavsiya': 'Mavsumiylik va aksiyalarni hisobga oling.'},
            'AZ': {'count': 0, 'label': 'AZ - Katta Tavakkal', 'xulosa': 'Sotilsa juda katta kassa qiladi, lekin qachon sotilishi noma\'lum.', 'tavsiya': 'Omborda katta zaxira saqlamang. Faqat buyurtma asosida ishlang.'},
            'BX': {'count': 0, 'label': 'BX - Barqaror O\'rtacha', 'xulosa': 'O\'rtacha aylanma va barqaror sotuv.', 'tavsiya': 'Optimal zaxira darajasini saqlang.'},
            'BY': {'count': 0, 'label': 'BY - O\'rtacha O\'zgaruvchan', 'xulosa': 'O\'rtacha aylanma va o\'zgaruvchan sotuv.', 'tavsiya': 'Talab dinamikasini kuzatib boring.'},
            'BZ': {'count': 0, 'label': 'BZ - Noaniq O\'rtacha', 'xulosa': 'O\'rtacha aylanma, noaniq talab.', 'tavsiya': 'Kichik partiyalarda xarid qiling.'},
            'CX': {'count': 0, 'label': 'CX - Past Barqaror', 'xulosa': 'Past aylanma, lekin barqaror talab.', 'tavsiya': 'Zaxirani minimal darajada tuting.'},
            'CY': {'count': 0, 'label': 'CY - Past O\'zgaruvchan', 'xulosa': 'Past aylanma va o\'zgaruvchan sotuv.', 'tavsiya': 'Xaridlarni optimallashtiring.'},
            'CZ': {'count': 0, 'label': 'CZ - O\'lik Kapital', 'xulosa': 'Past aylanma va noaniq talab.', 'tavsiya': 'Tugallash yoki sotuvdan chiqarish choralarini ko\'ring.'},
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
                'ombor_qoldigi': p.miqdori,
                'aylanma': str(aylanma),
                'sof_foyda': str(round(aylanma * Decimal('0.2'), 2)),
                'tavsiya': categories_def[cat]['tavsiya']
            })

        matrix = {
            k: {
                'count': v['count'],
                'label': v['label'],
                'xulosa': v['xulosa'],
                'tavsiya': v['tavsiya']
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
                'olik_kapital': categories_def['CZ']['count'],
                'mavsumiy': categories_def['AY']['count']
            },
            'matrix': matrix,
            'products': products_data,
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
    tolov_turi = django_filters.CharFilter(field_name="tolov_turi")
    kategoriya = django_filters.NumberFilter(field_name="kategoriya")

    class Meta:
        from .models import Xarajat
        model = Xarajat
        fields = ['kategoriya', 'tolov_turi', 'sana', 'dan', 'gacha']


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

    def perform_create(self, serializer):
        biznes = None
        xodim = None
        if self.request.user.is_authenticated and hasattr(self.request.user, 'xodim'):
            xodim = self.request.user.xodim
            biznes = xodim.biznes
        serializer.save(biznes=biznes, xodim=xodim)
