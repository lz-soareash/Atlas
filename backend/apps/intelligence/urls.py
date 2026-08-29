from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import InboxViewSet, IntelligenceView

router = DefaultRouter()
router.register("inbox", InboxViewSet, basename="inbox")

urlpatterns = [
    path("intelligence/duplicates/", IntelligenceView.as_view(), name="intelligence-duplicates"),
    path("intelligence/relationship-suggestions/", IntelligenceView.as_view(), name="intelligence-rel-suggestions"),
    path("intelligence/gaps/", IntelligenceView.as_view(), name="intelligence-gaps"),
    *router.urls,
]
