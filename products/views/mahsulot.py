from decimal import Decimal
import datetime
from django.db.models import F, Q, Sum, ExpressionWrapper, DecimalField
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from products.models import Mahsulot, Characteristic, MahsulotRasm, MahsulotShtrixKod, YorliqShablon, DokonQoldiq
from products.serializers import MahsulotSerializer, CharacteristicSerializer, MahsulotRasmSerializer, MahsulotShtrixKodSerializer, YorliqShablonSerializer
from user.permissions import IsAdminOrOmborchiOrReadOnly, IsAdminOrOmborchi
from .common import DynamicPagination

class MahsulotViewSet(viewsets.ModelViewSet):
    serializer_class = MahsulotSerializer
    permission_classes = [IsAdminOrOmborchiOrReadOnly]
    
    filterset_fields = ['olchov_birligi', 'is_active', 'toifa', 'brend', 'taminotchi', 'erkin_narx']
    search_fields = ['nomi', 'shtrix_kodlar__kod']
    ordering_fields = ['kelish_narxi', 'sotish_narxi', 'miqdori', 'yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        queryset = Mahsulot.objects.all().prefetch_related('qoldiqlar', 'shtrix_kodlar').order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            pass
        elif user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            queryset = queryset.filter(biznes=user.xodim.biznes)
        else:
            queryset = queryset.none()
            
        kam_qoldi = self.request.query_params.get('kam_qoldi')
        if kam_qoldi is not None:
            if kam_qoldi.lower() == 'true':
                queryset = queryset.filter(qoldiqlar__miqdori__lte=F('qoldiqlar__ogohlantirish')).distinct()
            elif kam_qoldi.lower() == 'false':
                queryset = queryset.exclude(qoldiqlar__miqdori__lte=F('qoldiqlar__ogohlantirish')).distinct()

        dokon_id = self.request.query_params.get('dokon')
        if dokon_id is not None:
            queryset = queryset.filter(qoldiqlar__dokon_id=dokon_id, qoldiqlar__miqdori__gt=0)

        nol_qoldiq = self.request.query_params.get('nol_qoldiq')
        if nol_qoldiq is not None:
            if nol_qoldiq.lower() == 'true':
                if dokon_id:
                    queryset = queryset.filter(
                        Q(qoldiqlar__dokon_id=dokon_id, qoldiqlar__miqdori=0) |
                        ~Q(qoldiqlar__dokon_id=dokon_id)
                    ).distinct()
                else:
                    queryset = queryset.filter(miqdori=0)
            elif nol_qoldiq.lower() == 'false':
                if dokon_id:
                    queryset = queryset.filter(qoldiqlar__dokon_id=dokon_id, qoldiqlar__miqdori__gt=0)
                else:
                    queryset = queryset.filter(miqdori__gt=0)

        kelish_min = self.request.query_params.get('kelish_narxi_min')
        if kelish_min:
            queryset = queryset.filter(kelish_narxi__gte=kelish_min)
        kelish_max = self.request.query_params.get('kelish_narxi_max')
        if kelish_max:
            queryset = queryset.filter(kelish_narxi__lte=kelish_max)

        sotish_min = self.request.query_params.get('sotish_narxi_min')
        if sotish_min:
            queryset = queryset.filter(sotish_narxi__gte=sotish_min)
        sotish_max = self.request.query_params.get('sotish_narxi_max')
        if sotish_max:
            queryset = queryset.filter(sotish_narxi__lte=sotish_max)

        ulgurji_min = self.request.query_params.get('ulgurji_narx_min')
        if ulgurji_min:
            queryset = queryset.filter(ulgurji_narx__gte=ulgurji_min)
        ulgurji_max = self.request.query_params.get('ulgurji_narx_max')
        if ulgurji_max:
            queryset = queryset.filter(ulgurji_narx__lte=ulgurji_max)

        rang = self.request.query_params.get('rang')
        if rang:
            queryset = queryset.filter(characteristics__name__iexact='rang', characteristics__value__icontains=rang).distinct()

        oldin_buyurtma_qilingan = self.request.query_params.get('oldin_buyurtma_qilingan')
        if oldin_buyurtma_qilingan is not None:
            if oldin_buyurtma_qilingan.lower() == 'true':
                taminotchi_id = self.request.query_params.get('taminotchi')
                from orders.models import SupplierOrderItem
                biznes = user.xodim.biznes if (user.is_authenticated and hasattr(user, 'xodim')) else None
                ordered_products = SupplierOrderItem.objects.filter(order__biznes=biznes)
                if taminotchi_id:
                    ordered_products = ordered_products.filter(order__taminotchi_id=taminotchi_id)
                product_ids = ordered_products.values_list('mahsulot_id', flat=True)
                queryset = queryset.filter(id__in=product_ids)
                
        return queryset

    def filter_queryset(self, queryset):
        oldin_buy = self.request.query_params.get('oldin_buyurtma_qilingan')
        if oldin_buy and oldin_buy.lower() == 'true':
            q_params = self.request._request.GET.copy()
            taminotchi_val = q_params.pop('taminotchi', None)
            self.request._request.GET = q_params
            try:
                qs = super().filter_queryset(queryset)
            finally:
                if taminotchi_val is not None:
                    q_params['taminotchi'] = taminotchi_val
                    self.request._request.GET = q_params
            return qs
        return super().filter_queryset(queryset)

    def perform_create(self, serializer):
        biznes = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            biznes = self.request.user.xodim.biznes
            
        if biznes and biznes.tarif:
            limit = biznes.tarif.mahsulot_limiti
            if Mahsulot.objects.filter(biznes=biznes).count() >= limit:
                raise DRFValidationError({"detail": f"Tarif rejangiz bo'yicha mahsulotlar soni limiti ({limit}) tugagan. Iltimos tarifingizni yangilang."})
                
        serializer.save(biznes=biznes)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrOmborchi])
    def bulk_operations(self, request):
        action_type = request.data.get('action')
        product_ids = request.data.get('product_ids', [])
        params = request.data.get('params', {})

        if not action_type:
            return Response({"detail": "Amal ('action') ko'rsatilishi shart."}, status=status.HTTP_400_BAD_REQUEST)
        if not product_ids or not isinstance(product_ids, list):
            return Response({"detail": "Mahsulotlar ro'yxati ('product_ids') yuborilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        # MED-7: Limit bulk operations to prevent DoS
        MAX_BULK_IDS = 500
        if len(product_ids) > MAX_BULK_IDS:
            return Response({"detail": f"Bir vaqtda eng ko'pi bilan {MAX_BULK_IDS} ta mahsulot tanlanishi mumkin."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.is_superuser and user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            biznes = user.xodim.biznes
        elif user.is_superuser:
            biznes = None
        else:
            return Response({"detail": "Ruxsat etilmagan so'rov."}, status=status.HTTP_403_FORBIDDEN)

        queryset = Mahsulot.objects.filter(id__in=product_ids)
        if biznes:
            queryset = queryset.filter(biznes=biznes)

        if not queryset.exists():
            return Response({"detail": "Tanlangan tovarlar topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        if action_type == 'print_labels':
            label_data = []
            soni_turi = params.get('soni_turi', 'qolda')
            dokon_id = params.get('dokon')
            nol_qoldiq_otkazish = params.get('nol_qoldiq_otkazish', False)

            for p in queryset:
                shtrix_kod = ""
                if p.shtrix_kodlar.exists():
                    shtrix_kod = p.shtrix_kodlar.first().kod

                if dokon_id and str(dokon_id).isdigit():
                    qoldiq_obj = p.qoldiqlar.filter(dokon_id=int(dokon_id)).first()
                    real_stock = qoldiq_obj.miqdori if qoldiq_obj else 0
                else:
                    real_stock = p.miqdori

                if nol_qoldiq_otkazish and real_stock <= 0:
                    continue

                soni = 1
                if soni_turi == 'qoldiqlar_boyicha':
                    soni = real_stock

                label_data.append({
                    "nomi": p.nomi,
                    "shtrix_kod": shtrix_kod,
                    "sotish_narxi": str(p.sotish_narxi or '0.00'),
                    "olchov_birligi": p.olchov_birligi,
                    "soni": max(0, int(soni))
                })
            return Response({"success": True, "labels": label_data}, status=status.HTTP_200_OK)

        elif action_type == 'set_low_stock':
            threshold = params.get('threshold')
            if threshold is None:
                return Response({"detail": "Ogohlantirish miqdori ('threshold') kiritilishi shart."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                threshold_val = int(threshold)
                if threshold_val < 0:
                    raise ValueError
            except (ValueError, TypeError):
                return Response({"detail": "Ogohlantirish miqdori manfiy bo'lmagan butun son bo'lishi shart."}, status=status.HTTP_400_BAD_REQUEST)

            queryset.update(ogohlantirish=threshold_val)
            DokonQoldiq.objects.filter(mahsulot__in=queryset).update(ogohlantirish=threshold_val)
            return Response({"success": True, "message": "Kam qoldiq ogohlantirishi ommaviy sozlandi."}, status=status.HTTP_200_OK)

        elif action_type == 'edit_characteristics':
            characteristics_input = params.get('characteristics', {})
            if not isinstance(characteristics_input, dict):
                return Response({"detail": "Xususiyatlar to'g'ri formatda yuborilmadi (dict bo'lishi shart)."}, status=status.HTTP_400_BAD_REQUEST)

            char_objs = []
            for name, val in characteristics_input.items():
                name_clean = name.strip()
                val_clean = str(val).strip()
                if name_clean and val_clean:
                    char_obj, _ = Characteristic.objects.get_or_create(name=name_clean, value=val_clean)
                    char_objs.append(char_obj)

            for product in queryset:
                for name in characteristics_input.keys():
                    product.characteristics.filter(name__iexact=name.strip()).delete()
                if char_objs:
                    product.characteristics.add(*char_objs)
            return Response({"success": True, "message": "Mahsulot xususiyatlari ommaviy o'zgartirildi."}, status=status.HTTP_200_OK)

        elif action_type == 'edit_prices':
            price_type = params.get('price_type')
            operation = params.get('operation')
            value = params.get('value')
            erkin_narx = params.get('erkin_narx')

            if price_type is None and erkin_narx is None:
                return Response({"detail": "Kamida bitta o'zgartirish maydoni ('price_type' yoki 'erkin_narx') ko'rsatilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

            if erkin_narx is not None:
                queryset.update(erkin_narx=bool(erkin_narx))

            if price_type is not None:
                if price_type not in ['kelish_narxi', 'sotish_narxi', 'ulgurji_narx']:
                    return Response({"detail": "Noto'g'ri narx turi ('price_type')."}, status=status.HTTP_400_BAD_REQUEST)
                if operation not in ['belgilash', 'oshirish_foiz', 'kamaytirish_foiz', 'oshirish_summa', 'kamaytirish_summa']:
                    return Response({"detail": "Noto'g'ri narx amaliyoti ('operation')."}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    qiymat_val = Decimal(str(value))
                    if qiymat_val < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    return Response({"detail": "Narx qiymati ('value') manfiy bo'lmagan raqam bo'lishi shart."}, status=status.HTTP_400_BAD_REQUEST)

                for p in queryset:
                    old_val = getattr(p, price_type) or Decimal('0.00')
                    if operation == 'belgilash':
                        new_val = qiymat_val
                    elif operation == 'oshirish_foiz':
                        new_val = old_val * (1 + qiymat_val / 100)
                    elif operation == 'kamaytirish_foiz':
                        new_val = old_val * (1 - qiymat_val / 100)
                    elif operation == 'oshirish_summa':
                        new_val = old_val + qiymat_val
                    elif operation == 'kamaytirish_summa':
                        new_val = old_val - qiymat_val

                    if new_val < 0:
                        new_val = Decimal('0.00')
                    else:
                        new_val = new_val.quantize(Decimal('0.01'))

                    setattr(p, price_type, new_val)
                    if p.kelish_narxi > 0 and p.sotish_narxi > 0:
                        p.ustama = (((p.sotish_narxi - p.kelish_narxi) / p.kelish_narxi) * Decimal('100.00')).quantize(Decimal('0.01'))
                    p.save()

            return Response({"success": True, "message": "Mahsulot narxlari ommaviy o'zgartirildi."}, status=status.HTTP_200_OK)

        elif action_type == 'upload_images':
            images = request.FILES.getlist('images')
            if not images:
                return Response({"detail": "Yuklash uchun rasmlar ('images') topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

            for product in queryset:
                for img in images:
                    MahsulotRasm.objects.create(mahsulot=product, rasm=img)
            return Response({"success": True, "message": "Mahsulot rasmlari ommaviy yuklandi."}, status=status.HTTP_200_OK)

        elif action_type == 'archive':
            archive = params.get('archive')
            if archive is None:
                return Response({"detail": "Arxivlash holati ('archive') ko'rsatilishi shart."}, status=status.HTTP_400_BAD_REQUEST)
            
            is_active_val = not bool(archive)
            queryset.update(is_active=is_active_val)
            return Response({"success": True, "message": "Mahsulotlar holati ommaviy o'zgartirildi."}, status=status.HTTP_200_OK)

        else:
            return Response({"detail": f"Noto'g'ri ommaviy amal '{action_type}'."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        user = self.request.user
        queryset = Mahsulot.objects.all()
        if not user.is_superuser and user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            queryset = queryset.filter(biznes=user.xodim.biznes)
        elif not user.is_superuser:
            queryset = queryset.none()

        dokon_id = request.query_params.get('dokon')

        total_count = queryset.count()
        active_count = queryset.filter(is_active=True).count()
        inactive_count = queryset.filter(is_active=False).count()

        if dokon_id:
            low_stock_count = queryset.filter(qoldiqlar__dokon_id=dokon_id, qoldiqlar__miqdori__lte=F('qoldiqlar__ogohlantirish')).distinct().count()
            zero_stock_count = queryset.filter(
                Q(qoldiqlar__dokon_id=dokon_id, qoldiqlar__miqdori=0) |
                ~Q(qoldiqlar__dokon_id=dokon_id)
            ).distinct().count()
            
            tovar_birliklari = queryset.filter(qoldiqlar__dokon_id=dokon_id).aggregate(total_qty=Sum('qoldiqlar__miqdori'))['total_qty'] or 0
            
            qs_dokon = queryset.filter(qoldiqlar__dokon_id=dokon_id)
            cost_expr = ExpressionWrapper(F('kelish_narxi') * F('qoldiqlar__miqdori'), output_field=DecimalField())
            retail_expr = ExpressionWrapper(F('sotish_narxi') * F('qoldiqlar__miqdori'), output_field=DecimalField())
            
            cost_value = qs_dokon.aggregate(val=Sum(cost_expr))['val'] or Decimal('0.00')
            retail_value = qs_dokon.aggregate(val=Sum(retail_expr))['val'] or Decimal('0.00')
        else:
            low_stock_count = queryset.filter(qoldiqlar__miqdori__lte=F('qoldiqlar__ogohlantirish')).distinct().count()
            zero_stock_count = queryset.filter(miqdori=0).count()
            
            tovar_birliklari = queryset.aggregate(total_qty=Sum('miqdori'))['total_qty'] or 0
            
            cost_expr = ExpressionWrapper(F('kelish_narxi') * F('miqdori'), output_field=DecimalField())
            retail_expr = ExpressionWrapper(F('sotish_narxi') * F('miqdori'), output_field=DecimalField())
            
            cost_value = queryset.aggregate(val=Sum(cost_expr))['val'] or Decimal('0.00')
            retail_value = queryset.aggregate(val=Sum(retail_expr))['val'] or Decimal('0.00')

        from django.db.models import Count
        breakdown = queryset.values('olchov_birligi').annotate(count=Count('id'))
        unit_breakdown = {item['olchov_birligi']: item['count'] for item in breakdown}

        return Response({
            "total": total_count,
            "active": active_count,
            "inactive": inactive_count,
            "low_stock": low_stock_count,
            "zero_stock": zero_stock_count,
            "tovar_birliklari": tovar_birliklari,
            "cost_value": cost_value,
            "retail_value": retail_value,
            "unit_breakdown": unit_breakdown
        }, status=status.HTTP_200_OK)


class CharacteristicViewSet(viewsets.ModelViewSet):
    queryset = Characteristic.objects.all().order_by('-yaratilgan_vaqt')
    serializer_class = CharacteristicSerializer
    permission_classes = [IsAdminOrOmborchiOrReadOnly]
    search_fields = ['name', 'value']

    @action(detail=False, methods=['get'])
    def grouped(self, request):
        queryset = self.get_queryset()
        grouped_data = {}
        for char in queryset:
            name = char.name
            if name not in grouped_data:
                grouped_data[name] = []
            grouped_data[name].append({
                "id": char.id,
                "value": char.value
            })
        return Response(grouped_data, status=status.HTTP_200_OK)


class MahsulotRasmViewSet(viewsets.ModelViewSet):
    serializer_class = MahsulotRasmSerializer
    permission_classes = [IsAdminOrOmborchiOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = MahsulotRasm.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(mahsulot__biznes=user.xodim.biznes)
        return queryset.none()


class MahsulotShtrixKodViewSet(viewsets.ModelViewSet):
    serializer_class = MahsulotShtrixKodSerializer
    permission_classes = [IsAdminOrOmborchiOrReadOnly]
    filterset_fields = ['mahsulot']
    search_fields = ['kod']

    def get_queryset(self):
        user = self.request.user
        queryset = MahsulotShtrixKod.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(mahsulot__biznes=user.xodim.biznes)
        return queryset.none()

    def perform_destroy(self, instance):
        product = instance.mahsulot
        if product.shtrix_kodlar.count() <= 1:
            raise DRFValidationError({"detail": "Mahsulotning oxirgi shtrix kodini o'chirib bo'lmaydi. Kamida bitta shtrix kod bo'lishi shart."})
        instance.delete()


class YorliqShablonViewSet(viewsets.ModelViewSet):
    serializer_class = YorliqShablonSerializer
    permission_classes = [IsAdminOrOmborchiOrReadOnly]
    filterset_fields = ['is_active']
    search_fields = ['nomi']
    ordering_fields = ['nomi', 'yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        queryset = YorliqShablon.objects.all().order_by('-yaratilgan_vaqt')
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


from products.models import XususiyatMaydoni, Toplam
from products.serializers import XususiyatMaydoniSerializer, ToplamSerializer
from django.core.exceptions import ValidationError as DjangoValidationError

class XususiyatMaydoniViewSet(viewsets.ModelViewSet):
    serializer_class = XususiyatMaydoniSerializer
    permission_classes = [IsAdminOrOmborchiOrReadOnly]
    filterset_fields = ['is_active', 'tur']
    search_fields = ['nomi']
    ordering_fields = ['nomi', 'yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        queryset = XususiyatMaydoni.objects.all().order_by('-yaratilgan_vaqt')
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


class ToplamViewSet(viewsets.ModelViewSet):
    serializer_class = ToplamSerializer
    permission_classes = [IsAdminOrOmborchi]
    filterset_fields = ['dokon', 'holat']
    search_fields = ['nomi']
    ordering_fields = ['miqdori', 'summa', 'yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        queryset = Toplam.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()

    def perform_create(self, serializer):
        yaratgan_xodim = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            yaratgan_xodim = self.request.user.xodim

        toplam_obj = serializer.save()
        
        try:
            toplam_obj.confirm_and_execute(executor_xodim=yaratgan_xodim)
        except DjangoValidationError as e:
            raise DRFValidationError({'detail': str(e)})

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        toplam_obj = self.get_object()
        xodim = request.user.xodim if hasattr(request.user, 'xodim') else None
        try:
            toplam_obj.confirm_and_execute(executor_xodim=xodim)
        except DjangoValidationError as e:
            raise DRFValidationError({'detail': str(e)})
        return Response({
            'status': "Muvaffaqiyatli qabul qilindi.",
            'holat': toplam_obj.holat
        }, status=status.HTTP_200_OK)
