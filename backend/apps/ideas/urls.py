from rest_framework.routers import DefaultRouter

from .views import IdeaViewSet

router = DefaultRouter()
router.register("ideas", IdeaViewSet, basename="ideas")

urlpatterns = router.urls
