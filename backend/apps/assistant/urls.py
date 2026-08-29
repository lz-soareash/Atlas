from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChatView, MemoryViewSet, ToolProposalViewSet

router = DefaultRouter()
router.register("memories", MemoryViewSet, basename="memories")
router.register("tools/proposals", ToolProposalViewSet, basename="tool-proposals")

urlpatterns = [
    path("assistant/chat/", ChatView.as_view(), name="assistant-chat"),
    *router.urls,
]