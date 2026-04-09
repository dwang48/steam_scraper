"""
Utilities for identifying adult / NSFW Steam records.
"""

from __future__ import annotations

import html
import re
from typing import Any, Iterable

NSFW_QUERY_TERMS = (
    "adult only",
    "sexual",
    "porn",
    "hentai",
    "xxx",
    "nudity",
    "nude",
    "naked",
    "erotic",
    "nsfw",
    "lewd",
    "fetish",
    "bdsm",
    "brothel",
    "striptease",
    "stripper",
    "prostitute",
    "incest",
    "milf",
)

_WEAK_REASON_LABELS = {"adult", "mature sexual"}

_NSFW_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("adult only", re.compile(r"\badult(?:s)?\s+only\b", re.IGNORECASE)),
    ("adult", re.compile(r"\badult(?:s)?\b", re.IGNORECASE)),
    ("mature sexual", re.compile(r"\bmature\s+(?:sexual|adult|erotic|explicit|content|themes?)\b", re.IGNORECASE)),
    ("explicit sexual", re.compile(r"\bexplicit\s+(?:sexual|erotic|adult)\b", re.IGNORECASE)),
    ("sexual", re.compile(r"\bsexual(?:\s+content|\s+themes?)?\b", re.IGNORECASE)),
    ("sex", re.compile(r"\bsex\w*\b", re.IGNORECASE)),
    ("porn", re.compile(r"\bporn\w*\b", re.IGNORECASE)),
    ("hentai", re.compile(r"\bhentai\b", re.IGNORECASE)),
    ("erotic", re.compile(r"\berotic\b", re.IGNORECASE)),
    ("nsfw", re.compile(r"\bnsfw\b", re.IGNORECASE)),
    ("nudity", re.compile(r"\bnudity\b", re.IGNORECASE)),
    ("nude", re.compile(r"\bnude\b", re.IGNORECASE)),
    ("naked", re.compile(r"\bnaked\b", re.IGNORECASE)),
    ("lewd", re.compile(r"\blewd\b", re.IGNORECASE)),
    ("fetish", re.compile(r"\bfetish\w*\b", re.IGNORECASE)),
    ("bdsm", re.compile(r"\bbdsm\b", re.IGNORECASE)),
    ("brothel", re.compile(r"\bbrothel\b", re.IGNORECASE)),
    ("prostitute", re.compile(r"\bprostitut\w*\b", re.IGNORECASE)),
    ("striptease", re.compile(r"\bstriptease\b", re.IGNORECASE)),
    ("stripper", re.compile(r"\bstripper\b", re.IGNORECASE)),
    ("incest", re.compile(r"\bincest\b", re.IGNORECASE)),
    ("milf", re.compile(r"\bmilf\b", re.IGNORECASE)),
)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    if isinstance(value, dict):
        return " ".join(filter(None, (_clean_text(item) for item in value.values())))
    if isinstance(value, (list, tuple, set)):
        return " ".join(filter(None, (_clean_text(item) for item in value)))
    return str(value).strip()


def _extract_descriptions(values: Any) -> str:
    if not values:
        return ""
    parts: list[str] = []
    for item in values:
        if isinstance(item, dict):
            description = item.get("description")
            if description:
                parts.append(str(description))
        elif item:
            parts.append(str(item))
    return ";".join(parts)


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _normalize_field_reasons(reasons: list[str]) -> list[str]:
    labels = {reason.split(":", 1)[1] for reason in reasons if ":" in reason}
    normalized = list(reasons)

    if "adult only" in labels:
        normalized = [reason for reason in normalized if not reason.endswith(":adult")]
    if "explicit sexual" in labels:
        normalized = [reason for reason in normalized if not (reason.endswith(":sexual") or reason.endswith(":sex"))]
    if "mature sexual" in labels:
        normalized = [reason for reason in normalized if not (reason.endswith(":sexual") or reason.endswith(":sex"))]
    elif "sexual" in labels:
        normalized = [reason for reason in normalized if not reason.endswith(":sex")]

    return normalized


def _is_nsfw_from_reasons(reasons: list[str]) -> bool:
    if not reasons:
        return False

    labels = {reason.split(":", 1)[1] for reason in reasons if ":" in reason}
    strong_labels = labels - _WEAK_REASON_LABELS
    if strong_labels:
        return True

    return len(labels & _WEAK_REASON_LABELS) >= 2


def detect_nsfw_reasons(text_map: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for field, raw_value in text_map.items():
        text = _clean_text(raw_value)
        if not text:
            continue
        field_reasons: list[str] = []
        for label, pattern in _NSFW_RULES:
            if pattern.search(text):
                field_reasons.append(f"{field}:{label}")
        reasons.extend(_normalize_field_reasons(field_reasons))
    return _dedupe(reasons)


def classify_nsfw_from_details(details: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not details:
        return False, []

    content_descriptors = details.get("content_descriptors") or {}

    text_map = {
        "name": details.get("name"),
        "short_description": details.get("short_description"),
        "detailed_description": details.get("detailed_description"),
        "genres": _extract_descriptions(details.get("genres") or []),
        "categories": _extract_descriptions(details.get("categories") or []),
        "store_tags": details.get("store_tags") or details.get("tags") or [],
        "content_descriptors": content_descriptors,
    }
    reasons = detect_nsfw_reasons(text_map)
    return _is_nsfw_from_reasons(reasons), reasons


def classify_nsfw_from_row(row: dict[str, Any] | None) -> tuple[bool, list[str]]:
    if not row:
        return False, []

    text_map = {
        "name": row.get("name"),
        "description": row.get("description"),
        "genres": row.get("genres") or row.get("source_genres"),
        "categories": row.get("categories") or row.get("source_categories"),
        "tags": row.get("tags") or row.get("source_tags") or row.get("target_tags_found"),
        "nsfw_notes": row.get("content_descriptors") or row.get("content_descriptor_notes"),
    }
    reasons = detect_nsfw_reasons(text_map)
    return _is_nsfw_from_reasons(reasons), reasons


def classify_nsfw_game_bundle(game: Any, snapshots: Iterable[Any]) -> tuple[bool, list[str]]:
    descriptions: list[str] = []
    genres: list[str] = [game.genres] if getattr(game, "genres", "") else []
    categories: list[str] = [game.categories] if getattr(game, "categories", "") else []
    tags: list[str] = [game.tags] if getattr(game, "tags", "") else []

    for snapshot in snapshots:
        if getattr(snapshot, "description", ""):
            descriptions.append(snapshot.description)
        if getattr(snapshot, "source_genres", ""):
            genres.append(snapshot.source_genres)
        if getattr(snapshot, "source_categories", ""):
            categories.append(snapshot.source_categories)
        if getattr(snapshot, "source_tags", ""):
            tags.append(snapshot.source_tags)
        raw_payload = getattr(snapshot, "raw_payload", {}) or {}
        if isinstance(raw_payload, dict):
            if raw_payload.get("content_descriptors"):
                tags.append(str(raw_payload.get("content_descriptors")))
            if raw_payload.get("content_descriptor_notes"):
                tags.append(str(raw_payload.get("content_descriptor_notes")))

    row = {
        "name": getattr(game, "name", ""),
        "description": " ".join(descriptions),
        "genres": ";".join(filter(None, genres)),
        "categories": ";".join(filter(None, categories)),
        "tags": ";".join(filter(None, tags)),
    }
    return classify_nsfw_from_row(row)
