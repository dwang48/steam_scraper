"""
Database models for the Steam selection backend.
"""

from django.conf import settings
from django.db import models


class DiscoveryBatch(models.Model):
    """Represents a single ingestion run from one of the crawler scripts."""

    source_name = models.CharField(max_length=100, help_text="crawler identifier, e.g. steam_daily")
    run_started_at = models.DateTimeField()
    run_completed_at = models.DateTimeField(null=True, blank=True)
    ingested_for_date = models.DateField(help_text="Business date the batch covers (typically UTC date).")
    source_file = models.CharField(max_length=255, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ingested_for_date", "-run_started_at"]
        indexes = [
            models.Index(fields=["ingested_for_date"]),
            models.Index(fields=["source_name", "run_started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_name} @ {self.ingested_for_date:%Y-%m-%d}"


class Game(models.Model):
    """Canonical Steam game record."""

    steam_appid = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    steam_url = models.URLField(max_length=500, blank=True)
    website = models.URLField(max_length=500, blank=True)
    developers = models.CharField(max_length=500, blank=True)
    publishers = models.CharField(max_length=500, blank=True)
    categories = models.CharField(max_length=500, blank=True)
    genres = models.CharField(max_length=500, blank=True)
    tags = models.CharField(max_length=500, blank=True)
    latest_release_date = models.CharField(max_length=120, blank=True)
    latest_detection_stage = models.CharField(max_length=50, blank=True)
    latest_api_response_type = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["steam_appid"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.steam_appid})"


class GameSnapshot(models.Model):
    """
    Snapshot of a game's metrics taken from a single ingestion batch.
    Stores the data needed by the UI without mutating the canonical Game record.
    """

    game = models.ForeignKey(Game, related_name="snapshots", on_delete=models.CASCADE)
    batch = models.ForeignKey(DiscoveryBatch, related_name="snapshots", on_delete=models.PROTECT)
    detection_stage = models.CharField(max_length=50, blank=True)
    api_response_type = models.CharField(max_length=50, blank=True)
    potential_duplicate = models.BooleanField(default=False)
    discovery_date = models.DateField(null=True, blank=True)
    ingested_for_date = models.DateField()
    release_date_raw = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    supported_languages = models.CharField(max_length=500, blank=True)
    followers = models.IntegerField(null=True, blank=True)
    wishlists_est = models.IntegerField(null=True, blank=True)
    wishlist_rank = models.IntegerField(null=True, blank=True)
    source_categories = models.CharField(max_length=500, blank=True)
    source_genres = models.CharField(max_length=500, blank=True)
    source_tags = models.CharField(max_length=500, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ingested_for_date", "-followers"]
        unique_together = ("game", "batch")
        indexes = [
            models.Index(fields=["ingested_for_date"]),
            models.Index(fields=["followers"]),
            models.Index(fields=["wishlists_est"]),
        ]

    def __str__(self) -> str:
        return f"{self.game} snapshot @ {self.ingested_for_date:%Y-%m-%d}"


class WatchlistEntry(models.Model):
    """Stores the early-stage watchlist state migrated from the legacy JSON file."""

    game = models.OneToOneField(Game, related_name="watchlist_entry", on_delete=models.CASCADE)
    first_detected = models.DateField(null=True, blank=True)
    last_checked = models.DateField(null=True, blank=True)
    status_history = models.JSONField(default=list, blank=True)
    current_status = models.CharField(max_length=50, blank=True)
    check_count = models.PositiveIntegerField(default=0)
    latest_name = models.CharField(max_length=255, blank=True)
    latest_type = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["game__name"]

    def __str__(self) -> str:
        return f"Watchlist → {self.game}"


class SwipeAction(models.Model):
    """Captures user interactions from the swipe UI."""

    ACTION_LIKE = "like"
    ACTION_SKIP = "skip"
    ACTION_WATCHLIST = "watchlist"
    ACTION_CHOICES = [
        (ACTION_LIKE, "Like"),
        (ACTION_SKIP, "Skip"),
        (ACTION_WATCHLIST, "Add to Watchlist"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="swipe_actions")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="swipe_actions")
    batch = models.ForeignKey(
        DiscoveryBatch,
        on_delete=models.SET_NULL,
        related_name="swipe_actions",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["game", "created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.game} ({self.action})"


class WishlistMomentum(models.Model):
    """Stores wishlist/follower growth momentum metrics."""

    WINDOW_3D = "3d"
    WINDOW_7D = "7d"
    WINDOW_CHOICES = [
        (WINDOW_3D, "3 days"),
        (WINDOW_7D, "7 days"),
    ]

    game = models.ForeignKey(Game, related_name="momentum_entries", on_delete=models.CASCADE)
    window = models.CharField(max_length=8, choices=WINDOW_CHOICES)
    calc_date = models.DateField(help_text="Business date the metric was calculated for.")
    baseline_value = models.IntegerField(help_text="Baseline wishlist/follower value at window start.")
    latest_followers = models.IntegerField(null=True, blank=True)
    latest_wishlists_est = models.IntegerField(null=True, blank=True)
    delta_followers = models.IntegerField(help_text="Net follower change within the window.")
    delta_per_day = models.FloatField(help_text="Average follower change per day.")
    delta_rate = models.FloatField(null=True, blank=True, help_text="Relative change against baseline.")
    percentile = models.FloatField(null=True, blank=True, help_text="Percentile ranking within the peer group.")
    rank = models.PositiveIntegerField(help_text="Rank within the window for calc_date (1 = fastest growth).")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-calc_date", "window", "rank"]
        unique_together = ("game", "window", "calc_date")
        indexes = [
            models.Index(fields=["calc_date", "window"]),
            models.Index(fields=["window", "rank"]),
        ]

    def __str__(self) -> str:
        return f"Momentum {self.game} [{self.window}] @ {self.calc_date:%Y-%m-%d}"
