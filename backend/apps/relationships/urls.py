from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import GraphView, RelationshipViewSet

router = DefaultRouter()
router.register("relationships", RelationshipViewSet, basename="relationships")

urlpatterns = [
    path("graph/", GraphView.as_view(), name="graph"),
    *router.urls,
]
