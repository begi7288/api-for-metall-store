from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MahsulotViewSet, ImportViewSet, DokonViewSet, TransferViewSet, CharacteristicViewSet, MahsulotRasmViewSet, MahsulotShtrixKodViewSet, WriteOffViewSet, XususiyatMaydoniViewSet, ToplamViewSet, YorliqShablonViewSet, TaminotchiViewSet

router = DefaultRouter()
router.register('dokon', DokonViewSet, basename='dokon')
router.register('import', ImportViewSet, basename='import')
router.register('transfer', TransferViewSet, basename='transfer')
router.register('write-off', WriteOffViewSet, basename='write-off')
router.register('characteristics', CharacteristicViewSet, basename='characteristic')
router.register('images', MahsulotRasmViewSet, basename='product-image')
router.register('barcodes', MahsulotShtrixKodViewSet, basename='product-barcode')
router.register('fields', XususiyatMaydoniViewSet, basename='fields')
router.register('toplam', ToplamViewSet, basename='toplam')
router.register('price-tag-templates', YorliqShablonViewSet, basename='price-tag-templates')
router.register('suppliers', TaminotchiViewSet, basename='suppliers')
router.register('', MahsulotViewSet, basename='mahsulot')

urlpatterns = [
    path('', include(router.urls)),
]
