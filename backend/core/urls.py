"""URL routing for the core app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"auth", views.AuthViewSet, basename="auth")
router.register(r"games", views.GameSnapshotViewSet, basename="games")
router.register(r"swipes", views.SwipeActionViewSet, basename="swipes")
router.register(r"watchlist", views.WatchlistEntryViewSet, basename="watchlist")
router.register(r"reports", views.ReportViewSet, basename="reports")
router.register(r"momentum", views.WishlistMomentumViewSet, basename="momentum")
router.register(r"health", views.HealthViewSet, basename="health")

urlpatterns = [
    path("", include(router.urls)),
]
