"""Rotas do Cognitive Engine (Fase 10)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

session_router = DefaultRouter()
session_router.register("sessions", views.CognitiveSessionViewSet, basename="cognitive-session")

event_router = DefaultRouter()
event_router.register("events", views.IntegrationEventViewSet, basename="integration-event")

urlpatterns = [
    path("cognitive/", include(session_router.urls)),
    path("integration/", include(event_router.urls)),
]
