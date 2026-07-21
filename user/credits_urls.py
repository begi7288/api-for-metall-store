from django.urls import path
from .credits_views import DebtorsViewSet, PaymentsViewSet

urlpatterns = [
    path('debtors/stats/', DebtorsViewSet.as_view({'get': 'stats'}), name='credits-debtors-stats'),
    path('debtors/bulk-payment/', DebtorsViewSet.as_view({'post': 'bulk_payment'}), name='credits-debtors-bulk-payment'),
    path('debtors/send-sms/', DebtorsViewSet.as_view({'post': 'send_sms'}), name='credits-debtors-send-sms'),
    path('debtors/', DebtorsViewSet.as_view({'get': 'list', 'post': 'create'}), name='credits-debtors-list'),
    path('debtors/<int:pk>/', DebtorsViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='credits-debtors-detail'),
    
    path('payments/', PaymentsViewSet.as_view({'get': 'list', 'post': 'create'}), name='credits-payments-list'),
    path('stats/', DebtorsViewSet.as_view({'get': 'stats'}), name='credits-stats'),
    path('', DebtorsViewSet.as_view({'get': 'list', 'post': 'create'}), name='credits-root'),
]
