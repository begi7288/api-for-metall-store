from django.urls import path
from .loyalty_views import LoyaltyViewSet

urlpatterns = [
    path('tiers/', LoyaltyViewSet.as_view({'get': 'list', 'post': 'create'}), name='loyalty-tiers-list'),
    path('tiers/<int:pk>/', LoyaltyViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='loyalty-tiers-detail'),
    path('', LoyaltyViewSet.as_view({'get': 'list', 'post': 'create'}), name='loyalty-root'),
]
