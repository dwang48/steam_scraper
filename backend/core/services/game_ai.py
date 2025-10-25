"""
Utilities for generating AI-assisted analysis for Steam games.
"""

from __future__ import annotations

from typing import Any, Dict, List

from openai import OpenAI

from core import models


DEFAULT_SYSTEM_PROMPT = (
    "You are an investment analyst who evaluates unreleased Steam games for publishing potential. "
    "Respond with concise, evidence-based assessments."
)


def build_analysis_prompt(game: models.Game, snapshots: List[models.GameSnapshot], criteria: Dict[str, Any]) -> str:
    """
    Assemble a natural-language prompt that summarises the game and user-provided criteria.
    """

    latest_snapshot = snapshots[0] if snapshots else None
    lines = [
        f"Game: {game.name} (AppID {game.steam_appid})",
        f"Developers: {game.developers or 'Unknown'}; Publishers: {game.publishers or 'Unknown'}",
        f"Genres: {game.genres or 'Unknown'}; Tags: {latest_snapshot.source_tags if latest_snapshot else game.tags}",
        f"Followers: {latest_snapshot.followers if latest_snapshot else 'n/a'}; Wishlist est.: {latest_snapshot.wishlists_est if latest_snapshot else 'n/a'}",
        f"Latest snapshot date: {latest_snapshot.ingested_for_date if latest_snapshot else 'n/a'}",
        "",
        "Evaluation guidance:",
    ]
    for key, value in criteria.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("Return a JSON object with keys risk_score (0-100), upside_score (0-100), summary, and action_item.")
    return "\n".join(lines)


def analyse_game_potential(
    *,
    client: OpenAI,
    game: models.Game,
    snapshots: List[models.GameSnapshot],
    criteria: Dict[str, Any],
    model: str = "gpt-4.1-mini",
) -> Dict[str, Any]:
    """
    Ask the OpenAI Responses API for an investment-style assessment.
    """

    prompt = build_analysis_prompt(game, snapshots, criteria)
    response = client.responses.create(
        model=model,
        input=prompt,
        system=DEFAULT_SYSTEM_PROMPT,
        response_format={"type": "json_schema", "json_schema": _analysis_schema()},
    )

    content = response.output[0].content[0].text  # type: ignore[attr-defined]
    return _safe_json_loads(content)


def _analysis_schema() -> Dict[str, Any]:
    return {
        "name": "GameInvestmentAssessment",
        "schema": {
            "type": "object",
            "properties": {
                "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "upside_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "summary": {"type": "string", "description": "Two-sentence evaluation referencing concrete data."},
                "action_item": {"type": "string", "description": "Recommended next step for the scouting team."},
            },
            "required": ["risk_score", "upside_score", "summary", "action_item"],
        },
        "strict": True,
    }


def _safe_json_loads(raw: str) -> Dict[str, Any]:
    import json

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {raw}") from exc
