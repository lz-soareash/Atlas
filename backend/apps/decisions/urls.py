from rest_framework.routers import DefaultRouter

from .views import DecisionViewSet

router = DefaultRouter()
router.register("decisions", DecisionViewSet, basename="decisions")

urlpatterns = router.urls
