from rest_framework.routers import DefaultRouter

from .views import ExperienceViewSet

router = DefaultRouter()
router.register("experiences", ExperienceViewSet, basename="experiences")

urlpatterns = router.urls
