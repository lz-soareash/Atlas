from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatView, MemoryViewSet

router = DefaultRouter()
router.register("memories", MemoryViewSet, basename="memories")

urlpatterns = [
    path("assistant/chat/", ChatView.as_view(), name="assistant-chat"),
    *router.urls,
]