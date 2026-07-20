from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from user.models import Xodim
from products.models import Mahsulot
from products.serializers import MahsulotSerializer

class RolesListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        roles_data = [{"id": r[0], "nomi": r[1]} for r in Xodim.ROL_CHOICES]
        return Response(roles_data, status=status.HTTP_200_OK)

class UnitsListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        units_data = [{"id": u[0], "nomi": u[1]} for u in Mahsulot.OLCHOV_CHOICES]
        return Response(units_data, status=status.HTTP_200_OK)

class CategoriesListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        queryset = Mahsulot.objects.all()
        if user.is_superuser:
            pass
        elif hasattr(user, 'xodim') and user.xodim.biznes:
            queryset = queryset.filter(biznes=user.xodim.biznes)
        else:
            queryset = queryset.none()
            
        categories = queryset.exclude(toifa__isnull=True).exclude(toifa="").values_list('toifa', flat=True).distinct().order_by('toifa')
        categories_data = [{"nomi": cat} for cat in categories]
        return Response(categories_data, status=status.HTTP_200_OK)

class ArchiveListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        queryset = Mahsulot.objects.filter(is_active=False).prefetch_related('qoldiqlar', 'shtrix_kodlar').order_by('-yangilangan_vaqt')
        if user.is_superuser:
            pass
        elif hasattr(user, 'xodim') and user.xodim.biznes:
            queryset = queryset.filter(biznes=user.xodim.biznes)
        else:
            queryset = queryset.none()
            
        serializer = MahsulotSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
