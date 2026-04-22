"""Keyword cannibalization detector (Gap 13 — deferred → done).

Detects when multiple pages on the same site target the same primary query.
Heuristic: group pages by a normalized key built from H1 (preferred) or title.
When 2+ pages share that key, emit a `keyword_cannibalization` issue per page
in the cluster (each page references its sibling competitors).
"""
from __future__ import annotations

import re
from collections import defaultdict


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "at",
    "by", "with", "from", "is", "are", "be", "as", "your", "you", "we",
    "our", "this", "that", "best", "top", "vs", "&",
}


def _normalize_query(text: str) -> str:
    """Lowercase, strip punctuation, drop stopwords, collapse whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in _STOPWORDS and len(t) > 1]
    return " ".join(sorted(tokens))


def _page_key(page: dict) -> str:
    """Pick the strongest available signal for a page's primary query."""
    h1s = page.get("h1_text") or []
    if isinstance(h1s, list) and h1s:
        return _normalize_query(str(h1s[0]))
    return _normalize_query(page.get("title") or "")


def detect_cannibalization(pages: list[dict]) -> list[dict]:
    """Return a list of issue dicts for cannibalizing pages.

    Each issue points at one page and lists the URLs of the competing siblings
    in `current_value` so the user can resolve it.
    """
    if not pages or len(pages) < 2:
        return []

    clusters: dict[str, list[dict]] = defaultdict(list)
    for p in pages:
        key = _page_key(p)
        if not key or len(key) < 4:
            continue
        clusters[key].append(p)

    issues: list[dict] = []
    for key, group in clusters.items():
        if len(group) < 2:
            continue
        urls = [g.get("url", "") for g in group if g.get("url")]
        for page in group:
            siblings = [u for u in urls if u and u != page.get("url")]
            if not siblings:
                continue
            issues.append({
                "page_id": page.get("_page_id"),
                "type": "keyword_cannibalization",
                "category": "content",
                "severity": "medium",
                "impact_score": 60,
                "current_value": (
                    f"Target query '{key}' is shared with: "
                    + ", ".join(siblings[:5])
                    + ("…" if len(siblings) > 5 else "")
                ),
                "fix_type": "manual",
            })
    return issues
