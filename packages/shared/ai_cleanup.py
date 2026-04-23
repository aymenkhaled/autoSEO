"""Helpers for removing old placeholder AI proposals from the database."""
from __future__ import annotations

from sqlalchemy import select

_PLACEHOLDER_MARKERS = (
    "[AI fix for",
    "ANTHROPIC_API_KEY required",
    "Stub response",
    "AI key required for generation",
)


def is_placeholder_fix(proposed_fix: str | None, reasoning: str | None = None) -> bool:
    values = [proposed_fix or "", reasoning or ""]
    return any(marker in value for value in values for marker in _PLACEHOLDER_MARKERS)


async def clear_placeholder_ai_fixes(db) -> int:
    """Clear old placeholder fix proposals so the UI stops treating them as deployable."""
    from models.tables import Issue

    rows = (await db.execute(select(Issue))).scalars().all()
    cleaned = 0
    for issue in rows:
        metadata = issue.proposed_fix_metadata or {}
        reasoning = ""
        if isinstance(metadata, dict):
            reasoning = str(metadata.get("reasoning") or "")
        if not is_placeholder_fix(issue.proposed_fix, reasoning):
            continue
        issue.proposed_fix = None
        issue.ai_confidence = None
        issue.fix_type = "manual"
        issue.proposed_fix_metadata = {
            **(metadata if isinstance(metadata, dict) else {}),
            "ai_status": "provider_unavailable",
            "placeholder_cleared": True,
        }
        cleaned += 1
    if cleaned:
        await db.commit()
    return cleaned
