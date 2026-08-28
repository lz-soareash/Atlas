"""Configuração de rotas raiz do Atlas."""

from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import index

urlpatterns = [
    path("admin/", admin.site.urls),
    # Frontend (HTML/CSS/JS puro servido pelo Django)
    path("", index, name="index"),
    # Autenticação JWT
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Aplicações
    path("api/accounts/", include("apps.accounts.urls")),
]
