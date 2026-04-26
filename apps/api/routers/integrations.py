"""Organization-level integration certification summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.tables import ConnectionCertification, Site
from packages.shared.seo_domain import CONNECTION_CAPABILITY_SUMMARY, connection_capabilities
from schemas.auth import AuthContext

router = APIRouter(tags=["integrations"])
settings = get_settings()


def _provider_configured(connection_type: str) -> bool:
    if connection_type == "github":
        return bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY)
    if connection_type in {"crawler", "snippet"}:
        return True
    return False


@router.get("/integrations/certification")
async def certification_dashboard(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sites = (
        await db.execute(select(Site).where(Site.org_id == auth.org_id).order_by(Site.created_at.desc()))
    ).scalars().all()
    certifications = (
        await db.execute(select(ConnectionCertification).where(ConnectionCertification.org_id == auth.org_id))
    ).scalars().all()
    cert_by_site_type = {
        (str(cert.site_id), cert.connection_type): cert
        for cert in certifications
    }

    rows = []
    for site in sites:
        site_rows = []
        for connection_type in CONNECTION_CAPABILITY_SUMMARY.keys():
            cert = cert_by_site_type.get((str(site.id), connection_type))
            caps = connection_capabilities(connection_type)
            status = cert.status if cert else "not_connected"
            if connection_type == site.connection_type and not cert:
                status = "credentials_tested" if connection_type in {"crawler", "snippet"} else "not_certified"
            site_rows.append({
                "connection_type": connection_type,
                "label": caps["label"],
                "status": status,
                "message": cert.message if cert else "No real certification has been recorded for this site and connection.",
                "provider_configured": _provider_configured(connection_type),
                "auto_deploy_capable": bool(caps["supported_fix_fields"]),
                "supported_fix_fields": caps["supported_fix_fields"],
                "last_tested_at": cert.last_tested_at.isoformat() if cert and cert.last_tested_at else None,
                "safe_fix_tested_at": cert.safe_fix_tested_at.isoformat() if cert and cert.safe_fix_tested_at else None,
            })
        rows.append({
            "site_id": str(site.id),
            "site_name": site.name,
            "domain": site.domain,
            "current_connection_type": site.connection_type,
            "ownership_verified": bool(site.ownership_verified),
            "certifications": site_rows,
        })

    return {
        "sites": rows,
        "total_sites": len(rows),
        "status_order": ["not_connected", "sandbox_only", "credentials_tested", "safe_fix_tested", "production_ready", "failed"],
        "message": "Certification separates sandbox wiring from real credentials and safe staging/draft fix tests.",
    }
