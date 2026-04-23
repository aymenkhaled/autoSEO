"""Sites router — CRUD operations for managed sites."""
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from uuid import UUID
from typing import Optional

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.site import SiteCreate, SiteUpdate, SiteResponse, SiteListResponse
from models.tables import Crawl, Issue, Page, Site
from packages.crawler.url_utils import is_safe_url
from packages.shared.seo_domain import FIX_STATUS_DEPLOYED, FIX_STATUS_ROLLED_BACK

router = APIRouter(tags=["sites"])


@router.get("", response_model=SiteListResponse)
async def list_sites(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all sites for the current organization."""
    # Count total
    count_q = select(func.count(Site.id)).where(Site.org_id == auth.org_id)
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch page
    offset = (page - 1) * per_page
    query = (
        select(Site)
        .where(Site.org_id == auth.org_id)
        .order_by(Site.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    sites = result.scalars().all()

    return SiteListResponse(sites=sites, total=total)


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new site to monitor."""
    # Normalize domain
    domain = data.domain.lower().strip()
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"

    # Check for duplicate domain in org
    existing = await db.execute(
        select(Site).where(Site.org_id == auth.org_id, Site.domain == domain)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Site {domain} already exists in your organization",
        )

    site = Site(
        org_id=auth.org_id,
        name=data.name,
        domain=domain,
        connection_type=data.connection_type,
        cms_endpoint=data.cms_endpoint,
        github_repo=data.github_repo,
        github_branch=data.github_branch,
        crawl_frequency=data.crawl_frequency,
        crawl_max_pages=data.crawl_max_pages,
        respect_robots_txt=data.respect_robots_txt,
        crawl_delay_ms=data.crawl_delay_ms,
        status="pending",
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)

    return site


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific site by ID."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.org_id == auth.org_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.get("/{site_id}/summary")
async def get_site_summary(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    latest_crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.site_id == site_id, Crawl.org_id == auth.org_id, Crawl.status == "completed")
            .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    latest_crawl_id = latest_crawl.id if latest_crawl else None
    pages_count = 0
    if latest_crawl_id:
        pages_count = int(
            (
                await db.execute(
                    select(func.count(Page.id)).where(Page.crawl_id == latest_crawl_id, Page.site_id == site_id)
                )
            ).scalar()
            or 0
        )

    open_issues = int(
        (
            await db.execute(
                select(func.count(Issue.id)).where(
                    Issue.site_id == site_id,
                    Issue.org_id == auth.org_id,
                    Issue.fix_status.notin_([FIX_STATUS_DEPLOYED, FIX_STATUS_ROLLED_BACK, "applied"]),
                )
            )
        ).scalar()
        or 0
    )
    deployed_fixes = int(
        (
            await db.execute(
                select(func.count(Issue.id)).where(
                    Issue.site_id == site_id,
                    Issue.org_id == auth.org_id,
                    Issue.fix_status.in_([FIX_STATUS_DEPLOYED, "applied"]),
                )
            )
        ).scalar()
        or 0
    )

    severity_rows = (
        await db.execute(
            select(Issue.severity, func.count(Issue.id))
            .where(Issue.site_id == site_id, Issue.org_id == auth.org_id)
            .group_by(Issue.severity)
        )
    ).all()

    return {
        "site": SiteResponse.model_validate(site).model_dump(mode="json"),
        "latest_crawl": {
            "id": str(latest_crawl.id),
            "status": latest_crawl.status,
            "seo_score": latest_crawl.seo_score,
            "pages_crawled": latest_crawl.pages_crawled,
            "issues_found": latest_crawl.issues_found,
            "completed_at": latest_crawl.completed_at.isoformat() if latest_crawl.completed_at else None,
        }
        if latest_crawl
        else None,
        "metrics": {
            "pages_count": pages_count,
            "open_issues": open_issues,
            "deployed_fixes": deployed_fixes,
            "ownership_verified": bool(site.ownership_verified),
        },
        "issues_by_severity": {
            "critical": next((count for severity, count in severity_rows if severity == "critical"), 0),
            "high": next((count for severity, count in severity_rows if severity == "high"), 0),
            "medium": next((count for severity, count in severity_rows if severity == "medium"), 0),
            "low": next((count for severity, count in severity_rows if severity == "low"), 0),
        },
    }


@router.get("/{site_id}/pages")
async def list_site_pages(
    site_id: UUID,
    crawl_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    target_crawl_id = crawl_id
    if not target_crawl_id:
        latest_crawl = (
            await db.execute(
                select(Crawl.id)
                .where(Crawl.site_id == site_id, Crawl.org_id == auth.org_id)
                .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        target_crawl_id = latest_crawl

    if not target_crawl_id:
        return {"site_id": str(site_id), "crawl_id": None, "pages": [], "total": 0}

    total = int(
        (
            await db.execute(
                select(func.count(Page.id)).where(Page.site_id == site_id, Page.crawl_id == target_crawl_id)
            )
        ).scalar()
        or 0
    )
    rows = (
        await db.execute(
            select(Page)
            .where(Page.site_id == site_id, Page.crawl_id == target_crawl_id)
            .order_by(Page.seo_score.asc().nullslast(), Page.url.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    page_ids = [row.id for row in rows]
    issue_counts = {
        page_id: count
        for page_id, count in (
            await db.execute(
                select(Issue.page_id, func.count(Issue.id))
                .where(Issue.page_id.in_(page_ids))
                .group_by(Issue.page_id)
            )
        ).all()
    } if page_ids else {}

    return {
        "site_id": str(site_id),
        "crawl_id": str(target_crawl_id),
        "pages": [
            {
                "id": str(row.id),
                "url": row.url,
                "title": row.title,
                "status_code": row.status_code,
                "seo_score": row.seo_score,
                "word_count": row.word_count,
                "response_time_ms": row.response_time_ms,
                "issue_count": int(issue_counts.get(row.id, 0)),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
        "total": total,
    }


@router.post("/{site_id}/verify")
async def start_site_verification(
    site_id: UUID,
    data: dict | None = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    method = (data or {}).get("method") or "meta_tag"
    if method not in {"meta_tag", "html_file"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported verification method")

    token = secrets.token_urlsafe(24)
    site.verification_method = method
    site.verification_token = token
    site.verification_requested_at = datetime.now(timezone.utc)
    site.ownership_verified = False
    await db.commit()

    verification_target = site.domain if str(site.domain).startswith("http") else f"https://{site.domain}"
    return {
        "site_id": str(site.id),
        "method": method,
        "token": token,
        "instructions": {
            "meta_tag": f'<meta name="autoseo-site-verification" content="{token}" />',
            "html_file": {
                "filename": f"autoseo-verification-{token}.txt",
                "contents": token,
                "url": f"{verification_target.rstrip('/')}/autoseo-verification-{token}.txt",
            },
        }[method],
    }


@router.post("/{site_id}/verify/check")
async def check_site_verification(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if not site.verification_token or not site.verification_method:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification has not been started")

    domain = site.domain if str(site.domain).startswith("http") else f"https://{site.domain}"
    if not is_safe_url(domain):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site domain failed safety validation")

    verified = False
    checked_url = domain
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        if site.verification_method == "meta_tag":
            resp = await client.get(domain)
            checked_url = str(resp.url)
            body = resp.text.lower()
            token = site.verification_token.lower()
            verified = (
                resp.status_code == 200
                and is_safe_url(checked_url)
                and "autoseo-site-verification" in body
                and token in body
            )
        elif site.verification_method == "html_file":
            checked_url = f"{domain.rstrip('/')}/autoseo-verification-{site.verification_token}.txt"
            resp = await client.get(checked_url)
            verified = resp.status_code == 200 and is_safe_url(str(resp.url)) and site.verification_token in resp.text

    if verified:
        site.ownership_verified = True
        site.verified_at = datetime.now(timezone.utc)
        if site.status == "pending_verification":
            site.status = "pending"
        await db.commit()

    return {
        "site_id": str(site.id),
        "verified": verified,
        "method": site.verification_method,
        "checked_url": checked_url,
        "verified_at": site.verified_at.isoformat() if site.verified_at else None,
    }


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: UUID,
    data: SiteUpdate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update site settings."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.org_id == auth.org_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(site, field, value)

    await db.commit()
    await db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a site and all related data."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.org_id == auth.org_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    await db.delete(site)
    await db.commit()
