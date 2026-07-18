from rest_framework import viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from products.models import Dokon
from products.serializers import DokonSerializer
from user.permissions import IsAdminOrOmborchiOrReadOnly

class DokonViewSet(viewsets.ModelViewSet):
    serializer_class = DokonSerializer
    permission_classes = [IsAdminOrOmborchiOrReadOnly]
    search_fields = ['nomi']

    def get_queryset(self):
        user = self.request.user
        queryset = Dokon.objects.all().order_by('nomi')
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
            limit = biznes.tarif.dokon_limiti
            if Dokon.objects.filter(biznes=biznes).count() >= limit:
                raise DRFValidationError({"detail": f"Tarif rejangiz bo'yicha do'konlar soni limiti ({limit}) tugagan. Iltimos tarifingizni yangilang."})
                
        serializer.save(biznes=biznes)
