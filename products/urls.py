from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MahsulotViewSet, ImportViewSet, DokonViewSet, TransferViewSet, CharacteristicViewSet, MahsulotRasmViewSet, MahsulotShtrixKodViewSet, WriteOffViewSet, XususiyatMaydoniViewSet, ToplamViewSet, YorliqShablonViewSet, TaminotchiViewSet
from user.extra_views import UnitsViewSet, CategoriesViewSet, ArchiveListAPIView

router = DefaultRouter()
router.register('dokon', DokonViewSet, basename='dokon')
router.register('import', ImportViewSet, basename='import')
router.register('kirim', ImportViewSet, basename='kirim')
router.register('kirimlar', ImportViewSet, basename='kirimlar')
router.register('transfer', TransferViewSet, basename='transfer')
router.register('write-off', WriteOffViewSet, basename='write-off')
router.register('hisobdan-chiqarish', WriteOffViewSet, basename='hisobdan-chiqarish')
router.register('toplam', ToplamViewSet, basename='toplam')
router.register('inventarizatsiya', ToplamViewSet, basename='inventarizatsiya')
router.register('characteristics', CharacteristicViewSet, basename='characteristic')
router.register('images', MahsulotRasmViewSet, basename='product-image')
router.register('barcodes', MahsulotShtrixKodViewSet, basename='product-barcode')
router.register('fields', XususiyatMaydoniViewSet, basename='fields')
router.register('xususiyatlar', XususiyatMaydoniViewSet, basename='xususiyatlar')
router.register('attributes', XususiyatMaydoniViewSet, basename='attributes')
router.register('price-tag-templates', YorliqShablonViewSet, basename='price-tag-templates')
router.register('suppliers', TaminotchiViewSet, basename='suppliers')
router.register('olchov-birliklari', UnitsViewSet, basename='olchov-birliklari')
router.register('units', UnitsViewSet, basename='units')
router.register('toifalar', CategoriesViewSet, basename='toifalar')
router.register('categories', CategoriesViewSet, basename='categories')
router.register('', MahsulotViewSet, basename='mahsulot')

urlpatterns = [
    path('archive/', ArchiveListAPIView.as_view(), name='product-archive'),
    path('', include(router.urls)),
]
