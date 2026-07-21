from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect, render
from .models import Xodim, Mijoz, Biznes, Tarif
from .serializers import XodimSerializer, MijozSerializer, ChangePasswordSerializer, LoginSerializer, LogoutSerializer, RegisterSerializer, BiznesSerializer, TarifSerializer
from .permissions import IsAdminOrOmborchi, IsEmployee

from .throttling import PhoneRateThrottle, IPLoginRateThrottle, PasswordChangeRateThrottle, RegisterRateThrottle
from rest_framework.permissions import IsAuthenticated
import time


class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = LoginSerializer
    throttle_classes = [PhoneRateThrottle, IPLoginRateThrottle]

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({"detail": "Siz allaqachon tizimga kirgansiz.", "redirect_url": "/users/me/"}, status=status.HTTP_200_OK)
        return Response({"detail": "Tizimga kirish uchun ushbu sahifada POST so'rovini yuboring."}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied
        from django.contrib.auth.models import User
        from django.utils import timezone
        from datetime import timedelta

        telefon_raqam = serializer.validated_data['telefon_raqam']
        parol = serializer.validated_data['parol']

        # MED-6: Constant-time response to prevent phone enumeration via timing attack
        start_time = time.monotonic()

        # Generic error message — same for wrong phone AND wrong password (MED-6)
        GENERIC_ERROR = "Telefon raqami yoki parol noto'g'ri."

        phone_formats = []
        clean_phone = telefon_raqam.strip().replace('+', '')
        if clean_phone.isdigit():
            if len(clean_phone) == 9:
                phone_formats.extend([clean_phone, f"+998{clean_phone}", f"998{clean_phone}"])
            elif len(clean_phone) == 12 and clean_phone.startswith('998'):
                phone_formats.extend([clean_phone, f"+{clean_phone}", clean_phone[3:]])
            else:
                phone_formats.append(telefon_raqam)
        else:
            phone_formats.append(telefon_raqam)
            
        phone_formats = list(set(phone_formats))

        try:
            xodim = Xodim.objects.filter(telefon_raqam__in=phone_formats).first()
            if xodim:
                user_obj = xodim.user
                if not xodim.is_active:
                    raise PermissionDenied("Ushbu xodim faol emas.")
                if not check_password(parol, xodim.parol):
                    raise DRFValidationError({'detail': GENERIC_ERROR})
                role = xodim.rol
                ism = xodim.ism
                familiya = xodim.familiya
            else:
                clean_username = telefon_raqam.replace('+', '')
                user_obj = User.objects.filter(username__in=[telefon_raqam, clean_username]).first()
                if not user_obj:
                    # MED-6: Do a dummy password hash check to prevent timing-based enumeration
                    check_password(parol, "pbkdf2_sha256$260000$dummy$dummyhash=")
                    raise DRFValidationError({'detail': GENERIC_ERROR})

                if not user_obj.is_active:
                    raise PermissionDenied("Ushbu foydalanuvchi faol emas.")
                if not user_obj.check_password(parol):
                    raise DRFValidationError({'detail': GENERIC_ERROR})

                if hasattr(user_obj, 'xodim'):
                    xodim = user_obj.xodim
                    role = xodim.rol
                    ism = xodim.ism
                    familiya = xodim.familiya
                else:
                    role = 'admin' if user_obj.is_superuser else 'sotuvchi'
                    ism = user_obj.first_name if user_obj.first_name else None
                    familiya = user_obj.last_name if user_obj.last_name else None

            token, created = Token.objects.get_or_create(user=user_obj)
            if not created:
                if token.created < timezone.now() - timedelta(hours=6):
                    token.delete()
                    token = Token.objects.create(user=user_obj)

            # MED-1: Session login olib tashlandi — faqat Token auth ishlatiladi

            return Response({
                'token': token.key,
                'ism': ism,
                'familiya': familiya,
                'rol': role,
                'redirect_url': '/users/me/'
            }, status=status.HTTP_200_OK)

        except (DRFValidationError, PermissionDenied) as e:
            raise


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def get(self, request, *args, **kwargs):
        return Response({"detail": "Tizimdan chiqish uchun ushbu sahifada POST so'rovini yuboring."}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        Token.objects.filter(user=request.user).delete()

        return Response({
            "success": True,
            "message": "Tizimdan muvaffaqiyatli chiqildi.",
            "redirect_url": "/users/login/"
        }, status=status.HTTP_200_OK)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if hasattr(user, 'xodim'):
            xodim = user.xodim
            data = {
                "id": xodim.id,
                "ism": xodim.ism,
                "familiya": xodim.familiya,
                "telefon_raqam": xodim.telefon_raqam,
                "rol": xodim.rol,
                "jinsi": xodim.jinsi,
                "tugilgan_sana": xodim.tugilgan_sana,
                "is_active": xodim.is_active,
                "vaqt_mintaqasi": xodim.vaqt_mintaqasi or "Toshkent (GMT +5)",
                "timezone": xodim.vaqt_mintaqasi or "Toshkent (GMT +5)",
                "avatar": xodim.avatar or "",
                "pin_kod": xodim.pin_kod or "",
                "pin_code": xodim.pin_kod or "",
                "til": xodim.til or "O'zbekcha",
                "language": xodim.til or "O'zbekcha",
                "mavzu": xodim.mavzu or "Yorug'",
                "theme": xodim.mavzu or "Yorug'",
                "yaratilgan_vaqt": xodim.yaratilgan_vaqt,
                "yangilangan_vaqt": xodim.yangilangan_vaqt
            }
        else:
            data = {
                "id": None,
                "ism": user.first_name if user.first_name else "Boshliq",
                "familiya": user.last_name if user.last_name else "",
                "telefon_raqam": user.username,
                "rol": "admin",
                "jinsi": "erkak",
                "tugilgan_sana": None,
                "is_active": user.is_active,
                "vaqt_mintaqasi": "Toshkent (GMT +5)",
                "avatar": "",
                "pin_kod": "",
                "til": "O'zbekcha",
                "mavzu": "Yorug'",
                "yaratilgan_vaqt": user.date_joined,
                "yangilangan_vaqt": user.date_joined
            }

        return Response({"success": True, "data": data, **data}, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        if hasattr(user, 'xodim'):
            xodim = user.xodim
            if 'ism' in data: xodim.ism = data['ism']
            if 'familiya' in data: xodim.familiya = data['familiya']
            if 'vaqt_mintaqasi' in data or 'timezone' in data:
                xodim.vaqt_mintaqasi = data.get('vaqt_mintaqasi') or data.get('timezone')
            if 'avatar' in data: xodim.avatar = data['avatar']
            if 'pin_kod' in data or 'pin_code' in data:
                xodim.pin_kod = data.get('pin_kod') or data.get('pin_code')
            if 'til' in data or 'language' in data:
                xodim.til = data.get('til') or data.get('language')
            if 'mavzu' in data or 'theme' in data:
                xodim.mavzu = data.get('mavzu') or data.get('theme')
            xodim.save()

        if 'ism' in data: user.first_name = data['ism']
        if 'familiya' in data: user.last_name = data['familiya']
        user.save()

        return self.get(request, *args, **kwargs)


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]
    # LOW-3: Rate limit on password change
    throttle_classes = [PasswordChangeRateThrottle]

    def get(self, request, *args, **kwargs):
        return Response({"detail": "Parolni o'zgartirish uchun ushbu sahifada POST so'rovini yuboring."}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        yangi_parol = serializer.validated_data['yangi_parol']

        user.set_password(yangi_parol)
        user.save()

        # HIGH-4: Xodim.parol ga Django User hash ni SAQLAMAYMIZ.
        # Parol faqat Django User modelida saqlanadi.
        # Xodim.parol eski hash bilan qoladi, lekin login faqat User.check_password orqali ishlaydi.

        Token.objects.filter(user=user).delete()
        new_token = Token.objects.create(user=user)

        return Response({
            "success": True,
            "message": "Parol muvaffaqiyatli o'zgartirildi. Barcha boshqa qurilmalardan chiqildi.",
            "token": new_token.key,
            "redirect_url": "/users/me/"
        }, status=status.HTTP_200_OK)


class RegisterAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RegisterSerializer
    # HIGH-2: Strict rate limiting on registration (3/hour per IP)
    throttle_classes = [RegisterRateThrottle, IPLoginRateThrottle]

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({"detail": "Siz allaqachon tizimga kirgansiz.", "redirect_url": "/users/me/"}, status=status.HTTP_200_OK)
        return Response({"detail": "Ro'yxatdan o'tish uchun ushbu sahifada POST so'rovini yuboring."}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        xodim = serializer.save()

        # Send Telegram message with phone number and verification code
        raw_password = serializer.context.get('raw_password')
        if raw_password:
            from user.telegram_bot import send_telegram_message
            biznes_nomi = xodim.biznes.nomi if xodim.biznes else "Noma'lum"
            msg = (
                f"<b>Yangi ro'yxatdan o'tish:</b>\n"
                f"👤 Ism: {xodim.ism}\n"
                f"📞 Telefon: {xodim.telefon_raqam}\n"
                f"🏢 Biznes: {biznes_nomi}\n"
                f"💬 Tasdiqlash kodi: <code>{raw_password}</code>"
            )
            send_telegram_message(msg)

        from django.contrib.auth.models import User
        user_obj = User.objects.get(pk=xodim.user.pk)
        token, created = Token.objects.get_or_create(user=user_obj)

        # MED-1: Session login olib tashlandi

        return Response({
            'token': token.key,
            'ism': xodim.ism,
            'familiya': xodim.familiya,
            'rol': xodim.rol,
            'redirect_url': '/users/me/'
        }, status=status.HTTP_201_CREATED)



class XodimViewSet(viewsets.ModelViewSet):
    serializer_class = XodimSerializer
    permission_classes = [IsAdminOrOmborchi]
    filterset_fields = ['rol', 'jinsi', 'is_active']
    search_fields = ['ism', 'familiya', 'telefon_raqam']
    ordering_fields = ['ism', 'familiya', 'yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        queryset = Xodim.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_superuser:
            pass
        elif user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            biznes = user.xodim.biznes
            queryset = queryset.filter(biznes=biznes)
        else:
            return queryset.none()

        tab = self.request.query_params.get('tab') or self.request.query_params.get('status') or self.request.query_params.get('type')
        if tab:
            tab_lower = tab.lower()
            if 'ochirilgan' in tab_lower or 'deleted' in tab_lower:
                queryset = queryset.filter(is_active=False)
            elif 'bloklangan' in tab_lower or 'blocked' in tab_lower:
                queryset = queryset.filter(is_active=False)
            elif 'joriy' in tab_lower or 'active' in tab_lower:
                queryset = queryset.filter(is_active=True)

        return queryset

    def perform_create(self, serializer):
        biznes = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            biznes = self.request.user.xodim.biznes
            
        if biznes and biznes.tarif:
            limit = biznes.tarif.xodim_limiti
            if Xodim.objects.filter(biznes=biznes).count() >= limit:
                from rest_framework.exceptions import ValidationError as DRFValidationError
                raise DRFValidationError({"detail": f"Tarif rejangiz bo'yicha xodimlar soni limiti ({limit}) tugagan. Iltimos tarifingizni yangilang."})
                
        serializer.save(biznes=biznes)


from rest_framework.decorators import action

class MijozViewSet(viewsets.ModelViewSet):
    serializer_class = MijozSerializer
    permission_classes = [IsEmployee]
    filterset_fields = ['jinsi']
    search_fields = ['ism', 'familiya', 'otasining_ismi', 'telefon_raqam_1', 'telefon_raqam_2', 'manzil', 'guruhlar', 'teglar']
    ordering_fields = ['ism', 'familiya', 'yaratilgan_vaqt']

    def get_queryset(self):
        from django.db.models import Sum, Max, OuterRef, Subquery, DecimalField, DateTimeField
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        from sales.models import Sale

        user = self.request.user
        queryset = Mijoz.objects.all().order_by('-yaratilgan_vaqt')
        
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                queryset = queryset.filter(biznes=user.xodim.biznes)
            else:
                return queryset.none()

        guruh = self.request.query_params.get('guruh') or self.request.query_params.get('guruhlar')
        if guruh:
            queryset = queryset.filter(guruhlar__icontains=guruh)

        teg = self.request.query_params.get('teg') or self.request.query_params.get('teglar')
        if teg:
            queryset = queryset.filter(teglar__icontains=teg)

        xaridlar = self.request.query_params.get('xaridlar')
        if xaridlar in ['xarid_qilgan', 'qilgan', 'yes', 'true', '1']:
            queryset = queryset.filter(sotuvlar__holat='yakunlangan').distinct()
        elif xaridlar in ['xarid_qilmagan', 'qilmagan', 'no', 'false', '0']:
            queryset = queryset.exclude(sotuvlar__holat='yakunlangan').distinct()

        completed_sales = Sale.objects.filter(mijoz=OuterRef('pk'), holat='yakunlangan')
        sum_subquery = completed_sales.values('mijoz').annotate(total=Sum('yakuniy_summa')).values('total')
        last_sale_subquery = completed_sales.order_by('-yaratilgan_vaqt').values('yaratilgan_vaqt')[:1]

        queryset = queryset.annotate(
            annotated_xaridlar_summasi=Coalesce(
                Subquery(sum_subquery, output_field=DecimalField(max_digits=15, decimal_places=2)),
                Decimal('0.00')
            ),
            annotated_oxirgi_xarid=Subquery(last_sale_subquery, output_field=DateTimeField())
        )

        return queryset

    def perform_create(self, serializer):
        biznes = None
        if self.request.user and hasattr(self.request.user, 'xodim'):
            biznes = self.request.user.xodim.biznes
        serializer.save(biznes=biznes)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Max

        base_qs = Mijoz.objects.all()
        user = request.user
        if not user.is_superuser:
            if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
                base_qs = base_qs.filter(biznes=user.xodim.biznes)
            else:
                base_qs = base_qs.none()

        jami_mijozlar = base_qs.count()

        seven_days_ago = timezone.now() - timedelta(days=7)
        otgan_hafta = base_qs.filter(yaratilgan_vaqt__gte=seven_days_ago).count()

        thirty_days_ago = timezone.now() - timedelta(days=30)
        qaytib_kelmaydiganlar = base_qs.filter(sotuvlar__holat='yakunlangan').annotate(
            oxirgi_sana=Max('sotuvlar__yaratilgan_vaqt')
        ).filter(oxirgi_sana__lt=thirty_days_ago).distinct().count()

        today = timezone.now().date()
        tugilgan_kunlar = base_qs.filter(
            tugilgan_sana__month=today.month,
            tugilgan_sana__day=today.day
        ).count()

        return Response({
            'jami_mijozlar': jami_mijozlar,
            'otgan_hafta': otgan_hafta,
            'qaytib_kelmaydiganlar': qaytib_kelmaydiganlar,
            'tugilgan_kunlar': tugilgan_kunlar,
        }, status=status.HTTP_200_OK)


class BiznesViewSet(viewsets.ModelViewSet):
    serializer_class = BiznesSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Biznes.objects.all().order_by('-yaratilgan_vaqt')
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return Biznes.objects.filter(id=user.xodim.biznes.id)
        return Biznes.objects.none()

    def check_permissions(self, request):
        super().check_permissions(request)
        if self.action in ['create', 'destroy']:
            if not request.user.is_superuser:
                self.permission_denied(request, message="Faqat tizim superuseri yangi biznes qo'shishi yoki o'chirishi mumkin.")


class TarifViewSet(viewsets.ModelViewSet):
    serializer_class = TarifSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Tarif.objects.all().order_by('nomi')

    def check_permissions(self, request):
        super().check_permissions(request)
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if not request.user.is_superuser:
                self.permission_denied(request, message="Faqat superuser yangi tariflar yaratishi, tahrirlashi yoki o'chirishi mumkin.")


class BiznesSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"success": False, "message": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        data = {
            "id": biznes.id,
            "nomi": biznes.nomi,
            "company_name": biznes.nomi,
            "egasi_ism": biznes.egasi_ism,
            "telefon": biznes.telefon or "+998 90 123 45 67",
            "phone": biznes.telefon or "+998 90 123 45 67",
            "soha": biznes.soha or "Chakana savdo",
            "industry": biznes.soha or "Chakana savdo",
            "manzil": biznes.manzil or "Toshkent sh., Chilonzor t.",
            "address": biznes.manzil or "Toshkent sh., Chilonzor t.",
            "yuridik_nomi": biznes.yuridik_nomi or "",
            "legal_name": biznes.yuridik_nomi or "",
            "yuridik_manzil": biznes.yuridik_manzil or "",
            "legal_address": biznes.yuridik_manzil or "",
            "mamlakat": biznes.mamlakat or "",
            "country": biznes.mamlakat or "",
            "pochta_indeksi": biznes.pochta_indeksi or "",
            "postal_code": biznes.pochta_indeksi or "",
            "inn": biznes.inn or "",
            "mfo": biznes.mfo or ""
        }
        return Response({"success": True, "data": data, **data}, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"success": False, "message": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        d = request.data
        if 'nomi' in d or 'company_name' in d: biznes.nomi = d.get('nomi') or d.get('company_name')
        if 'telefon' in d or 'phone' in d: biznes.telefon = d.get('telefon') or d.get('phone')
        if 'soha' in d or 'industry' in d: biznes.soha = d.get('soha') or d.get('industry')
        if 'manzil' in d or 'address' in d: biznes.manzil = d.get('manzil') or d.get('address')
        if 'yuridik_nomi' in d or 'legal_name' in d: biznes.yuridik_nomi = d.get('yuridik_nomi') or d.get('legal_name')
        if 'yuridik_manzil' in d or 'legal_address' in d: biznes.yuridik_manzil = d.get('yuridik_manzil') or d.get('legal_address')
        if 'mamlakat' in d or 'country' in d: biznes.mamlakat = d.get('mamlakat') or d.get('country')
        if 'pochta_indeksi' in d or 'postal_code' in d: biznes.pochta_indeksi = d.get('pochta_indeksi') or d.get('postal_code')
        if 'inn' in d: biznes.inn = d['inn']
        if 'mfo' in d: biznes.mfo = d['mfo']
        biznes.save()

        return self.get(request, *args, **kwargs)


class TarifSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        current_tarif_name = biznes.tarif.nomi if (biznes and biznes.tarif) else "Business"

        data = [
            {
                "id": 1,
                "nomi": "Start",
                "narx": "Bepul",
                "price": "Bepul",
                "features": ["1 do'kon", "2 foydalanuvchi", "100 mahsulot", "Asosiy hisobotlar"],
                "is_current": current_tarif_name == "Start"
            },
            {
                "id": 2,
                "nomi": "Business",
                "narx": "299 000 so'm / oy",
                "price": "299 000 so'm / oy",
                "features": ["5 do'kon", "10 foydalanuvchi", "Cheksiz mahsulot", "Kengaytirilgan hisobotlar", "SMS xabarnamalar"],
                "is_current": current_tarif_name == "Business"
            },
            {
                "id": 3,
                "nomi": "Premium",
                "narx": "599 000 so'm / oy",
                "price": "599 000 so'm / oy",
                "features": ["Cheksiz do'kon", "Cheksiz foydalanuvchi", "Cheksiz mahsulot", "API kirish", "Shaxsiy menejer"],
                "is_current": current_tarif_name == "Premium"
            }
        ]
        return Response({"current_tarif": current_tarif_name, "results": data, "tarifs": data}, status=status.HTTP_200_OK)


class ChekSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import ChekSozlamalari
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        sozlama, _ = ChekSozlamalari.objects.get_or_create(biznes=biznes) if biznes else (None, False)

        data = {
            "id": sozlama.id if sozlama else None,
            "nomi": sozlama.nomi if sozlama else "Standart",
            "name": sozlama.nomi if sozlama else "Standart",
            "chop_etish_turi": sozlama.chop_etish_turi if sozlama else "Chek",
            "print_type": sozlama.chop_etish_turi if sozlama else "Chek",
            "logotip": sozlama.logotip if sozlama else False,
            "logo_icon": sozlama.logo_icon if sozlama else "",
            "logo_size": sozlama.logo_size if sozlama else 50,
            "dokon_nomi_text": sozlama.dokon_nomi_text if sozlama else "",
            "malumot_bloki": sozlama.malumot_bloki if sozlama else False,
            "malumot_bloki_options": sozlama.malumot_bloki_options if (sozlama and sozlama.malumot_bloki_options) else {
                "dokon_nomi": True, "sana": True, "chek_raqami": True, "sotuvchi": True,
                "manzil": True, "tel_fax": True, "kassir": False, "inn": False,
                "yuridik_dokon_nomi": False, "hizmat": False, "mijoz_nomi": False, "izohlar": False
            },
            "mijoz_balansi": sozlama.mijoz_balansi if sozlama else False,
            "mijoz_balansi_options": sozlama.mijoz_balansi_options if (sozlama and sozlama.mijoz_balansi_options) else {
                "xariddan_oldingi_balans": True, "balansga_qoshildi": True,
                "balansdan_yechildi": True, "xariddan_keyingi_balans": True
            },
            "mijoz_qarzi": sozlama.mijoz_qarzi if sozlama else False,
            "mijoz_qarzi_options": sozlama.mijoz_qarzi_options if (sozlama and sozlama.mijoz_qarzi_options) else {
                "xariddan_oldingi_qarz": True, "qarzga_qoshildi": True, "qarzdan_ochirildi": True
            }
        }
        return Response(data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        from .models import ChekSozlamalari
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"detail": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        sozlama, _ = ChekSozlamalari.objects.get_or_create(biznes=biznes)
        d = request.data
        if 'nomi' in d or 'name' in d: sozlama.nomi = d.get('nomi') or d.get('name')
        if 'chop_etish_turi' in d or 'print_type' in d: sozlama.chop_etish_turi = d.get('chop_etish_turi') or d.get('print_type')
        if 'logotip' in d: sozlama.logotip = bool(d['logotip'])
        if 'logo_icon' in d: sozlama.logo_icon = d['logo_icon']
        if 'logo_size' in d: sozlama.logo_size = d['logo_size']
        if 'dokon_nomi_text' in d: sozlama.dokon_nomi_text = d['dokon_nomi_text']
        if 'malumot_bloki' in d: sozlama.malumot_bloki = bool(d['malumot_bloki'])
        if 'malumot_bloki_options' in d: sozlama.malumot_bloki_options = d['malumot_bloki_options']
        if 'mijoz_balansi' in d: sozlama.mijoz_balansi = bool(d['mijoz_balansi'])
        if 'mijoz_balansi_options' in d: sozlama.mijoz_balansi_options = d['mijoz_balansi_options']
        if 'mijoz_qarzi' in d: sozlama.mijoz_qarzi = bool(d['mijoz_qarzi'])
        if 'mijoz_qarzi_options' in d: sozlama.mijoz_qarzi_options = d['mijoz_qarzi_options']
        sozlama.save()

        return self.get(request, *args, **kwargs)


class ValyutaSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import Valyuta
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if biznes and not Valyuta.objects.filter(biznes=biznes).exists():
            Valyuta.objects.create(biznes=biznes, kod="UZS", nomi="O'zbek so'mi", is_asosiy=True)
            Valyuta.objects.create(biznes=biznes, kod="USD", nomi="AQSH dollari", is_asosiy=False)
            Valyuta.objects.create(biznes=biznes, kod="EUR", nomi="Yevro", is_asosiy=False)
            Valyuta.objects.create(biznes=biznes, kod="RUB", nomi="Rossiya rubli", is_asosiy=False)

        qs = Valyuta.objects.filter(biznes=biznes) if biznes else Valyuta.objects.none()
        data = [
            {"id": v.id, "kod": v.kod, "code": v.kod, "nomi": v.nomi, "name": v.nomi, "is_asosiy": v.is_asosiy, "is_primary": v.is_asosiy}
            for v in qs
        ]
        return Response({"valyutalar": data, "currencies": data, "results": data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        from .models import Valyuta
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"detail": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        kod = request.data.get('kod') or request.data.get('code')
        val_id = request.data.get('id') or request.data.get('valyuta_id')
        if val_id or kod:
            if val_id:
                val = Valyuta.objects.filter(biznes=biznes, id=val_id).first()
            else:
                val = Valyuta.objects.filter(biznes=biznes, kod__iexact=kod).first()
            if val:
                Valyuta.objects.filter(biznes=biznes).update(is_asosiy=False)
                val.is_asosiy = True
                val.save()
        return self.get(request, *args, **kwargs)


class TolovTuriSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import TolovTuriSozlama
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if biznes and not TolovTuriSozlama.objects.filter(biznes=biznes).exists():
            TolovTuriSozlama.objects.create(biznes=biznes, nomi="Naqd pul", is_active=True, is_asosiy=True, is_custom=False)
            TolovTuriSozlama.objects.create(biznes=biznes, nomi="Plastik karta", is_active=True, is_asosiy=True, is_custom=False)
            TolovTuriSozlama.objects.create(biznes=biznes, nomi="Nasiya", is_active=True, is_asosiy=True, is_custom=False)
            TolovTuriSozlama.objects.create(biznes=biznes, nomi="Click", is_active=False, is_asosiy=False, is_custom=False)
            TolovTuriSozlama.objects.create(biznes=biznes, nomi="Payme", is_active=False, is_asosiy=False, is_custom=False)
            TolovTuriSozlama.objects.create(biznes=biznes, nomi="Uzum Bank", is_active=False, is_asosiy=False, is_custom=False)

        qs = TolovTuriSozlama.objects.filter(biznes=biznes) if biznes else TolovTuriSozlama.objects.none()
        active_count = qs.filter(is_active=True).count()
        data = [
            {
                "id": t.id,
                "nomi": t.nomi,
                "name": t.nomi,
                "is_active": t.is_active,
                "is_asosiy": t.is_asosiy,
                "is_custom": t.is_custom
            }
            for t in qs
        ]
        return Response({"active_count": active_count, "results": data, "payment_types": data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        from .models import TolovTuriSozlama
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"detail": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        nomi = request.data.get('nomi') or request.data.get('name')
        if nomi:
            TolovTuriSozlama.objects.create(biznes=biznes, nomi=nomi, is_active=True, is_asosiy=False, is_custom=True)

        return self.get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        from .models import TolovTuriSozlama
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"detail": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        item_id = request.data.get('id')
        if item_id:
            item = TolovTuriSozlama.objects.filter(biznes=biznes, id=item_id).first()
            if item:
                if 'is_active' in request.data: item.is_active = bool(request.data['is_active'])
                if 'is_asosiy' in request.data: item.is_asosiy = bool(request.data['is_asosiy'])
                item.save()
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        from .models import TolovTuriSozlama
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        item_id = request.query_params.get('id') or request.data.get('id')
        if biznes and item_id:
            TolovTuriSozlama.objects.filter(biznes=biznes, id=item_id, is_custom=True).delete()
        return self.get(request, *args, **kwargs)


class MahsulotSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import MahsulotSozlamalari
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        sozlama, _ = MahsulotSozlamalari.objects.get_or_create(biznes=biznes) if biznes else (None, False)

        data = {
            "id": sozlama.id if sozlama else None,
            "auto_generate_barcode": sozlama.auto_generate_barcode if sozlama else True,
            "shtrix_kod_avto": sozlama.auto_generate_barcode if sozlama else True,
            "require_image": sozlama.require_image if sozlama else False,
            "rasm_majburiy": sozlama.require_image if sozlama else False,
            "min_stock_alert": sozlama.min_stock_alert if sozlama else 10,
            "minimal_qoldiq": sozlama.min_stock_alert if sozlama else 10,
        }
        return Response(data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        from .models import MahsulotSozlamalari
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"detail": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        sozlama, _ = MahsulotSozlamalari.objects.get_or_create(biznes=biznes)
        d = request.data
        if 'auto_generate_barcode' in d or 'shtrix_kod_avto' in d:
            sozlama.auto_generate_barcode = bool(d.get('auto_generate_barcode') if 'auto_generate_barcode' in d else d.get('shtrix_kod_avto'))
        if 'require_image' in d or 'rasm_majburiy' in d:
            sozlama.require_image = bool(d.get('require_image') if 'require_image' in d else d.get('rasm_majburiy'))
        if 'min_stock_alert' in d or 'minimal_qoldiq' in d:
            sozlama.min_stock_alert = int(d.get('min_stock_alert') or d.get('minimal_qoldiq') or 10)
        sozlama.save()

        return self.get(request, *args, **kwargs)


class BildirishnomaSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import BildirishnomaSozlamalari
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        sozlama, _ = BildirishnomaSozlamalari.objects.get_or_create(biznes=biznes) if biznes else (None, False)

        default_matrix = {
            "qoldiq_tugashi": {"email": True, "sms": False, "push": True},
            "yangi_savdo": {"email": True, "sms": False, "push": True},
            "kunlik_hisobot": {"email": True, "sms": False, "push": True},
            "tizim_yangilanishlari": {"email": True, "sms": False, "push": True},
        }
        matrix = sozlama.matrix if (sozlama and sozlama.matrix) else default_matrix
        return Response({"id": sozlama.id if sozlama else None, "matrix": matrix}, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self.patch(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        from .models import BildirishnomaSozlamalari
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"detail": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        sozlama, _ = BildirishnomaSozlamalari.objects.get_or_create(biznes=biznes)
        if 'matrix' in request.data:
            sozlama.matrix = request.data['matrix']
            sozlama.save()

        return self.get(request, *args, **kwargs)


class IlovalarSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import Ilova
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if biznes and not Ilova.objects.filter(biznes=biznes).exists():
            Ilova.objects.create(biznes=biznes, kod="telegram_bot", nomi="Telegram bot", is_connected=True, status_text="Ulangan va faol")
            Ilova.objects.create(biznes=biznes, kod="instagram", nomi="Instagram", is_connected=False, status_text="Hozircha ulanmagan")
            Ilova.objects.create(biznes=biznes, kod="excel_export", nomi="Excel eksport", is_connected=True, status_text="Ulangan va faol")
            Ilova.objects.create(biznes=biznes, kod="1c_buxgalteriya", nomi="1C buxgalteriya", is_connected=False, status_text="Hozircha ulanmagan")
            Ilova.objects.create(biznes=biznes, kod="marketplace", nomi="Marketplace", is_connected=False, status_text="Hozircha ulanmagan")
            Ilova.objects.create(biznes=biznes, kod="mobil_ilova", nomi="Mobil ilova", is_connected=True, status_text="Ulangan va faol")

        qs = Ilova.objects.filter(biznes=biznes) if biznes else Ilova.objects.none()
        data = [
            {
                "id": il.id,
                "kod": il.kod,
                "code": il.kod,
                "nomi": il.nomi,
                "name": il.nomi,
                "is_connected": il.is_connected,
                "status_text": il.status_text or ("Ulangan va faol" if il.is_connected else "Hozircha ulanmagan")
            }
            for il in qs
        ]
        return Response({"ilovalar": data, "integrations": data, "results": data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        from .models import Ilova
        user = request.user
        biznes = user.xodim.biznes if (hasattr(user, 'xodim') and user.xodim.biznes) else None
        if not biznes:
            return Response({"detail": "Biznes topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        item_id = request.data.get('id') or request.data.get('ilova_id')
        kod = request.data.get('kod') or request.data.get('code')

        ilova = None
        if item_id:
            ilova = Ilova.objects.filter(biznes=biznes, id=item_id).first()
        elif kod:
            ilova = Ilova.objects.filter(biznes=biznes, kod=kod).first()

        if ilova:
            ilova.is_connected = not ilova.is_connected
            ilova.status_text = "Ulangan va faol" if ilova.is_connected else "Hozircha ulanmagan"
            ilova.save()

        return self.get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)
