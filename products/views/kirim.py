from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from decimal import Decimal

from ..models import Import, Dokon, Taminotchi
from ..serializers.kirim import KirimSerializer
from user.permissions import IsAdminOrOmborchi, IsEmployee

class KirimViewSet(viewsets.ModelViewSet):
    """
    Omborga kirim (Warehouse Manual Stock Inward) ViewSet.
    Provides API for manual stock entry form, listing inward entries, confirmation, and statistics.
    """
    queryset = Import.objects.filter(import_turi='kirim')
    serializer_class = KirimSerializer
    permission_classes = [IsAuthenticated, IsEmployee]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['dokon', 'taminotchi', 'tolov_turi', 'holat']
    search_fields = ['nomi', 'chek_raqami', 'elementlar__nomi', 'taminotchi__nomi']
    ordering_fields = ['yaratilgan_vaqt', 'kelish_summasi', 'miqdori']
    ordering = ['-yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        qs = Import.objects.filter(import_turi__in=['kirim', 'qoldiq_kirimi']).exclude(holat='xatolik')
        if hasattr(user, 'xodim') and user.xodim.biznes:
            qs = qs.filter(biznes=user.xodim.biznes)
        elif not user.is_superuser:
            return qs.none()
        return qs.select_related('biznes', 'dokon', 'taminotchi', 'yaratgan_xodim', 'yakunlagan_xodim')

    def perform_create(self, serializer):
        user = self.request.user
        biznes = None
        executor_xodim = None
        if hasattr(user, 'xodim'):
            executor_xodim = user.xodim
            biznes = user.xodim.biznes

        dokon_id = self.request.data.get('dokon')
        dokon = None
        if dokon_id:
            try:
                dokon = Dokon.objects.get(id=dokon_id, biznes=biznes)
            except Dokon.DoesNotExist:
                pass
        if not dokon and hasattr(executor_xodim, 'dokon') and executor_xodim.dokon:
            dokon = executor_xodim.dokon
        if not dokon and biznes:
            dokon = Dokon.objects.filter(biznes=biznes).first()

        try:
            kirim_obj = serializer.save(
                biznes=biznes,
                dokon=dokon,
                yaratgan_xodim=executor_xodim
            )
            if kirim_obj.holat == 'kutilmoqda':
                kirim_obj.confirm_and_execute(executor_xodim=executor_xodim)

            if kirim_obj.holat == 'yakunlangan' and kirim_obj.taminotchi:
                from orders.models import SupplierOrder
                from django.utils import timezone

                is_nasiya = (kirim_obj.tolov_turi == 'nasiya')
                paid_amt = Decimal('0.00') if is_nasiya else kirim_obj.kelish_summasi
                debt_amt = kirim_obj.kelish_summasi if is_nasiya else Decimal('0.00')

                so, created = SupplierOrder.objects.get_or_create(
                    biznes=kirim_obj.biznes,
                    taminotchi=kirim_obj.taminotchi,
                    dokon=kirim_obj.dokon,
                    nomi=f"Kirim #{kirim_obj.chek_raqami or kirim_obj.id}",
                    defaults={
                        'holat': 'qabul_qilingan',
                        'qabul_qilish_sanasi': timezone.now().date(),
                        'yaratgan_xodim': kirim_obj.yaratgan_xodim,
                        'umumiy_summa': kirim_obj.kelish_summasi,
                        'sotuv_summasi': kirim_obj.sotish_summasi,
                        'tolangan_summa': Decimal('0.00'),
                        'nasiya_summa': debt_amt,
                    }
                )
                
                if created:
                    from orders.models import SupplierOrderItem
                    from products.models import Mahsulot
                    for item in kirim_obj.elementlar:
                        shtrix_kod = item.get('shtrix_kod')
                        nomi = item.get('nomi')
                        miqdori = int(item.get('miqdori', 1))
                        kelish_narxi = Decimal(str(item.get('kelish_narxi', 0.0)))
                        sotish_narxi = Decimal(str(item.get('sotish_narxi', 0.0)))
                        
                        product = None
                        if shtrix_kod:
                            product = Mahsulot.objects.filter(biznes=kirim_obj.biznes, shtrix_kodlar__kod=shtrix_kod).first()
                        if not product and nomi:
                            product = Mahsulot.objects.filter(biznes=kirim_obj.biznes, nomi=nomi).first()
                            
                        if product:
                            ustama = Decimal('0.00')
                            if kelish_narxi > 0 and sotish_narxi > 0:
                                ustama = (((sotish_narxi - kelish_narxi) / kelish_narxi) * Decimal('100.00')).quantize(Decimal('0.01'))
                            
                            SupplierOrderItem.objects.create(
                                order=so,
                                mahsulot=product,
                                miqdori=miqdori,
                                kelish_narxi=kelish_narxi,
                                ustama=ustama,
                                sotish_narxi=sotish_narxi
                            )
                    
                    # Set the actual paid amount after items are created and validated
                    so.tolangan_summa = paid_amt
                    so.save()

                if created and is_nasiya and kirim_obj.taminotchi.balans > 0 and so.nasiya_summa > 0:
                    use_balans = min(kirim_obj.taminotchi.balans, so.nasiya_summa)
                    so.add_payment(use_balans, 'balans_postavshika', executor_xodim)
        except DjangoValidationError as e:
            if hasattr(e, 'message_dict'):
                raise DRFValidationError(e.message_dict)
            else:
                raise DRFValidationError({'detail': e.messages})

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        kirim_obj = self.get_object()
        if kirim_obj.holat == 'yakunlangan':
            return Response({
                'status': "Omborga kirim allaqachon yakunlangan.",
                'holat': kirim_obj.holat
            }, status=status.HTTP_200_OK)

        executor_xodim = request.user.xodim if hasattr(request.user, 'xodim') else None

        try:
            kirim_obj.confirm_and_execute(executor_xodim=executor_xodim)
            
            # If supplier is set, create a SupplierOrder to properly record purchase debt and payments
            if kirim_obj.taminotchi:
                from orders.models import SupplierOrder
                from django.utils import timezone

                is_nasiya = (kirim_obj.tolov_turi == 'nasiya')
                paid_amt = Decimal('0.00') if is_nasiya else kirim_obj.kelish_summasi
                debt_amt = kirim_obj.kelish_summasi if is_nasiya else Decimal('0.00')

                so = SupplierOrder.objects.create(
                    biznes=kirim_obj.biznes,
                    taminotchi=kirim_obj.taminotchi,
                    dokon=kirim_obj.dokon,
                    nomi=f"Kirim #{kirim_obj.chek_raqami or kirim_obj.id}",
                    holat='qabul_qilingan',
                    qabul_qilish_sanasi=timezone.now().date(),
                    yaratgan_xodim=kirim_obj.yaratgan_xodim,
                    umumiy_summa=kirim_obj.kelish_summasi,
                    tolangan_summa=Decimal('0.00'),
                    nasiya_summa=debt_amt
                )

                from orders.models import SupplierOrderItem
                from products.models import Mahsulot
                for item in kirim_obj.elementlar:
                    shtrix_kod = item.get('shtrix_kod')
                    nomi = item.get('nomi')
                    miqdori = int(item.get('miqdori', 1))
                    kelish_narxi = Decimal(str(item.get('kelish_narxi', 0.0)))
                    sotish_narxi = Decimal(str(item.get('sotish_narxi', 0.0)))
                    
                    product = None
                    if shtrix_kod:
                        product = Mahsulot.objects.filter(biznes=kirim_obj.biznes, shtrix_kodlar__kod=shtrix_kod).first()
                    if not product and nomi:
                        product = Mahsulot.objects.filter(biznes=kirim_obj.biznes, nomi=nomi).first()
                        
                    if product:
                        ustama = Decimal('0.00')
                        if kelish_narxi > 0 and sotish_narxi > 0:
                            ustama = (((sotish_narxi - kelish_narxi) / kelish_narxi) * Decimal('100.00')).quantize(Decimal('0.01'))
                        
                        SupplierOrderItem.objects.create(
                            order=so,
                            mahsulot=product,
                            miqdori=miqdori,
                            kelish_narxi=kelish_narxi,
                            ustama=ustama,
                            sotish_narxi=sotish_narxi
                        )

                # Set the actual paid amount after items are created and validated
                so.tolangan_summa = paid_amt
                so.save()

                # If debt exists and supplier has advance deposit (balans > 0), auto-apply balance
                if is_nasiya and kirim_obj.taminotchi.balans > 0 and so.nasiya_summa > 0:
                    use_balans = min(kirim_obj.taminotchi.balans, so.nasiya_summa)
                    so.add_payment(use_balans, 'balans_postavshika', executor_xodim)

        except Exception as e:
            raise DRFValidationError({'detail': str(e)})

        try:
            from user.telegram_bot import notify_import
            notify_import(kirim_obj)
        except Exception:
            pass

        return Response({
            'status': "Omborga kirim muvaffaqiyatli yakunlandi.",
            'holat': kirim_obj.holat
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        kirim_obj = self.get_object()
        if kirim_obj.holat == 'yakunlangan':
            raise DRFValidationError({'detail': "Yakunlangan kirimni bekor qilib bo'lmaydi."})

        kirim_obj.holat = 'bekor_qilingan'
        kirim_obj.save(update_fields=['holat'])

        return Response({
            'status': "Kirim bekor qilindi.",
            'holat': kirim_obj.holat
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        cheklar = queryset.count()
        soni = queryset.aggregate(total=Sum('miqdori'))['total'] or 0
        jami = queryset.aggregate(total=Sum('kelish_summasi'))['total'] or Decimal('0.00')

        return Response({
            'cheklar': cheklar,
            'soni': soni,
            'jami': str(jami)
        }, status=status.HTTP_200_OK)
