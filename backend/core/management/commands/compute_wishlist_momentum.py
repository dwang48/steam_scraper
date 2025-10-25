"""
Compute wishlist/follower growth momentum metrics.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from dateutil import parser as dateparser
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core import models


def _is_unreleased(snapshot: models.GameSnapshot, calc_date: date) -> bool:
    """Heuristic to determine if a game is unreleased."""

    # Detection stage hints
    if snapshot.detection_stage and "released" not in snapshot.detection_stage.lower():
        return True

    release_raw = (snapshot.release_date_raw or "").strip()
    if not release_raw:
        return True

    lowered = release_raw.lower()
    if any(token in lowered for token in ("tba", "coming soon", "comingsoon", "soon")):
        return True

    try:
        parsed_dt = dateparser.parse(release_raw, fuzzy=True)
    except (ValueError, TypeError, OverflowError):
        return True

    parsed_date = parsed_dt.date()
    return parsed_date > calc_date


def _primary_metric(snapshot: models.GameSnapshot) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Return (metric, followers, wishlists)."""

    followers = snapshot.followers if snapshot.followers is not None else None
    wishlists = snapshot.wishlists_est if snapshot.wishlists_est is not None else None

    if followers is not None:
        return followers, followers, wishlists
    if wishlists is not None:
        return wishlists, followers, wishlists
    return None, followers, wishlists


class Command(BaseCommand):
    help = "Compute wishlist/follower growth momentum for unreleased games."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="calc_date",
            help="Calculation date (YYYY-MM-DD). Defaults to today (UTC).",
        )
        parser.add_argument(
            "--window",
            action="append",
            choices=[models.WishlistMomentum.WINDOW_3D, models.WishlistMomentum.WINDOW_7D],
            help="Window to compute (3d/7d). Can be provided multiple times. Defaults to both.",
        )
        parser.add_argument(
            "--min-baseline",
            type=int,
            default=50,
            help="Minimum baseline follower/wishlist value required to consider a game.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculate results without persisting to the database.",
        )

    def handle(self, *args, **options):
        calc_date = self._resolve_calc_date(options.get("calc_date"))
        windows = options.get("window") or [
            models.WishlistMomentum.WINDOW_3D,
            models.WishlistMomentum.WINDOW_7D,
        ]
        min_baseline = options["min_baseline"]
        dry_run = options["dry_run"]

        self.stdout.write(f"Computing wishlist momentum for {calc_date} (windows: {', '.join(windows)})")

        for window in windows:
            window_days = 3 if window == models.WishlistMomentum.WINDOW_3D else 7
            self._compute_window(calc_date, window, window_days, min_baseline, dry_run)

    def _resolve_calc_date(self, value: str | None) -> date:
        if value:
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError(f"Invalid --date: {value}") from exc
        return timezone.now().date()

    def _compute_window(
        self,
        calc_date: date,
        window_code: str,
        window_days: int,
        min_baseline: int,
        dry_run: bool,
    ) -> None:
        window_span = max(window_days - 1, 0)
        start_date = calc_date - timedelta(days=window_span)
        snapshots = (
            models.GameSnapshot.objects.select_related("game")
            .filter(ingested_for_date__range=(start_date, calc_date))
            .order_by("game_id", "ingested_for_date")
        )

        grouped: Dict[int, List[models.GameSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            grouped[snapshot.game_id].append(snapshot)

        momentum_entries: List[models.WishlistMomentum] = []

        for game_id, data in grouped.items():
            first_snapshot = data[0]
            last_snapshot = data[-1]

            metric_start, followers_start, wishlists_start = _primary_metric(first_snapshot)
            metric_end, followers_end, wishlists_end = _primary_metric(last_snapshot)

            if metric_start is None or metric_end is None:
                continue
            if metric_start < min_baseline:
                continue
            if not _is_unreleased(last_snapshot, calc_date):
                continue

            days = max(1, (last_snapshot.ingested_for_date - first_snapshot.ingested_for_date).days)
            delta = metric_end - metric_start
            if delta <= 0:
                continue
            delta_per_day = delta / days
            delta_rate = (delta / metric_start) if metric_start else None

            entry = models.WishlistMomentum(
                game=first_snapshot.game,
                window=window_code,
                calc_date=calc_date,
                baseline_value=metric_start,
                latest_followers=last_snapshot.followers,
                latest_wishlists_est=last_snapshot.wishlists_est,
                delta_followers=delta,
                delta_per_day=delta_per_day,
                delta_rate=delta_rate,
                metadata={
                    "window_days": window_days,
                    "baseline_snapshot_date": first_snapshot.ingested_for_date.isoformat(),
                    "latest_snapshot_date": last_snapshot.ingested_for_date.isoformat(),
                    "baseline_followers": followers_start,
                    "baseline_wishlists_est": wishlists_start,
                    "latest_followers": followers_end,
                    "latest_wishlists_est": wishlists_end,
                    "days_covered": days,
                },
            )
            momentum_entries.append(entry)

        if not momentum_entries:
            self.stdout.write(self.style.WARNING(f"[{window_code}] No qualifying games found."))
            if not dry_run:
                models.WishlistMomentum.objects.filter(window=window_code, calc_date=calc_date).delete()
            return

        # Sort descending by delta_per_day and compute percentile/rank
        momentum_entries.sort(key=lambda entry: entry.delta_per_day, reverse=True)
        total = len(momentum_entries)

        filtered_entries: List[models.WishlistMomentum] = []
        for idx, entry in enumerate(momentum_entries, start=1):
            percentile = 100.0 * (total - idx + 1) / total
            entry.percentile = round(percentile, 2)
            entry.rank = idx

            if percentile >= 75.0:
                filtered_entries.append(entry)

        self.stdout.write(
            self.style.SUCCESS(
                f"[{window_code}] Identified {len(filtered_entries)} high-momentum games out of {total} candidates."
            )
        )

        if dry_run:
            for entry in filtered_entries[:10]:
                self.stdout.write(
                    f"  - {entry.game.name} Δ/day {entry.delta_per_day:.2f} ({entry.percentile} pct) baseline {entry.baseline_value}"
                )
            return

        with transaction.atomic():
            models.WishlistMomentum.objects.filter(window=window_code, calc_date=calc_date).delete()
            models.WishlistMomentum.objects.bulk_create(filtered_entries, batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"[{window_code}] Persisted {len(filtered_entries)} momentum entries."))
