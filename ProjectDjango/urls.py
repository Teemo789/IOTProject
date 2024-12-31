from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('DHT.urls')),  # Inclus les URLs de DHT sous le préfixe /api/
]
