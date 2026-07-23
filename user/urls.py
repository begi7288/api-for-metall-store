from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    XodimViewSet, MijozViewSet, LoginAPIView, LogoutAPIView, MeAPIView, ChangePasswordAPIView, RegisterAPIView,
    BiznesViewSet, TarifViewSet, BiznesSettingsAPIView, TarifSettingsAPIView, ChekSettingsAPIView,
    ValyutaSettingsAPIView, TolovTuriSettingsAPIView, MahsulotSettingsAPIView, BildirishnomaSettingsAPIView,
    IlovalarSettingsAPIView, ClearDatabaseAPIView
)
from user.extra_views import RolesViewSet, CategoriesViewSet, UnitsViewSet
from products.views.taminotchi import TaminotchiViewSet

router = DefaultRouter()
router.register('biznes', BiznesViewSet, basename='biznes')
router.register('tarif', TarifViewSet, basename='tarif')
router.register('xodimlar', XodimViewSet, basename='xodim')
router.register('employees', XodimViewSet, basename='employees')
router.register('mijozlar', MijozViewSet, basename='mijoz')
router.register('rollar', RolesViewSet, basename='rollar')
router.register('roles', RolesViewSet, basename='roles')
router.register('lavozimlar', RolesViewSet, basename='lavozimlar')
router.register('kategoriya', CategoriesViewSet, basename='kategoriya')
router.register('kategoriyalar', CategoriesViewSet, basename='kategoriyalar')
router.register('categories', CategoriesViewSet, basename='categories')
router.register('taminotchi', TaminotchiViewSet, basename='taminotchi')
router.register('taminotchilar', TaminotchiViewSet, basename='taminotchilar')
router.register('suppliers', TaminotchiViewSet, basename='suppliers')
router.register('olchov', UnitsViewSet, basename='olchov')
router.register('olchov-birliklari', UnitsViewSet, basename='olchov-birliklari')
router.register('units', UnitsViewSet, basename='units')

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('me/', MeAPIView.as_view(), name='me'),
    path('profile/', MeAPIView.as_view(), name='user-profile'),
    path('settings/profile/', MeAPIView.as_view(), name='settings-profile'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='change-password'),
    path('company/', BiznesSettingsAPIView.as_view(), name='user-company'),
    path('settings/company/', BiznesSettingsAPIView.as_view(), name='settings-company'),
    path('tarifs/', TarifSettingsAPIView.as_view(), name='user-tarifs'),
    path('settings/tarif/', TarifSettingsAPIView.as_view(), name='settings-tarif'),
    path('receipt-settings/', ChekSettingsAPIView.as_view(), name='receipt-settings'),
    path('settings/cheklar/', ChekSettingsAPIView.as_view(), name='settings-cheklar'),
    path('currencies/', ValyutaSettingsAPIView.as_view(), name='user-currencies'),
    path('valyutalar/', ValyutaSettingsAPIView.as_view(), name='user-valyutalar'),
    path('settings/valyutalar/', ValyutaSettingsAPIView.as_view(), name='settings-valyutalar'),
    path('payment-types/', TolovTuriSettingsAPIView.as_view(), name='user-payment-types'),
    path('tolov-turlari/', TolovTuriSettingsAPIView.as_view(), name='user-tolov-turlari'),
    path('settings/tolov-turlari/', TolovTuriSettingsAPIView.as_view(), name='settings-tolov-turlari'),
    path('product-settings/', MahsulotSettingsAPIView.as_view(), name='user-product-settings'),
    path('settings/mahsulotlar/', MahsulotSettingsAPIView.as_view(), name='settings-mahsulotlar'),
    path('notification-settings/', BildirishnomaSettingsAPIView.as_view(), name='user-notification-settings'),
    path('settings/bildirishnomalar/', BildirishnomaSettingsAPIView.as_view(), name='settings-bildirishnomalar'),
    path('integrations/', IlovalarSettingsAPIView.as_view(), name='user-integrations'),
    path('ilovalar/', IlovalarSettingsAPIView.as_view(), name='user-ilovalar'),
    path('settings/ilovalar/', IlovalarSettingsAPIView.as_view(), name='settings-ilovalar'),
    path('credits/', include('user.credits_urls')),
    path('loyalty/', include('user.loyalty_urls')),
    path('sodiqlik/', include('user.loyalty_urls')),
    path('clear-database/', ClearDatabaseAPIView.as_view(), name='clear-database'),
    path('', include(router.urls)),
]