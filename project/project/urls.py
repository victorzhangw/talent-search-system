from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', RedirectView.as_view(url='/', permanent=False)),  # 導回網站首頁
    path('api/', include('api.urls')),  # API 路由
    path('', include('core.urls')),   # 包含 core app 的所有路由
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
