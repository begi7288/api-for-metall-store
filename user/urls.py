from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import XodimViewSet, MijozViewSet, LoginAPIView, LogoutAPIView, MeAPIView, ChangePasswordAPIView, RegisterAPIView, BiznesViewSet, TarifViewSet

router = DefaultRouter()
router.register('biznes', BiznesViewSet, basename='biznes')
router.register('tarif', TarifViewSet, basename='tarif')
router.register('xodimlar', XodimViewSet, basename='xodim')
router.register('mijozlar', MijozViewSet, basename='mijoz')

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('me/', MeAPIView.as_view(), name='me'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='change-password'),
    path('', include(router.urls)),
]