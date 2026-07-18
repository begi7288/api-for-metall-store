from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaminotchiViewSet, SupplierOrderViewSet, SupplierOrderReturnViewSet

router = DefaultRouter()
router.register('taminotchilar', TaminotchiViewSet, basename='taminotchi')
router.register('returns', SupplierOrderReturnViewSet, basename='supplier-order-return')
router.register('', SupplierOrderViewSet, basename='supplier-order')

urlpatterns = [
    path('', include(router.urls)),
]
