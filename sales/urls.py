from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, XarajatKategoriyasiViewSet, XarajatViewSet

router = DefaultRouter()
router.register(r'sotuvlar', SaleViewSet, basename='sotuvlar')
router.register(r'xarajatlar-kategoriyalari', XarajatKategoriyasiViewSet, basename='xarajat-kategoriyalari')
router.register(r'xarajatlar', XarajatViewSet, basename='xarajatlar')

urlpatterns = [
    path('dashboard/', SaleViewSet.as_view({'get': 'dashboard'}), name='sales-dashboard'),
    path('panel/', SaleViewSet.as_view({'get': 'dashboard'}), name='sales-panel'),
    path('analytics/', SaleViewSet.as_view({'get': 'dashboard'}), name='sales-analytics'),
    path('top-products/', SaleViewSet.as_view({'get': 'top_products'}), name='sales-top-products'),
    path('recent-activities/', SaleViewSet.as_view({'get': 'recent_activities'}), name='sales-recent-activities'),
    path('cashflow/', SaleViewSet.as_view({'get': 'cashflow'}), name='sales-cashflow'),
    path('pul-oqimi/', SaleViewSet.as_view({'get': 'cashflow'}), name='sales-pul-oqimi'),
    path('monthly/', SaleViewSet.as_view({'get': 'monthly'}), name='sales-monthly'),
    path('oylik/', SaleViewSet.as_view({'get': 'monthly'}), name='sales-oylik'),
    path('products-analytics/', SaleViewSet.as_view({'get': 'products_analytics'}), name='sales-products-analytics'),
    path('debts-analytics/', SaleViewSet.as_view({'get': 'debts_analytics'}), name='sales-debts-analytics'),
    path('abc-xyz/', SaleViewSet.as_view({'get': 'abc_xyz'}), name='sales-abc-xyz'),
    path('foizlar/', SaleViewSet.as_view({'get': 'abc_xyz'}), name='sales-foizlar'),
    path('percentages/', SaleViewSet.as_view({'get': 'abc_xyz'}), name='sales-percentages'),

    # Expense alias routes
    path('expenses/categories/', XarajatKategoriyasiViewSet.as_view({'get': 'list', 'post': 'create'}), name='expense-categories'),
    path('expenses/', XarajatViewSet.as_view({'get': 'list', 'post': 'create'}), name='expenses-list'),
    path('xarajatlar/kategoriyalar/', XarajatKategoriyasiViewSet.as_view({'get': 'list', 'post': 'create'}), name='xarajatlar-kategoriyalar'),

    path('', include(router.urls)),
]
