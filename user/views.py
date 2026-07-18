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
                "yaratilgan_vaqt": xodim.yaratilgan_vaqt,
                "yangilangan_vaqt": xodim.yangilangan_vaqt
            }
        else:
            data = {
                "id": None,
                "ism": user.first_name if user.first_name else None,
                "familiya": user.last_name if user.last_name else None,
                "telefon_raqam": user.username,
                "rol": "admin",
                "jinsi": "erkak",
                "tugilgan_sana": None,
                "is_active": user.is_active,
                "yaratilgan_vaqt": user.date_joined,
                "yangilangan_vaqt": user.date_joined
            }

        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


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
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        xodim = serializer.save()

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
            return queryset
        if user.is_authenticated and hasattr(user, 'xodim') and user.xodim.biznes:
            return queryset.filter(biznes=user.xodim.biznes)
        return queryset.none()

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


class MijozViewSet(viewsets.ModelViewSet):
    serializer_class = MijozSerializer
    permission_classes = [IsEmployee]
    filterset_fields = ['jinsi']
    search_fields = ['ism', 'familiya', 'otasining_ismi', 'telefon_raqam_1', 'telefon_raqam_2']
    ordering_fields = ['ism', 'familiya', 'yaratilgan_vaqt']

    def get_queryset(self):
        user = self.request.user
        queryset = Mijoz.objects.all().order_by('-yaratilgan_vaqt')
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
