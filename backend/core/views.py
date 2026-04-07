"""
API views powered by Django REST Framework.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Dict, Optional, Tuple, List
from itertools import combinations

import requests
import xlsxwriter
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.db.models import Exists, Max, OuterRef, Subquery, Q
from rest_framework import authentication, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import models, serializers
from .nsfw import NSFW_QUERY_TERMS

User = get_user_model()
logger = logging.getLogger(__name__)
DATE_FMT = "%Y-%m-%d"
DAILY_CSV_FIELDS = [
    "type",
    "name",
    "steam_appid",
    "developers",
    "publishers",
    "website",
    "categories",
    "genres",
    "steam_url",
    "detection_stage",
    "api_response_type",
    "potential_duplicate",
    "release_date",
    "description",
    "supported_languages",
    "followers",
    "wishlists_est",
    "wishlist_rank",
    "discovery_date",
]

NSFW_SNAPSHOT_FIELDS = [
    "source_tags",
    "source_genres",
    "source_categories",
    "description",
    "game__tags",
    "game__genres",
    "game__categories",
    "game__name",
]
NSFW_GAME_FIELDS = ["game__tags", "game__genres", "game__categories", "game__name"]


def _build_nsfw_filter(fields):
    condition = Q()
    for field in fields:
        for keyword in NSFW_QUERY_TERMS:
            condition |= Q(**{f"{field}__icontains": keyword})
    return condition


NSFW_SNAPSHOT_FILTER = _build_nsfw_filter(NSFW_SNAPSHOT_FIELDS)
NSFW_GAME_FILTER = _build_nsfw_filter(NSFW_GAME_FIELDS)


def _parse_iso_date(value: Optional[str], default):
    if not value:
        return default
    try:
        return datetime.strptime(value, DATE_FMT).date()
    except (TypeError, ValueError):
        return default


def _serialize_user(user: User, cache: Dict[int, dict]) -> dict:
    if not user:
        return {}
    if user.id not in cache:
        cache[user.id] = serializers.UserSerializer(user).data
    return cache[user.id]


def _ensure_watchlist_entry(swipe: models.SwipeAction) -> None:
    """Ensure watchlist entry exists/updates when a user selects watchlist."""

    today = timezone.now().date()
    defaults = {
        "first_detected": today,
        "last_checked": today,
        "status_history": [],
        "current_status": "watchlist",
        "check_count": 0,
        "latest_name": swipe.game.name,
        "latest_type": "game",
        "metadata": {},
    }

    entry, _created = models.WatchlistEntry.objects.get_or_create(game=swipe.game, defaults=defaults)
    status_history = list(entry.status_history or [])
    status_history.append(
        {
            "date": today.isoformat(),
            "status": "watchlist",
            "user_id": swipe.user_id,
            "user": swipe.user.get_full_name() or swipe.user.get_username(),
            "note": swipe.note or "",
        }
    )
    entry.status_history = status_history
    entry.current_status = "watchlist"
    entry.last_checked = today
    entry.check_count = (entry.check_count or 0) + 1
    entry.latest_name = swipe.game.name
    entry.metadata = {**(entry.metadata or {}), "last_swipe_id": swipe.id}
    entry.save(update_fields=["status_history", "current_status", "last_checked", "check_count", "latest_name", "metadata"])


def _build_daily_summary(target_date, start_date: Optional[date] = None, end_date: Optional[date] = None, window: str = "day"):
    """Aggregate swipe actions for a target date or window."""

    start = start_date or target_date
    finish = end_date or target_date
    if start > finish:
        start, finish = finish, start

    swipes = (
        models.SwipeAction.objects.filter(created_at__date__range=(start, finish), user__isnull=False)
        .exclude(NSFW_GAME_FILTER)
        .select_related("game", "user")
        .order_by("game__name", "created_at")
    )

    games_map: Dict[int, Dict[str, object]] = {}
    user_cache: Dict[int, dict] = {}
    unique_user_ids = set()

    for swipe in swipes:
        if not swipe.user:
            continue
        unique_user_ids.add(swipe.user_id)
        user_data = _serialize_user(swipe.user, user_cache)

        if swipe.game_id not in games_map:
            games_map[swipe.game_id] = {
                "game": swipe.game,
                "like_users": [],
                "skip_users": [],
                "watchlist_users": [],
                "total_actions": 0,
            }

        entry = games_map[swipe.game_id]
        entry["total_actions"] = int(entry["total_actions"]) + 1

        if swipe.action == models.SwipeAction.ACTION_LIKE:
            entry["like_users"].append(user_data)
        elif swipe.action == models.SwipeAction.ACTION_SKIP:
            entry["skip_users"].append(user_data)
        elif swipe.action == models.SwipeAction.ACTION_WATCHLIST:
            entry["watchlist_users"].append(user_data)

    games_payload = []
    like_count = skip_count = watchlist_count = 0

    for entry in games_map.values():
        like_count += len(entry["like_users"])
        skip_count += len(entry["skip_users"])
        watchlist_count += len(entry["watchlist_users"])
        games_payload.append(
            {
                "game": serializers.GameSerializer(entry["game"]).data,
                "like_users": entry["like_users"],
                "skip_users": entry["skip_users"],
                "watchlist_users": entry["watchlist_users"],
                "total_actions": entry["total_actions"],
            }
        )

    games_payload.sort(
        key=lambda item: (
            len(item["like_users"]),
            len(item["watchlist_users"]),
            item["total_actions"],
        ),
        reverse=True,
    )

    summary = {
        "date": target_date,
        "window": window,
        "start_date": start,
        "end_date": finish,
        "total_actions": like_count + skip_count + watchlist_count,
        "unique_users": len(unique_user_ids),
        "like_count": like_count,
        "skip_count": skip_count,
        "watchlist_count": watchlist_count,
        "games": games_payload,
    }

    return summary


def _build_daily_summary_workbook(summary: dict) -> bytes:
    """Generate an XLSX workbook for the daily summary."""

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    worksheet = workbook.add_worksheet("Daily Summary")

    header_format = workbook.add_format({"bold": True, "bg_color": "#1f2933", "font_color": "#f5f5f5"})
    text_wrap = workbook.add_format({"text_wrap": True})

    headers = [
        "Game Name",
        "Steam AppID",
        "Likes",
        "Skips",
        "Watchlist",
        "Like Users",
        "Skip Users",
        "Watchlist Users",
        "Total Actions",
    ]
    worksheet.write_row(0, 0, headers, header_format)

    for row, game_entry in enumerate(summary["games"], start=1):
        game = game_entry["game"]
        like_users = ", ".join(user.get("display_name") or user.get("username") for user in game_entry["like_users"])
        skip_users = ", ".join(user.get("display_name") or user.get("username") for user in game_entry["skip_users"])
        watch_users = ", ".join(user.get("display_name") or user.get("username") for user in game_entry["watchlist_users"])

        worksheet.write_row(
            row,
            0,
            [
                game.get("name"),
                game.get("steam_appid"),
                len(game_entry["like_users"]),
                len(game_entry["skip_users"]),
                len(game_entry["watchlist_users"]),
                like_users,
                skip_users,
                watch_users,
                game_entry["total_actions"],
            ],
            text_wrap,
        )

    worksheet.autofilter(0, 0, max(len(summary["games"]), 1), len(headers) - 1)
    worksheet.freeze_panes(1, 0)
    worksheet.set_column("A:A", 40)
    worksheet.set_column("B:B", 12)
    worksheet.set_column("C:E", 10)
    worksheet.set_column("F:H", 50)
    worksheet.set_column("I:I", 14)

    workbook.close()
    output.seek(0)
    return output.getvalue()


def _push_summary_to_feishu(summary: dict) -> Tuple[bool, str]:
    """Send a daily summary message to Feishu via webhook."""

    webhook_url = getattr(settings, "FEISHU_WEBHOOK_URL", "")
    if not webhook_url:
        return False, "Feishu webhook not configured."

    lines = [
        f"Steam 新游团队筛选 · {summary['date']}",
        f"总操作：{summary['total_actions']}（👍 {summary['like_count']} / 👎 {summary['skip_count']} / 👀 {summary['watchlist_count']}）",
        f"参与人数：{summary['unique_users']}",
        "",
    ]

    for idx, item in enumerate(summary["games"], start=1):
        game = item["game"]
        like = len(item["like_users"])
        skip = len(item["skip_users"])
        watch = len(item["watchlist_users"])
        lines.append(f"{idx}. {game['name']}（AppID {game['steam_appid']}） 👍{like} | 👎{skip} | 👀{watch}")
        if idx >= 30:
            lines.append("（其余游戏请在系统内查看）")
            break

    payload = {"msg_type": "text", "content": {"text": "\n".join(lines)}}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.ok:
            return True, "Feishu notification sent."
        return False, f"Feishu notification failed: {response.status_code} {response.text}"
    except requests.RequestException as exc:
        logger.exception("Failed to push Feishu notification")
        return False, f"Feishu notification error: {exc}"


class AuthViewSet(viewsets.ViewSet):
    """Session-based authentication endpoints."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = [authentication.SessionAuthentication, authentication.BasicAuthentication]

    def list(self, request):
        if request.user.is_authenticated:
            data = serializers.UserSerializer(request.user).data
            data.update({"is_authenticated": True})
            return Response(data)
        return Response({"is_authenticated": False}, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = serializers.UserSerializer(user).data
        data.update(
            {
                "is_authenticated": False,
                "pending_approval": True,
                "detail": "Registration received. An admin must approve your account before you can sign in.",
            }
        )
        return Response(data, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["post"], url_path="login")
    def login_action(self, request):
        serializer = serializers.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = serializer.validated_data["username"].strip()
        password = serializer.validated_data["password"]
        remember = serializer.validated_data.get("remember_me", False)

        user = authenticate(request, username=credential, password=password)
        if not user and "@" in credential:
            try:
                candidate = User.objects.get(email__iexact=credential)
            except User.DoesNotExist:
                candidate = None
            if candidate:
                user = authenticate(request, username=candidate.username, password=password)
        if not user:
            inactive_candidate = None
            try:
                inactive_candidate = User.objects.get(username__iexact=credential)
            except User.DoesNotExist:
                if "@" in credential:
                    try:
                        inactive_candidate = User.objects.get(email__iexact=credential)
                    except User.DoesNotExist:
                        inactive_candidate = None
            if inactive_candidate and not inactive_candidate.is_active:
                return Response(
                    {"detail": "Your account is awaiting admin approval."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        if not user:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_active:
            return Response(
                {"detail": "Your account is awaiting admin approval."},
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request, user)
        if remember:
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)

        data = serializers.UserSerializer(user).data
        data.update({"is_authenticated": True})
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="logout")
    def logout_action(self, request):
        logout(request)
        return Response({"is_authenticated": False}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        if not request.user.is_authenticated:
            return Response({"is_authenticated": False}, status=status.HTTP_200_OK)
        data = serializers.UserSerializer(request.user).data
        data.update({"is_authenticated": True})
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="csrf")
    def csrf(self, request):
        token = get_token(request)
        return Response({"csrfToken": token})


class GameSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to ingested game snapshots."""

    serializer_class = serializers.GameSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            models.GameSnapshot.objects.select_related("game", "batch")
            .order_by("-ingested_for_date", "-followers")
        )

        today = timezone.now().date()
        target_date = _parse_iso_date(self.request.query_params.get("date"), today)
        qs = qs.filter(ingested_for_date=target_date)
        qs = qs.exclude(NSFW_SNAPSHOT_FILTER)

        min_followers = self.request.query_params.get("min_followers")
        if min_followers:
            try:
                qs = qs.filter(followers__gte=int(min_followers))
            except ValueError:
                pass

        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(source_tags__icontains=tag)

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(source_categories__icontains=category)

        genre = self.request.query_params.get("genre")
        if genre:
            qs = qs.filter(source_genres__icontains=genre)

        source = self.request.query_params.get("source")
        if source:
            qs = qs.filter(batch__source_name=source)

        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            swipe_subquery = models.SwipeAction.objects.filter(
                user=user,
                game_id=OuterRef("game_id"),
            ).order_by("-created_at", "-id")
            qs = qs.annotate(
                user_has_swipe=Exists(swipe_subquery),
                user_action=Subquery(swipe_subquery.values("action")[:1]),
                user_note=Subquery(swipe_subquery.values("note")[:1]),
                user_handled_at=Subquery(swipe_subquery.values("created_at")[:1]),
            )
            exclude_handled = self.request.query_params.get("exclude_handled")
            if exclude_handled and exclude_handled.lower() in {"1", "true", "yes"}:
                qs = qs.filter(user_has_swipe=False)

        return qs


class SwipeActionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Capture swipe interactions and allow users to review their history."""

    serializer_class = serializers.SwipeActionSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication, authentication.BasicAuthentication]

    def get_queryset(self):
        qs = (
            models.SwipeAction.objects.select_related("game", "batch", "user")
            .filter(user=self.request.user)
            .order_by("-created_at")
        ).exclude(NSFW_GAME_FILTER)
        action_param = self.request.query_params.get("action")
        if action_param in {
            models.SwipeAction.ACTION_LIKE,
            models.SwipeAction.ACTION_SKIP,
            models.SwipeAction.ACTION_WATCHLIST,
        }:
            qs = qs.filter(action=action_param)
        date_param = self.request.query_params.get("date")
        if date_param:
            target_date = _parse_iso_date(date_param, None)
            if target_date:
                qs = qs.filter(created_at__date=target_date)
        return qs

    def perform_create(self, serializer):
        data = serializer.validated_data
        existing = (
            models.SwipeAction.objects.filter(user=self.request.user, game=data["game"])
            .order_by("-created_at", "-id")
            .first()
        )
        if existing:
            fields_to_update = []
            if existing.action != data["action"]:
                existing.action = data["action"]
                fields_to_update.append("action")
            if "note" in data:
                existing.note = data.get("note") or ""
                fields_to_update.append("note")
            batch = data.get("batch")
            if batch is not None and batch != existing.batch:
                existing.batch = batch
                fields_to_update.append("batch")
            existing.created_at = timezone.now()
            fields_to_update.append("created_at")
            if fields_to_update:
                existing.save(update_fields=fields_to_update)
            serializer.instance = existing
            swipe = existing
        else:
            swipe = serializer.save(user=self.request.user)
        if swipe.action == models.SwipeAction.ACTION_WATCHLIST:
            _ensure_watchlist_entry(swipe)

    @action(detail=False, methods=["get"], url_path="export")
    def export_csv(self, request):
        """Export the user's swipe history (defaulting to likes) in the daily CSV format."""

        action_filter = request.query_params.get("action") or models.SwipeAction.ACTION_LIKE
        ids_param = request.query_params.get("ids")
        queryset = self.filter_queryset(self.get_queryset())
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        if ids_param:
            try:
                id_list = [int(item) for item in ids_param.split(",") if item.strip()]
                if id_list:
                    queryset = queryset.filter(id__in=id_list)
            except ValueError:
                pass

        swipes = list(queryset.select_related("game", "batch"))
        game_ids = [swipe.game_id for swipe in swipes]

        snapshot_map: Dict[int, models.GameSnapshot] = {}
        if game_ids:
            snapshots = (
                models.GameSnapshot.objects.filter(game_id__in=game_ids)
                .order_by("game_id", "-ingested_for_date", "-created_at", "-id")
            )
            for snapshot in snapshots:
                if snapshot.game_id in snapshot_map:
                    continue
                snapshot_map[snapshot.game_id] = snapshot

        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.DictWriter(output, fieldnames=DAILY_CSV_FIELDS)
        writer.writeheader()

        for swipe in swipes:
            game = swipe.game
            snapshot = snapshot_map.get(swipe.game_id)
            raw_payload = snapshot.raw_payload if snapshot else {}
            row = {
                "type": (raw_payload.get("type") if isinstance(raw_payload, dict) else None) or "game",
                "name": game.name,
                "steam_appid": game.steam_appid,
                "developers": game.developers,
                "publishers": game.publishers,
                "website": game.website,
                "categories": snapshot.source_categories if snapshot else game.categories,
                "genres": snapshot.source_genres if snapshot else game.genres,
                "steam_url": game.steam_url,
                "detection_stage": snapshot.detection_stage if snapshot else game.latest_detection_stage,
                "api_response_type": snapshot.api_response_type if snapshot else game.latest_api_response_type,
                "potential_duplicate": snapshot.potential_duplicate if snapshot else "",
                "release_date": snapshot.release_date_raw or game.latest_release_date,
                "description": snapshot.description or "",
                "supported_languages": snapshot.supported_languages if snapshot else "",
                "followers": snapshot.followers,
                "wishlists_est": snapshot.wishlists_est,
                "wishlist_rank": snapshot.wishlist_rank,
                "discovery_date": snapshot.discovery_date.isoformat() if snapshot and snapshot.discovery_date else "",
            }
            writer.writerow({key: "" if value is None else value for key, value in row.items()})

        filename = f"swipes-{action_filter or 'all'}-{timezone.now().date().isoformat()}.csv"
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class WatchlistEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose watchlist entries for the UI."""

    serializer_class = serializers.WatchlistEntrySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = models.WatchlistEntry.objects.select_related("game").exclude(NSFW_GAME_FILTER)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(current_status=status_filter)

        return qs.order_by("game__name")


class ReportViewSet(viewsets.ViewSet):
    """Reporting endpoints (team summary, exports, notifications)."""

    permission_classes = [permissions.IsAuthenticated]

    def _determine_date(self, request):
        today = timezone.now().date()
        date_param = request.query_params.get("date") or request.data.get("date")
        return _parse_iso_date(date_param, today)

    def _resolve_window(self, target_date: date, window_param: Optional[str]):
        window_value = (window_param or "day").lower()
        if window_value == "week":
            start_date = target_date - timedelta(days=6)
            end_date = target_date
        elif window_value == "month":
            start_date = target_date.replace(day=1)
            last_day = monthrange(target_date.year, target_date.month)[1]
            end_date = target_date.replace(day=last_day)
        else:
            window_value = "day"
            start_date = target_date
            end_date = target_date
        return window_value, start_date, end_date

    @action(detail=False, methods=["get"], url_path="daily-summary")
    def daily_summary(self, request):
        target_date = self._determine_date(request)
        window_param = request.query_params.get("window")
        window_value, start_date, end_date = self._resolve_window(target_date, window_param)
        summary = _build_daily_summary(target_date, start_date=start_date, end_date=end_date, window=window_value)
        return Response(summary)

    @action(detail=False, methods=["get"], url_path="daily-summary/export")
    def daily_summary_export(self, request):
        target_date = self._determine_date(request)
        window_param = request.query_params.get("window")
        window_value, start_date, end_date = self._resolve_window(target_date, window_param)
        summary = _build_daily_summary(target_date, start_date=start_date, end_date=end_date, window=window_value)
        workbook_bytes = _build_daily_summary_workbook(summary)
        filename = f"steam-daily-summary-{target_date.strftime(DATE_FMT)}.xlsx"
        response = HttpResponse(
            workbook_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=["post"], url_path="daily-summary/push")
    def daily_summary_push(self, request):
        target_date = self._determine_date(request)
        window_param = request.data.get("window") or request.query_params.get("window")
        window_value, start_date, end_date = self._resolve_window(target_date, window_param)
        summary = _build_daily_summary(target_date, start_date=start_date, end_date=end_date, window=window_value)
        success, message = _push_summary_to_feishu(summary)
        status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({"success": success, "message": message}, status=status_code)

    @action(detail=False, methods=["get"], url_path="leaderboard")
    def leaderboard(self, request):
        target_date = self._determine_date(request)
        window_param = request.query_params.get("window")
        window_value, start_date, end_date = self._resolve_window(target_date, window_param)

        swipes = (
            models.SwipeAction.objects.filter(created_at__date__range=(start_date, end_date), user__isnull=False)
            .exclude(NSFW_GAME_FILTER)
            .select_related("user", "game")
            .order_by("user_id", "-created_at")
        )

        total_actions = 0
        unique_games = set()
        user_cache: Dict[int, dict] = {}
        member_map: Dict[int, dict] = {}
        like_sets: Dict[int, set] = {}

        for swipe in swipes:
            total_actions += 1
            unique_games.add(swipe.game_id)
            stats = member_map.get(swipe.user_id)
            if not stats:
                stats = {
                    "user": _serialize_user(swipe.user, user_cache),
                    "handled_games": set(),
                    "like_count": 0,
                    "skip_count": 0,
                    "watchlist_count": 0,
                    "total_actions": 0,
                    "last_action_at": swipe.created_at,
                }
                member_map[swipe.user_id] = stats

            stats["total_actions"] += 1
            stats["handled_games"].add(swipe.game_id)
            if swipe.action == models.SwipeAction.ACTION_LIKE:
                stats["like_count"] += 1
                like_sets.setdefault(swipe.user_id, set()).add(swipe.game_id)
            elif swipe.action == models.SwipeAction.ACTION_SKIP:
                stats["skip_count"] += 1
            elif swipe.action == models.SwipeAction.ACTION_WATCHLIST:
                stats["watchlist_count"] += 1

            if swipe.created_at and swipe.created_at > stats["last_action_at"]:
                stats["last_action_at"] = swipe.created_at

        member_stats: List[dict] = []
        for user_id, stats in member_map.items():
            handled_games = stats.pop("handled_games")
            stats["handled_games"] = len(handled_games)
            stats["last_action_at"] = stats["last_action_at"].isoformat() if stats["last_action_at"] else None
            member_stats.append(stats)

        member_stats.sort(key=lambda item: (item["handled_games"], item["like_count"], item["total_actions"]), reverse=True)

        overlap_pairs: List[dict] = []
        like_items = list(like_sets.items())
        for (user_a_id, likes_a), (user_b_id, likes_b) in combinations(like_items, 2):
            intersection = likes_a & likes_b
            if not intersection:
                continue
            union = likes_a | likes_b
            jaccard = len(intersection) / len(union) if union else 0.0
            overlap_pairs.append(
                {
                    "user_a": member_map[user_a_id]["user"],
                    "user_b": member_map[user_b_id]["user"],
                    "shared_likes": len(intersection),
                    "union_size": len(union),
                    "jaccard": round(jaccard, 4),
                }
            )

        overlap_pairs.sort(key=lambda item: (item["jaccard"], item["shared_likes"]), reverse=True)
        overlap_pairs = overlap_pairs[:15]

        payload = {
            "date": target_date.isoformat(),
            "window": window_value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_actions": total_actions,
            "unique_games": len(unique_games),
            "member_count": len(member_stats),
            "member_stats": member_stats,
            "overlap_pairs": overlap_pairs,
        }

        return Response(payload)


class WishlistMomentumViewSet(viewsets.ReadOnlyModelViewSet):
    """Expose wishlist momentum calculations."""

    serializer_class = serializers.WishlistMomentumSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs_all = models.WishlistMomentum.objects.select_related("game")

        window = self.request.query_params.get("window")
        if window:
            qs_all = qs_all.filter(window=window)

        today = timezone.now().date()
        calc_date = _parse_iso_date(self.request.query_params.get("date"), today)
        qs = qs_all.filter(calc_date=calc_date)
        if not qs.exists():
            latest_date = qs_all.aggregate(latest=Max("calc_date")).get("latest")
            if latest_date:
                qs = qs_all.filter(calc_date=latest_date)
            else:
                qs = qs_all.none()

        return qs.order_by("window", "rank")


class HealthViewSet(viewsets.ViewSet):
    """Minimal health endpoint for monitoring."""

    permission_classes = [permissions.AllowAny]

    def list(self, request):
        return Response({"status": "ok", "timestamp": timezone.now().isoformat()}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def ping(self, request):
        return Response({"status": "ok", "timestamp": timezone.now().isoformat()}, status=status.HTTP_200_OK)
