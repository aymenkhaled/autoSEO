"""Report tasks — Phase 6 implementation."""
from workers.celery_app import app
import structlog

logger = structlog.get_logger()


@app.task
def send_weekly_digest(org_id: str):
    """Send weekly SEO digest email via Resend.
    
    Phase 6 will implement:
    1. Aggregate weekly stats (score changes, issues found/fixed)
    2. Render React Email template
    3. Send via Resend API
    """
    logger.info("weekly_digest_started", org_id=org_id)
    # TODO: Phase 6 implementation


@app.task
def generate_pdf_report(crawl_id: str, site_id: str):
    """Generate a PDF SEO audit report.
    
    Phase 6 will implement:
    1. Aggregate crawl data
    2. Generate charts/graphs
    3. Render PDF
    4. Upload to Cloudflare R2
    5. Return download URL
    """
    logger.info("pdf_report_started", crawl_id=crawl_id, site_id=site_id)
    # TODO: Phase 6 implementation
