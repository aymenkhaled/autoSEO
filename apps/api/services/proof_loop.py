"""Proof-loop helpers for before/after SEO impact evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tables import (
    AnalyticsPageMetric,
    Crawl,
    FixProofSnapshot,
    Issue,
    PageSpeedRun,
    SearchConsolePageMetric,
    Site,
)
from packages.shared.seo_domain import (
    FIX_STATUS_DEPLOYED,
    FIX_STATUS_DEPLOYED_AFTER_MERGE,
    FIX_STATUS_GITHUB_PR_CREATED,
    FIX_STATUS_ROLLED_BACK,
)

_DONE_STATUSES = [FIX_STATUS_DEPLOYED, FIX_STATUS_DEPLOYED_AFTER_MERGE, FIX_STATUS_ROLLED_BACK, "applied"]
_OPEN_ISSUE_FILTER = or_(Issue.fix_status.is_(None), Issue.fix_status.notin_(_DONE_STATUSES))


def _float(value) -> float:
    return float(value or 0)


async def current_proof_metrics(db: AsyncSession, *, site: Site, issue_type: str | None = None) -> dict[str, Any]:
    latest_crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.site_id == site.id, Crawl.org_id == site.org_id, Crawl.status == "completed")
            .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    issue_conditions = [
        Issue.site_id == site.id,
        Issue.org_id == site.org_id,
        _OPEN_ISSUE_FILTER,
    ]
    group_conditions = [
        Issue.site_id == site.id,
        Issue.org_id == site.org_id,
        _OPEN_ISSUE_FILTER,
    ]
    if issue_type:
        issue_conditions.append(Issue.type == issue_type)
        group_conditions.append(Issue.type == issue_type)

    open_issue_count = int((await db.execute(select(func.count(Issue.id)).where(*issue_conditions))).scalar() or 0)
    grouped_issue_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(
                    select(Issue.type, Issue.category)
                    .where(*group_conditions)
                    .group_by(Issue.type, Issue.category)
                    .subquery()
                )
            )
        ).scalar()
        or 0
    )

    gsc = (
        await db.execute(
            select(
                func.sum(SearchConsolePageMetric.clicks),
                func.sum(SearchConsolePageMetric.impressions),
                func.avg(SearchConsolePageMetric.ctr),
                func.avg(SearchConsolePageMetric.position),
            ).where(SearchConsolePageMetric.site_id == site.id, SearchConsolePageMetric.org_id == site.org_id)
        )
    ).one()
    ga = (
        await db.execute(
            select(
                func.sum(AnalyticsPageMetric.sessions),
                func.sum(AnalyticsPageMetric.key_events),
                func.sum(AnalyticsPageMetric.total_revenue),
            ).where(AnalyticsPageMetric.site_id == site.id, AnalyticsPageMetric.org_id == site.org_id)
        )
    ).one()
    pagespeed = (
        await db.execute(
            select(func.avg(PageSpeedRun.performance_score)).where(
                PageSpeedRun.site_id == site.id,
                PageSpeedRun.org_id == site.org_id,
                PageSpeedRun.status == "completed",
            )
        )
    ).scalar()

    open_pr_rows = (
        await db.execute(
            select(Issue.type, Issue.proposed_fix_metadata)
            .where(
                Issue.site_id == site.id,
                Issue.org_id == site.org_id,
                Issue.fix_status == FIX_STATUS_GITHUB_PR_CREATED,
            )
            .order_by(Issue.created_at.desc())
            .limit(20)
        )
    ).all()
    open_prs = []
    seen_prs = set()
    for row_type, metadata in open_pr_rows:
        metadata = metadata or {}
        pr_url = metadata.get("pr_url")
        key = pr_url or f"{row_type}:{metadata.get('branch')}"
        if key in seen_prs:
            continue
        seen_prs.add(key)
        open_prs.append({
            "issue_type": row_type,
            "pr_url": pr_url,
            "branch": metadata.get("branch"),
            "risk_level": metadata.get("risk_level"),
            "recrawl_verification_status": metadata.get("recrawl_verification_status", "pending_deploy_recrawl"),
        })

    return {
        "seo_score": latest_crawl.seo_score if latest_crawl else None,
        "pages_crawled": latest_crawl.pages_crawled if latest_crawl else 0,
        "latest_crawl_id": str(latest_crawl.id) if latest_crawl else None,
        "latest_crawl_completed_at": latest_crawl.completed_at.isoformat() if latest_crawl and latest_crawl.completed_at else None,
        "open_issue_count": open_issue_count,
        "grouped_issue_count": grouped_issue_count,
        "gsc": {
            "clicks": _float(gsc[0]),
            "impressions": _float(gsc[1]),
            "ctr": _float(gsc[2]),
            "position": _float(gsc[3]),
        },
        "ga4": {
            "sessions": _float(ga[0]),
            "key_events": _float(ga[1]),
            "revenue": _float(ga[2]),
        },
        "pagespeed": {
            "avg_performance_score": round(_float(pagespeed), 1) if pagespeed is not None else None,
        },
        "open_prs": open_prs,
    }


async def create_proof_snapshot(
    db: AsyncSession,
    *,
    site: Site,
    snapshot_type: str,
    issue_type: str | None = None,
    created_by=None,
    evidence: dict[str, Any] | None = None,
) -> FixProofSnapshot:
    metrics = await current_proof_metrics(db, site=site, issue_type=issue_type)
    snapshot = FixProofSnapshot(
        org_id=site.org_id,
        site_id=site.id,
        issue_type=issue_type,
        snapshot_type=snapshot_type,
        pr_url=(evidence or {}).get("pr_url"),
        branch=(evidence or {}).get("branch"),
        seo_score=metrics["seo_score"],
        pages_crawled=metrics["pages_crawled"],
        open_issue_count=metrics["open_issue_count"],
        grouped_issue_count=metrics["grouped_issue_count"],
        gsc_clicks=metrics["gsc"]["clicks"],
        gsc_impressions=metrics["gsc"]["impressions"],
        gsc_ctr=metrics["gsc"]["ctr"],
        gsc_position=metrics["gsc"]["position"],
        ga_sessions=metrics["ga4"]["sessions"],
        ga_key_events=metrics["ga4"]["key_events"],
        ga_revenue=metrics["ga4"]["revenue"],
        pagespeed_score=int(round(metrics["pagespeed"]["avg_performance_score"])) if metrics["pagespeed"]["avg_performance_score"] is not None else None,
        evidence={**metrics, **(evidence or {})},
        created_by=created_by,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


async def proof_summary(db: AsyncSession, *, site: Site) -> dict[str, Any]:
    current = await current_proof_metrics(db, site=site)
    snapshots = (
        await db.execute(
            select(FixProofSnapshot)
            .where(FixProofSnapshot.site_id == site.id, FixProofSnapshot.org_id == site.org_id)
            .order_by(FixProofSnapshot.created_at.desc())
            .limit(30)
        )
    ).scalars().all()

    timeline = [
        {
            "id": str(snapshot.id),
            "snapshot_type": snapshot.snapshot_type,
            "issue_type": snapshot.issue_type,
            "pr_url": snapshot.pr_url,
            "branch": snapshot.branch,
            "seo_score": snapshot.seo_score,
            "open_issue_count": snapshot.open_issue_count,
            "grouped_issue_count": snapshot.grouped_issue_count,
            "gsc_clicks": _float(snapshot.gsc_clicks),
            "gsc_impressions": _float(snapshot.gsc_impressions),
            "ga_sessions": _float(snapshot.ga_sessions),
            "ga_key_events": _float(snapshot.ga_key_events),
            "ga_revenue": _float(snapshot.ga_revenue),
            "pagespeed_score": snapshot.pagespeed_score,
            "evidence": snapshot.evidence or {},
            "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        }
        for snapshot in snapshots
    ]

    proof_pairs = _paired_proof_groups(timeline)
    latest_pair = next((pair for pair in proof_pairs if pair.get("delta")), None)
    delta = latest_pair["delta"] if latest_pair else None

    return {
        "site_id": str(site.id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current": current,
        "timeline": timeline,
        "proof_pairs": proof_pairs,
        "delta": delta,
        "proof_status": "collecting" if not timeline else "ready",
        "message": "Proof tracks crawl health, Search Console demand, GA4 business impact, PageSpeed, and GitHub PR recrawl status. A PR is not considered fixed until recrawl evidence improves.",
    }


def _proof_pair_key(snapshot: dict[str, Any]) -> tuple[str, str, str]:
    """Pair proof by the same root cause and PR identity, not by latest rows."""
    return (
        snapshot.get("issue_type") or "site",
        snapshot.get("pr_url") or "",
        snapshot.get("branch") or "",
    )


def _snapshot_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "seo_score": (after.get("seo_score") or 0) - (before.get("seo_score") or 0),
        "open_issue_count": (after.get("open_issue_count") or 0) - (before.get("open_issue_count") or 0),
        "grouped_issue_count": (after.get("grouped_issue_count") or 0) - (before.get("grouped_issue_count") or 0),
        "gsc_clicks": round((after.get("gsc_clicks") or 0) - (before.get("gsc_clicks") or 0), 2),
        "gsc_impressions": round((after.get("gsc_impressions") or 0) - (before.get("gsc_impressions") or 0), 2),
        "ga_revenue": round((after.get("ga_revenue") or 0) - (before.get("ga_revenue") or 0), 2),
        "pagespeed_score": (after.get("pagespeed_score") or 0) - (before.get("pagespeed_score") or 0),
    }


def _paired_proof_groups(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: dict[tuple[str, str, str], dict[str, Any]] = {}
    for snapshot in reversed(timeline):
        key = _proof_pair_key(snapshot)
        pair = pairs.setdefault(
            key,
            {
                "issue_type": key[0],
                "pr_url": key[1] or None,
                "branch": key[2] or None,
                "before": None,
                "after_recrawl": None,
                "after_7_days": None,
                "after_28_days": None,
                "manual_snapshots": [],
                "delta": None,
                "proof_status": "collecting",
            },
        )
        snapshot_type = snapshot.get("snapshot_type")
        if snapshot_type == "before_pr":
            pair["before"] = snapshot
        elif snapshot_type == "after_recrawl":
            pair["after_recrawl"] = snapshot
        elif snapshot_type == "after_7_days":
            pair["after_7_days"] = snapshot
        elif snapshot_type == "after_28_days":
            pair["after_28_days"] = snapshot
        elif snapshot_type == "manual":
            pair["manual_snapshots"].append(snapshot)

    for pair in pairs.values():
        before = pair.get("before") or (pair["manual_snapshots"][-1] if pair["manual_snapshots"] else None)
        after = pair.get("after_28_days") or pair.get("after_7_days") or pair.get("after_recrawl")
        if before and after:
            pair["delta"] = _snapshot_delta(before, after)
            pair["proof_status"] = "proven_after_recrawl" if pair.get("after_recrawl") else "proven_later_window"
        elif before:
            pair["proof_status"] = "waiting_for_deploy_recrawl"

    return sorted(
        pairs.values(),
        key=lambda pair: (
            1 if pair.get("delta") else 0,
            (pair.get("after_28_days") or pair.get("after_7_days") or pair.get("after_recrawl") or pair.get("before") or {}).get("created_at") or "",
        ),
        reverse=True,
    )
