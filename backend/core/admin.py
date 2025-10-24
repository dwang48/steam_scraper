from django.contrib import admin

from . import models


@admin.register(models.Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("steam_appid", "name", "latest_detection_stage", "latest_release_date", "updated_at")
    search_fields = ("steam_appid", "name")
    list_filter = ("latest_detection_stage",)
    ordering = ("-updated_at",)


@admin.register(models.DiscoveryBatch)
class DiscoveryBatchAdmin(admin.ModelAdmin):
    list_display = ("source_name", "ingested_for_date", "run_started_at", "run_completed_at")
    list_filter = ("source_name", "ingested_for_date")
    search_fields = ("source_name", "source_file")
    ordering = ("-ingested_for_date", "-run_started_at")


@admin.register(models.GameSnapshot)
class GameSnapshotAdmin(admin.ModelAdmin):
    list_display = ("game", "ingested_for_date", "followers", "wishlists_est", "detection_stage")
    list_filter = ("ingested_for_date", "detection_stage", "batch__source_name")
    search_fields = ("game__name", "game__steam_appid")
    ordering = ("-ingested_for_date", "-followers")


@admin.register(models.WatchlistEntry)
class WatchlistEntryAdmin(admin.ModelAdmin):
    list_display = ("game", "current_status", "check_count", "last_checked")
    list_filter = ("current_status",)
    search_fields = ("game__name", "game__steam_appid")


@admin.register(models.SwipeAction)
class SwipeActionAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("game__name", "game__steam_appid", "user__username")
    ordering = ("-created_at",)
