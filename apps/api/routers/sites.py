"""Sites router — CRUD operations for managed sites."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from uuid import UUID
from typing import Optional

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.site import SiteCreate, SiteUpdate, SiteResponse, SiteListResponse
from models.tables import Site

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
