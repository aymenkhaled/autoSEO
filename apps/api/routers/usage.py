"""Usage router — plan limits, AI cost tracking, and usage stats."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import Crawl, Issue, Site, AiUsage, Organization

router = APIRouter(tags=["usage"])

PLAN_LIMITS = {
    "free":    {"sites": 1,   "crawls_per_month": 5,   "pages_per_crawl": 50,   "ai_fixes_per_month": 10},
    "starter": {"sites": 5,   "crawls_per_month": 30,  "pages_per_crawl": 500,  "ai_fixes_per_month": 100},
    "pro":     {"sites": 20,  "crawls_per_month": 100, "pages_per_crawl": 2000, "ai_fixes_per_month": 500},
    "agency":  {"sites": 100, "crawls_per_month": 500, "pages_per_crawl": 5000, "ai_fixes_per_month": 2000},
}


@router.get("")
async def get_usage(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage stats for the current billing period."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    org = (await db.execute(select(Organization).where(Organization.id == auth.org_id))).scalar_one_or_none()
    plan = org.plan if org else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    sites_count = (await db.execute(
        select(func.count(Site.id)).where(Site.org_id == auth.org_id)
    )).scalar() or 0

    crawls_this_month = (await db.execute(
        select(func.count(Crawl.id)).where(
            Crawl.org_id == auth.org_id,
            Crawl.created_at >= month_start,
        )
    )).scalar() or 0

    fixes_this_month = (await db.execute(
        select(func.count(Issue.id)).where(
            Issue.org_id == auth.org_id,
            Issue.fix_status == "applied",
            Issue.applied_at >= month_start,
        )
    )).scalar() or 0

    ai_cost_this_month = (await db.execute(
        select(func.sum(AiUsage.cost_usd)).where(
            AiUsage.org_id == auth.org_id,
            AiUsage.created_at >= month_start,
        )
    )).scalar() or 0.0

    ai_tokens_this_month = (await db.execute(
        select(func.sum(AiUsage.total_tokens)).where(
            AiUsage.org_id == auth.org_id,
            AiUsage.created_at >= month_start,
        )
    )).scalar() or 0

    return {
        "plan": plan,
        "billing_period": {
            "start": month_start.isoformat(),
            "end": (month_start + timedelta(days=32)).replace(day=1).isoformat(),
        },
        "usage": {
            "sites": {"used": sites_count, "limit": limits["sites"]},
            "crawls": {"used": crawls_this_month, "limit": limits["crawls_per_month"]},
            "ai_fixes": {"used": fixes_this_month, "limit": limits["ai_fixes_per_month"]},
        },
        "ai_cost": {
            "cost_usd": float(ai_cost_this_month),
            "tokens": int(ai_tokens_this_month),
        },
        "limits": limits,
    }
