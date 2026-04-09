"""
Rescan historical games against live Steam metadata, then purge NSFW records.
"""

from __future__ import annotations

import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction

from core import models
from core.nsfw import classify_nsfw_from_details, classify_nsfw_game_bundle

DETAILS_URL_TEMPLATE = "https://store.steampowered.com/api/appdetails?appids={appid}&cc=us&l=en"
STORE_PAGE_URL_TEMPLATE = "https://store.steampowered.com/app/{appid}/?cc=us&l=en"
STORE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (SteamNSFWRescan/1.0)",
    "Cookie": "birthtime=0; mature_content=1; wants_mature_content=1",
}


@dataclass
class LiveScanResult:
    game_id: int
    steam_appid: int
    details: dict[str, Any]
    errors: list[str]


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _fetch_store_tags(appid: int, timeout: int) -> tuple[list[str], str | None]:
    try:
        response = requests.get(
            STORE_PAGE_URL_TEMPLATE.format(appid=appid),
            headers=STORE_HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        tags: list[str] = []
        for tag_el in soup.select(".glance_tags.popular_tags a.app_tag, .glance_tags.popular_tags .app_tag"):
            tag_text = _clean_text(tag_el.get_text(" ", strip=True))
            if not tag_text or tag_text == "+":
                continue
            if tag_text not in tags:
                tags.append(tag_text)
            if len(";".join(tags)) >= 480 or len(tags) >= 12:
                break
        return tags, ""
    except Exception as exc:
        return [], f"store_tags={exc}"


def _fetch_live_details(appid: int, timeout: int) -> tuple[dict[str, Any], list[str]]:
    details: dict[str, Any] = {}
    errors: list[str] = []

    try:
        response = requests.get(
            DETAILS_URL_TEMPLATE.format(appid=appid),
            headers=STORE_HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json().get(str(appid), {})
        if payload.get("success") and isinstance(payload.get("data"), dict):
            details = payload["data"]
        else:
            errors.append("appdetails=unsuccessful")
    except Exception as exc:
        errors.append(f"appdetails={exc}")

    store_tags, tag_error = _fetch_store_tags(appid, timeout=timeout)
    if tag_error:
        errors.append(tag_error)
    if store_tags:
        details["store_tags"] = store_tags

    return details, errors


def _scan_one(game_id: int, steam_appid: int, timeout: int) -> LiveScanResult:
    details, errors = _fetch_live_details(steam_appid, timeout=timeout)
    return LiveScanResult(
        game_id=game_id,
        steam_appid=steam_appid,
        details=details,
        errors=errors,
    )


class Command(BaseCommand):
    help = "Rescan historical games using live Steam tags/details and remove NSFW games."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the games that would be removed without writing changes.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Only scan the first N games ordered by steam_appid.",
        )
        parser.add_argument(
            "--appid",
            type=int,
            action="append",
            dest="appids",
            help="Restrict the scan to one or more Steam appids.",
        )
        parser.add_argument(
            "--max-workers",
            type=int,
            default=4,
            help="Number of concurrent Steam metadata fetch workers. Default: 4.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=15,
            help="HTTP timeout in seconds for Steam requests. Default: 15.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        max_workers = max(1, int(options["max_workers"]))
        timeout = max(5, int(options["timeout"]))
        limit = options.get("limit")
        requested_appids = options.get("appids") or []

        queryset = models.Game.objects.prefetch_related("snapshots").order_by("steam_appid")
        if requested_appids:
            queryset = queryset.filter(steam_appid__in=requested_appids)

        games = list(queryset[:limit] if limit else queryset)
        if not games:
            self.stdout.write(self.style.WARNING("No games matched the scan scope."))
            return

        self.stdout.write(
            f"Scanning {len(games)} games for historical NSFW cleanup "
            f"(dry_run={dry_run}, max_workers={max_workers}, timeout={timeout}s)"
        )

        existing_reasons_by_game: dict[int, list[str]] = {}
        for game in games:
            existing_is_nsfw, existing_reasons = classify_nsfw_game_bundle(game, game.snapshots.all())
            existing_reasons_by_game[game.id] = existing_reasons if existing_is_nsfw else []

        game_by_id = {game.id: game for game in games}
        candidates: list[tuple[models.Game, list[str]]] = []
        live_hit_count = 0
        existing_hit_count = 0
        fetch_error_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_scan_one, game.id, game.steam_appid, timeout): game.id
                for game in games
            }
            for index, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                game = game_by_id[result.game_id]
                existing_reasons = existing_reasons_by_game.get(game.id, [])
                existing_hit = bool(existing_reasons)

                live_reasons: list[str] = []
                if result.details:
                    is_live_nsfw, raw_live_reasons = classify_nsfw_from_details(result.details)
                    if is_live_nsfw:
                        live_reasons = [f"live:{reason}" for reason in raw_live_reasons]

                if existing_hit:
                    existing_hit_count += 1
                if live_reasons:
                    live_hit_count += 1
                if result.errors:
                    fetch_error_count += 1

                reasons = _unique(existing_reasons + live_reasons)
                if reasons:
                    candidates.append((game, reasons))

                if result.errors:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Fetch issues for {game.steam_appid} | {game.name}: {', '.join(result.errors)}"
                        )
                    )

                if index % 25 == 0 or index == len(games):
                    self.stdout.write(
                        f"Progress {index}/{len(games)} | candidates={len(candidates)} "
                        f"| live_hits={live_hit_count} | existing_hits={existing_hit_count}"
                    )

        if not candidates:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No NSFW games detected after rescanning {len(games)} games "
                    f"(fetch issues on {fetch_error_count} games)."
                )
            )
            return

        for game, reasons in candidates:
            self.stdout.write(
                f"{'[dry-run] ' if dry_run else ''}NSFW → {game.steam_appid} | {game.name} | {', '.join(reasons)}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run only. {len(candidates)} games would be removed "
                    f"(live_hits={live_hit_count}, existing_hits={existing_hit_count}, fetch_issues={fetch_error_count})."
                )
            )
            return

        game_ids = [game.id for game, _reasons in candidates]
        with transaction.atomic():
            deleted_count, deleted_breakdown = models.Game.objects.filter(id__in=game_ids).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {len(game_ids)} NSFW games ({deleted_count} rows deleted including related records). "
                f"live_hits={live_hit_count}, existing_hits={existing_hit_count}, fetch_issues={fetch_error_count}, "
                f"breakdown={deleted_breakdown}"
            )
        )
