"""Agency/client workspace APIs."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import Client, ClientSite, Site
from schemas.auth import AuthContext

router = APIRouter(tags=["agency"])


class ClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    contact_email: str | None = None
    brand_name: str | None = None
    logo_url: str | None = None


class ClientSiteAssignRequest(BaseModel):
    site_id: UUID


@router.get("/agency/clients")
async def list_clients(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Client, func.count(ClientSite.id))
            .join(ClientSite, ClientSite.client_id == Client.id, isouter=True)
            .where(Client.org_id == auth.org_id)
            .group_by(Client.id)
            .order_by(Client.created_at.desc())
        )
    ).all()
    return {
        "clients": [
            {
                "id": str(client.id),
                "name": client.name,
                "contact_email": client.contact_email,
                "brand_name": client.brand_name,
                "logo_url": client.logo_url,
                "site_count": int(site_count or 0),
                "created_at": client.created_at.isoformat() if client.created_at else None,
            }
            for client, site_count in rows
        ],
        "total": len(rows),
        "message": "Agency mode groups sites by client for white-label reports, digest previews, and proof-of-work views.",
    }


@router.post("/agency/clients", status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreateRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client = Client(
        org_id=auth.org_id,
        name=data.name,
        contact_email=data.contact_email,
        brand_name=data.brand_name,
        logo_url=data.logo_url,
        created_by=auth.user_id,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return {"id": str(client.id), "name": client.name, "message": "Client workspace created."}


@router.get("/agency/clients/{client_id}")
async def get_client(
    client_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client = (await db.execute(select(Client).where(Client.id == client_id, Client.org_id == auth.org_id))).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    site_rows = (
        await db.execute(
            select(Site)
            .join(ClientSite, ClientSite.site_id == Site.id)
            .where(ClientSite.client_id == client.id, ClientSite.org_id == auth.org_id)
            .order_by(Site.created_at.desc())
        )
    ).scalars().all()
    return {
        "id": str(client.id),
        "name": client.name,
        "contact_email": client.contact_email,
        "brand_name": client.brand_name,
        "logo_url": client.logo_url,
        "sites": [
            {
                "id": str(site.id),
                "name": site.name,
                "domain": site.domain,
                "status": site.status,
                "ownership_verified": bool(site.ownership_verified),
                "last_crawled_at": site.last_crawled_at.isoformat() if site.last_crawled_at else None,
            }
            for site in site_rows
        ],
        "message": "Client detail is read-only for now; report share links remain snapshot-only and credential-safe.",
    }


@router.post("/agency/clients/{client_id}/sites", status_code=status.HTTP_201_CREATED)
async def assign_site_to_client(
    client_id: UUID,
    data: ClientSiteAssignRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client = (await db.execute(select(Client).where(Client.id == client_id, Client.org_id == auth.org_id))).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    site = (await db.execute(select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    existing = (
        await db.execute(
            select(ClientSite).where(
                ClientSite.client_id == client.id,
                ClientSite.site_id == site.id,
                ClientSite.org_id == auth.org_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return {"id": str(existing.id), "message": "Site is already assigned to this client."}
    link = ClientSite(org_id=auth.org_id, client_id=client.id, site_id=site.id, created_by=auth.user_id)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return {"id": str(link.id), "client_id": str(client.id), "site_id": str(site.id), "message": "Site assigned to client."}
