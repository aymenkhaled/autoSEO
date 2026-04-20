"""Fix tasks — Phase 3 implementation."""
from workers.celery_app import app
import structlog

logger = structlog.get_logger()


@app.task(bind=True, max_retries=2)
def apply_ai_fix(self, issue_id: str, site_id: str):
    """Apply an AI-generated fix via the appropriate CMS adapter.
    
    Phase 3 will implement:
    1. Load issue and proposed fix
    2. Select CMS adapter (WordPress/Shopify/Webflow/GitHub)
    3. Apply fix in staging first
    4. Verify change was applied (re-fetch page)
    5. Log to change_log
    """
    logger.info("fix_task_started", issue_id=issue_id, site_id=site_id)
    # TODO: Phase 3 implementation


@app.task(bind=True, max_retries=2)
def run_ai_analysis(self, crawl_id: str, site_id: str):
    """Run Claude AI analysis on crawl results to generate fix suggestions.
    
    Phase 3 will implement:
    1. Load all issues from the crawl
    2. Batch analyze with Claude
    3. Generate fix proposals with confidence scores
    4. Validate fixes (schema, URL, HTML safety)
    5. Store proposals on issues
    """
    logger.info("ai_analysis_started", crawl_id=crawl_id, site_id=site_id)
    # TODO: Phase 3 implementation
