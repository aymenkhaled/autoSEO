"""Business-priority scoring for grouped SEO issues and opportunities."""
from __future__ import annotations

from dataclasses import dataclass
from math import log10
from typing import Any


SEVERITY_WEIGHT = {
    "critical": 100,
    "high": 80,
    "medium": 55,
    "low": 25,
}


@dataclass(frozen=True)
class GscImpact:
    impressions: float = 0
    clicks: float = 0
    ctr: float = 0
    position: float = 0

    @property
    def potential_click_loss(self) -> float:
        if self.impressions <= 0:
            return 0
        benchmark_ctr = 0.05 if self.position <= 10 else 0.025
        return max(0.0, (benchmark_ctr - self.ctr) * self.impressions)


def score_group(
    *,
    severity: str | None,
    total_impact: int | float = 0,
    affected_count: int = 0,
    fix_ready: bool = False,
    gsc: GscImpact | None = None,
) -> dict[str, Any]:
    """Return a stable priority score with an explainable breakdown.

    The score is intentionally heuristic, but deterministic and easy to explain:
    technical severity + crawler impact + affected volume + real Google demand
    + fix readiness.
    """
    gsc = gsc or GscImpact()
    technical = SEVERITY_WEIGHT.get((severity or "").lower(), 40)
    crawler_impact = min(80, float(total_impact or 0) / 10)
    volume = min(35, affected_count * 4)
    search_demand = min(80, log10(max(gsc.impressions, 1)) * 22)
    lost_clicks = min(60, gsc.potential_click_loss * 2)
    fixability = 18 if fix_ready else 0

    score = int(round(technical + crawler_impact + volume + search_demand + lost_clicks + fixability))
    score = max(1, min(300, score))
    if gsc.impressions >= 1000 or gsc.potential_click_loss >= 25:
        label = "High traffic impact"
    elif gsc.impressions >= 100:
        label = "Visible in Google"
    elif fix_ready:
        label = "Fast fix"
    else:
        label = "Technical SEO"

    return {
        "priority_score": score,
        "impact_label": label,
        "breakdown": {
            "technical": round(technical, 2),
            "crawler_impact": round(crawler_impact, 2),
            "affected_volume": round(volume, 2),
            "search_demand": round(search_demand, 2),
            "lost_clicks": round(lost_clicks, 2),
            "fixability": fixability,
        },
        "gsc_impact": {
            "impressions": round(gsc.impressions, 2),
            "clicks": round(gsc.clicks, 2),
            "ctr": round(gsc.ctr, 6),
            "position": round(gsc.position, 3),
            "estimated_click_loss": round(gsc.potential_click_loss, 2),
        },
    }
