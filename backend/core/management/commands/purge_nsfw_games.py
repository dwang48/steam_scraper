"""
Delete NSFW games and their related records from the local database.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core import models
from core.nsfw import classify_nsfw_game_bundle


class Command(BaseCommand):
    help = "Remove NSFW Steam games and their related snapshots / swipe records from the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the records that would be deleted without writing changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        candidates: list[tuple[models.Game, list[str]]] = []

        queryset = models.Game.objects.prefetch_related("snapshots").order_by("steam_appid")
        for game in queryset:
            is_nsfw, reasons = classify_nsfw_game_bundle(game, game.snapshots.all())
            if is_nsfw:
                candidates.append((game, reasons))

        if not candidates:
            self.stdout.write(self.style.SUCCESS("No NSFW games detected."))
            return

        for game, reasons in candidates:
            self.stdout.write(
                f"{'[dry-run] ' if dry_run else ''}NSFW → {game.steam_appid} | {game.name} | {', '.join(reasons)}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run only. {len(candidates)} games would be removed."))
            return

        game_ids = [game.id for game, _reasons in candidates]
        with transaction.atomic():
            deleted_count, deleted_breakdown = models.Game.objects.filter(id__in=game_ids).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {len(game_ids)} NSFW games ({deleted_count} rows deleted including related records): {deleted_breakdown}"
            )
        )
