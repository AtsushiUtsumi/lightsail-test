from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PokerTableViewSet

router = DefaultRouter()
router.register(r'tables', PokerTableViewSet, basename='poker-table')

urlpatterns = [
    path('', include(router.urls)),
]
