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
    # Fase 2 — Knowledge Core
    path("api/", include("apps.knowledge.urls")),
    path("api/", include("apps.ideas.urls")),
    path("api/", include("apps.projects.urls")),
    path("api/", include("apps.questions.urls")),
    path("api/", include("apps.decisions.urls")),
    path("api/", include("apps.experiences.urls")),
    # Dashboard (visão agregada)
    path("api/", include("apps.dashboard.urls")),
    # Fase 3 — Relacionamentos + Grafo
    path("api/", include("apps.relationships.urls")),
]
