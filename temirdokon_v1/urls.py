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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blog.urls')),
    path('users/', include('user.urls')),
    path('products/order/', include('orders.urls')),
    path('products/', include('products.urls')),
    
    # Missing root-level endpoints with full CRUD mapping
    path('roles/', RolesViewSet.as_view({'get': 'list', 'post': 'create'}), name='roles-list'),
    path('roles/<int:pk>/', RolesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='roles-detail'),
    
    path('categories/', CategoriesViewSet.as_view({'get': 'list', 'post': 'create'}), name='categories-list'),
    path('categories/<int:pk>/', CategoriesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='categories-detail'),
    
    path('units/', UnitsViewSet.as_view({'get': 'list', 'post': 'create'}), name='units-list'),
    path('units/<int:pk>/', UnitsViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='units-detail'),
    
    path('archive/', ArchiveListAPIView.as_view(), name='archive-list'),
    
    # Swagger & Open API 3 Endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
