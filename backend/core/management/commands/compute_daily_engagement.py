"""
Aggregate swipe activity into per-game daily engagement records.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from core import models


class Command(BaseCommand):
    help = "Compute per-game engagement (likes/skips/watchlists) for a target date."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="summary_date",
            help="Summary date (YYYY-MM-DD). Defaults to yesterday (UTC).",
        )
        parser.add_argument(
            "--lookback",
            type=int,
            default=1,
            help="Number of consecutive days to compute, counting backwards from the summary date. Defaults to 1.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculate results without writing to the database.",
        )

    def handle(self, *args, **options):
        summary_date = self._resolve_summary_date(options.get("summary_date"))
        lookback = max(1, options["lookback"])
        dry_run = options["dry_run"]

        for offset in range(lookback):
            target_date = summary_date - timedelta(days=offset)
            self.stdout.write(f"Computing engagement for {target_date.isoformat()}...")
            payload = self._build_payload_for_date(target_date)

            if not payload:
                self.stdout.write(self.style.WARNING("  No swipe actions found."))
                if not dry_run:
                    models.DailyGameEngagement.objects.filter(summary_date=target_date).delete()
                continue

            if dry_run:
                preview = ", ".join(
                    f"{item['game'].name} ({item['likes']} likes)"
                    for item in payload[:5]
                )
                self.stdout.write(self.style.SUCCESS(f"  Would persist {len(payload)} rows. Top: {preview}"))
                continue

            with transaction.atomic():
                models.DailyGameEngagement.objects.filter(summary_date=target_date).delete()
                models.DailyGameEngagement.objects.bulk_create(
                    [
                        models.DailyGameEngagement(
                            game=item["game"],
                            summary_date=target_date,
                            likes=item["likes"],
                            skips=item["skips"],
                            watchlists=item["watchlists"],
                            unique_likers=item["unique_likers"],
                            unique_skeptics=item["unique_skeptics"],
                            total_actions=item["total_actions"],
                            metadata=item["metadata"],
                        )
                        for item in payload
                    ],
                    batch_size=500,
                )
            self.stdout.write(self.style.SUCCESS(f"  Persisted {len(payload)} rows."))

    def _resolve_summary_date(self, value: str | None) -> date:
        if value:
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError(f"Invalid --date: {value}") from exc
        # Default to "yesterday" so that scheduled runs catch the last full day of activity.
        return timezone.now().date() - timedelta(days=1)

    def _build_payload_for_date(self, target_date: date) -> List[Dict[str, object]]:
        swipes = (
            models.SwipeAction.objects.select_related("game", "user")
            .filter(created_at__date=target_date)
        )
        if not swipes.exists():
            return []

        aggregates = (
            swipes.values("game_id")
            .annotate(
                likes=Count("id", filter=Q(action=models.SwipeAction.ACTION_LIKE)),
                skips=Count("id", filter=Q(action=models.SwipeAction.ACTION_SKIP)),
                watchlists=Count("id", filter=Q(action=models.SwipeAction.ACTION_WATCHLIST)),
                unique_likers=Count("user_id", filter=Q(action=models.SwipeAction.ACTION_LIKE), distinct=True),
                unique_skeptics=Count("user_id", filter=Q(action=models.SwipeAction.ACTION_SKIP), distinct=True),
                total_actions=Count("id"),
            )
            .order_by("-likes", "-total_actions")
        )

        if not aggregates:
            return []

        # Collect a small sample of user display names per game for metadata.
        display_name_map: Dict[int, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        for swipe in swipes:
            display_name = swipe.user.get_full_name() or swipe.user.get_username()
            display_name_map[swipe.game_id][swipe.action].append(display_name)

        results: List[Dict[str, object]] = []
        games = models.Game.objects.in_bulk([row["game_id"] for row in aggregates])

        for row in aggregates:
            game = games.get(row["game_id"])
            if not game:
                continue

            metadata = {
                "sample_likers": display_name_map[row["game_id"]][models.SwipeAction.ACTION_LIKE][:10],
                "sample_skip_users": display_name_map[row["game_id"]][models.SwipeAction.ACTION_SKIP][:10],
                "sample_watchlist_users": display_name_map[row["game_id"]][models.SwipeAction.ACTION_WATCHLIST][:10],
            }

            results.append(
                {
                    "game": game,
                    "likes": row["likes"],
                    "skips": row["skips"],
                    "watchlists": row["watchlists"],
                    "unique_likers": row["unique_likers"],
                    "unique_skeptics": row["unique_skeptics"],
                    "total_actions": row["total_actions"],
                    "metadata": metadata,
                }
            )

        return results
