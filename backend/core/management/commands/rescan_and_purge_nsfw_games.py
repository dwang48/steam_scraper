"""
Rescan historical games against live Steam metadata, then purge NSFW records.
"""

from __future__ import annotations

import html
import random
import re
import threading
import time
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
DEFAULT_MAX_RETRIES = 3
DEFAULT_REQUEST_DELAY = 1.25
DEFAULT_REQUEST_JITTER = 0.35

_THREAD_LOCAL = threading.local()


@dataclass
class LiveScanResult:
    game_id: int
    steam_appid: int
    details: dict[str, Any]
    errors: list[str]


class SharedRequestThrottle:
    """Coordinate Steam requests across workers to reduce rate-limit bursts."""

    def __init__(self, base_delay: float, jitter: float):
        self.base_delay = max(0.0, float(base_delay))
        self.jitter = max(0.0, float(jitter))
        self._lock = threading.Lock()
        self._next_request_at = 0.0

    def wait(self) -> None:
        if self.base_delay <= 0 and self.jitter <= 0:
            return

        with self._lock:
            now = time.monotonic()
            sleep_for = max(0.0, self._next_request_at - now)
            next_start = max(now, self._next_request_at)
            delay = self.base_delay + (random.uniform(0.0, self.jitter) if self.jitter else 0.0)
            self._next_request_at = next_start + delay

        if sleep_for > 0:
            time.sleep(sleep_for)

    def backoff(self, seconds: float) -> None:
        if seconds <= 0:
            return
        with self._lock:
            self._next_request_at = max(self._next_request_at, time.monotonic() + seconds)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _get_session() -> requests.Session:
    session = getattr(_THREAD_LOCAL, "steam_session", None)
    if session is None:
        session = requests.Session()
        _THREAD_LOCAL.steam_session = session
    return session


def _parse_retry_after(value: str | None) -> int | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return int(value)
    return None


def _request_with_retries(
    url: str,
    timeout: int,
    throttle: SharedRequestThrottle,
    max_retries: int,
) -> tuple[requests.Response | None, str | None]:
    last_error: str | None = None
    session = _get_session()

    for attempt in range(1, max_retries + 1):
        try:
            throttle.wait()
            response = session.get(url, headers=STORE_HEADERS, timeout=timeout)
            if response.status_code == 403:
                return None, "403 Forbidden"
            if response.status_code == 429:
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                wait_seconds = retry_after or max(5, int(round((throttle.base_delay + throttle.jitter + 1) * attempt * 2)))
                throttle.backoff(wait_seconds)
                last_error = f"429 Too Many Requests (attempt {attempt}/{max_retries}, waited {wait_seconds}s)"
                if attempt < max_retries:
                    time.sleep(wait_seconds)
                    continue
            response.raise_for_status()
            return response, None
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt < max_retries:
                wait_seconds = max(1.0, throttle.base_delay * attempt)
                time.sleep(wait_seconds)
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_retries:
                time.sleep(1)
    return None, last_error


def _fetch_store_tags(
    appid: int,
    timeout: int,
    throttle: SharedRequestThrottle,
    max_retries: int,
) -> tuple[list[str], str | None]:
    response, error = _request_with_retries(
        STORE_PAGE_URL_TEMPLATE.format(appid=appid),
        timeout=timeout,
        throttle=throttle,
        max_retries=max_retries,
    )
    if error or response is None:
        return [], f"store_tags={error}"

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


def _fetch_live_details(
    appid: int,
    timeout: int,
    throttle: SharedRequestThrottle,
    max_retries: int,
) -> tuple[dict[str, Any], list[str]]:
    details: dict[str, Any] = {}
    errors: list[str] = []

    response, error = _request_with_retries(
        DETAILS_URL_TEMPLATE.format(appid=appid),
        timeout=timeout,
        throttle=throttle,
        max_retries=max_retries,
    )
    if response is not None:
        try:
            payload = response.json().get(str(appid), {})
            if payload.get("success") and isinstance(payload.get("data"), dict):
                details = payload["data"]
            else:
                errors.append("appdetails=unsuccessful")
        except ValueError as exc:
            errors.append(f"appdetails=invalid_json:{exc}")
    elif error:
        errors.append(f"appdetails={error}")

    store_tags, tag_error = _fetch_store_tags(
        appid,
        timeout=timeout,
        throttle=throttle,
        max_retries=max_retries,
    )
    if tag_error:
        errors.append(tag_error)
    if store_tags:
        details["store_tags"] = store_tags

    return details, errors


def _scan_one(
    game_id: int,
    steam_appid: int,
    timeout: int,
    throttle: SharedRequestThrottle,
    max_retries: int,
) -> LiveScanResult:
    details, errors = _fetch_live_details(
        steam_appid,
        timeout=timeout,
        throttle=throttle,
        max_retries=max_retries,
    )
    return LiveScanResult(
        game_id=game_id,
        steam_appid=steam_appid,
        details=details,
        errors=errors,
    )


class Command(BaseCommand):
    help = (
        "Remove NSFW games using local description/tag data first, with optional live Steam "
        "rescans for unresolved records."
    )

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
            default=2,
            help="Number of concurrent Steam metadata fetch workers when live rescans are enabled. Default: 2.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=15,
            help="HTTP timeout in seconds for Steam requests. Default: 15.",
        )
        parser.add_argument(
            "--live-fetch",
            action="store_true",
            help="Fetch live Steam metadata for games not already flagged by local description/tag data.",
        )
        parser.add_argument(
            "--request-delay",
            type=float,
            default=DEFAULT_REQUEST_DELAY,
            help=f"Shared base delay in seconds between live Steam requests. Default: {DEFAULT_REQUEST_DELAY}.",
        )
        parser.add_argument(
            "--request-jitter",
            type=float,
            default=DEFAULT_REQUEST_JITTER,
            help=f"Additional random jitter in seconds added to each live request. Default: {DEFAULT_REQUEST_JITTER}.",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=DEFAULT_MAX_RETRIES,
            help=f"Retry count for live Steam requests. Default: {DEFAULT_MAX_RETRIES}.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        live_fetch = bool(options["live_fetch"])
        max_workers = max(1, int(options["max_workers"]))
        timeout = max(5, int(options["timeout"]))
        request_delay = max(0.0, float(options["request_delay"]))
        request_jitter = max(0.0, float(options["request_jitter"]))
        max_retries = max(1, int(options["max_retries"]))
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
            f"(dry_run={dry_run}, live_fetch={live_fetch}, max_workers={max_workers}, "
            f"timeout={timeout}s, request_delay={request_delay}s, request_jitter={request_jitter}s)"
        )

        candidates: list[tuple[models.Game, list[str]]] = []
        local_hit_count = 0
        live_hit_count = 0
        fetch_error_count = 0
        live_scan_games: list[models.Game] = []

        for game in games:
            existing_is_nsfw, existing_reasons = classify_nsfw_game_bundle(game, game.snapshots.all())
            if existing_is_nsfw:
                local_hit_count += 1
                candidates.append((game, existing_reasons))
            elif live_fetch:
                live_scan_games.append(game)

        self.stdout.write(
            f"Local pass complete: local_hits={local_hit_count}, live_queue={len(live_scan_games)}"
        )

        if live_fetch and live_scan_games:
            game_by_id = {game.id: game for game in live_scan_games}
            throttle = SharedRequestThrottle(base_delay=request_delay, jitter=request_jitter)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        _scan_one,
                        game.id,
                        game.steam_appid,
                        timeout,
                        throttle,
                        max_retries,
                    ): game.id
                    for game in live_scan_games
                }
                for index, future in enumerate(as_completed(futures), start=1):
                    result = future.result()
                    game = game_by_id[result.game_id]

                    live_reasons: list[str] = []
                    if result.details:
                        is_live_nsfw, raw_live_reasons = classify_nsfw_from_details(result.details)
                        if is_live_nsfw:
                            live_reasons = [f"live:{reason}" for reason in raw_live_reasons]

                    if live_reasons:
                        live_hit_count += 1
                        candidates.append((game, live_reasons))
                    if result.errors:
                        fetch_error_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"Fetch issues for {game.steam_appid} | {game.name}: {', '.join(result.errors)}"
                            )
                        )

                    if index % 25 == 0 or index == len(live_scan_games):
                        self.stdout.write(
                            f"Live progress {index}/{len(live_scan_games)} | candidates={len(candidates)} "
                            f"| live_hits={live_hit_count} | local_hits={local_hit_count}"
                        )

        if not candidates:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No NSFW games detected after rescanning {len(games)} games "
                    f"(local_hits={local_hit_count}, live_hits={live_hit_count}, fetch_issues={fetch_error_count})."
                )
            )
            return

        candidates.sort(key=lambda item: item[0].steam_appid)
        for game, reasons in candidates:
            self.stdout.write(
                f"{'[dry-run] ' if dry_run else ''}NSFW → {game.steam_appid} | {game.name} | {', '.join(reasons)}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run only. {len(candidates)} games would be removed "
                    f"(local_hits={local_hit_count}, live_hits={live_hit_count}, fetch_issues={fetch_error_count})."
                )
            )
            return

        game_ids = [game.id for game, _reasons in candidates]
        with transaction.atomic():
            deleted_count, deleted_breakdown = models.Game.objects.filter(id__in=game_ids).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {len(game_ids)} NSFW games ({deleted_count} rows deleted including related records). "
                f"local_hits={local_hit_count}, live_hits={live_hit_count}, fetch_issues={fetch_error_count}, "
                f"breakdown={deleted_breakdown}"
            )
        )
