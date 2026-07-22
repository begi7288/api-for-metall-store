"""
URL configuration for temirdokon_v1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from user.extra_views import CategoriesViewSet, UnitsViewSet, RolesViewSet, ArchiveListAPIView
from products.views.taminotchi import TaminotchiViewSet

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blog.urls')),
    path('users/', include('user.urls')),
    path('products/order/', include('orders.urls')),
    path('products/', include('products.urls')),
    path('sales/', include('sales.urls')),
    path('expenses/', include('sales.urls')),
    path('xarajatlar/', include('sales.urls')),
    path('credits/', include('user.credits_urls')),
    path('loyalty/', include('user.loyalty_urls')),
    path('sodiqlik/', include('user.loyalty_urls')),
    
    path('roles/', RolesViewSet.as_view({'get': 'list', 'post': 'create'}), name='roles-list'),
    path('roles/<str:pk>/', RolesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='roles-detail'),
    path('lavozimlar/', RolesViewSet.as_view({'get': 'list', 'post': 'create'}), name='lavozimlar-list'),
    path('lavozimlar/<str:pk>/', RolesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='lavozimlar-detail'),

    path('categories/', CategoriesViewSet.as_view({'get': 'list', 'post': 'create'}), name='categories-list'),
    path('categories/<int:pk>/', CategoriesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='categories-detail'),
    path('kategoriya/', CategoriesViewSet.as_view({'get': 'list', 'post': 'create'}), name='kategoriya-list'),
    path('kategoriya/<int:pk>/', CategoriesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='kategoriya-detail'),
    path('kategoriyalar/', CategoriesViewSet.as_view({'get': 'list', 'post': 'create'}), name='kategoriyalar-list'),
    path('kategoriyalar/<int:pk>/', CategoriesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='kategoriyalar-detail'),

    path('taminotchi/', TaminotchiViewSet.as_view({'get': 'list', 'post': 'create'}), name='taminotchi-list'),
    path('taminotchi/<int:pk>/', TaminotchiViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='taminotchi-detail'),
    path('taminotchilar/', TaminotchiViewSet.as_view({'get': 'list', 'post': 'create'}), name='taminotchilar-list'),
    path('taminotchilar/<int:pk>/', TaminotchiViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='taminotchilar-detail'),
    
    path('units/', UnitsViewSet.as_view({'get': 'list', 'post': 'create'}), name='units-list'),
    path('units/<int:pk>/', UnitsViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='units-detail'),
    path('olchov/', UnitsViewSet.as_view({'get': 'list', 'post': 'create'}), name='olchov-list'),
    path('olchov/<int:pk>/', UnitsViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='olchov-detail'),
    path('olchov-birliklari/', UnitsViewSet.as_view({'get': 'list', 'post': 'create'}), name='olchov-birliklari-list'),
    path('olchov-birliklari/<int:pk>/', UnitsViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='olchov-birliklari-detail'),
    
    path('archive/', ArchiveListAPIView.as_view(), name='archive-list'),
    
    # Swagger & Open API 3 Endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui-alias'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui-direct'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
