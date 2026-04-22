# AUTOSEO — COMPLETE MASTER PLAN v5
### April 2026 | React + FastAPI | Replit-Ready
### The Only Plan You Need — Synthesized From All Previous Plans + Real-World Testing

---

> **WHAT THIS IS:** The definitive plan incorporating v2, v3, v4, gap analysis, the PDF critical analysis, AND real-world feedback from testing on strategynavigator.ai. This supersedes all previous plans. Paste it to Replit/Cursor/Claude Code.

---

## 🗺 CURRENT STATE (As Of April 2026)

### ✅ CONFIRMED WORKING (from strategynavigator.ai testing)
- P0: Async crawl dispatch (Celery + inline fallback)
- P0: SSRF protection on URL fetches
- P0: INP stored in backend (confirmed by user message)
- P0: Hreflang validator fixed (no false positives)
- P0: Snippet rate limiting
- P1: Redis pool, page-type classifier, modern image format detection, nofollow tracking, bot filtering, response headers
- P2: URL normalization, crawl cancellation, issue-specific Claude prompts, robots.txt cache, conditional GET
- P3: Crawl-to-crawl diff API (`GET /crawls/{id}/diff`)
- P3: Issue aggregation API (`GET /issues/aggregated`)
- P3: Site filters on Issues/Fixes
- P3: FixVersion snapshots
- P3: Keyword cannibalization detection

### 🔴 CONFIRMED FROM REAL TESTING (strategynavigator.ai)
The tool correctly identified:
1. **SPA No Prerender** — React SPA returning `<div id="root"></div>` to crawlers
2. **Keyword Cannibalization** — All pages sharing identical title/meta (same root cause)
3. **Stale Schema Date** — `priceValidUntil="2025-12-31"` expired 4 months ago

### ❌ STILL MISSING (Honest List From All Analysis)
1. **Frontend UI** for diff + aggregation APIs (APIs work, no UI)
2. **Scheduled/Recurring Crawls** (users must manually trigger)
3. **Google Search Console Integration** (no real click/impression data)
4. **CMS Token Rotation** (WordPress/Shopify tokens expire silently)
5. **True SimHash LSH** (current catches ~80% of duplicates)
6. **Additive Scoring Model** (still using deduction — floors at 0)
7. **Google PageSpeed Insights API** (no real Lighthouse scores)
8. **Weekly SEO Digest Email** (retention-critical feature missing)
9. **White-label Agency Mode** (not architected)
10. **Webflow + GitHub CMS Readers** (listed as supported, code is `pass`)
11. **Fix Verification Timing** (5-second wait will NEVER work — needs delayed Celery)
12. **Crawl-to-Crawl Diff UI** (backend done, frontend missing)
13. **IndexNow Notification** (tell Google after fixes are applied)
14. **Content Freshness Detection** (stale content flagging)
15. **GDPR Compliance** (data export/delete endpoints exist but untested)

---

## TABLE OF CONTENTS

1. [Final Database Schema (Complete + All Missing Columns)](#1-database-schema)
2. [SPA Prerender Detection — New Issue Type](#2-spa-detection)
3. [Stale Schema Date Detection — New Issue Type](#3-stale-schema)
4. [Additive Scoring Model — Replace Deduction Model](#4-scoring)
5. [Fix Verification — Delayed Celery Task (Replace 5s Sleep)](#5-fix-verification)
6. [Google Search Console Integration](#6-gsc)
7. [Scheduled Crawls — Celery Beat](#7-scheduled-crawls)
8. [Weekly SEO Digest Email](#8-weekly-digest)
9. [Frontend: What Changed Tab (Crawl Diff UI)](#9-diff-ui)
10. [Frontend: Aggregated Issues View](#10-aggregated-ui)
11. [Frontend: Dashboard Score Trend Chart](#11-score-trend)
12. [IndexNow Integration](#12-indexnow)
13. [True SimHash + LSH Duplicate Detection](#13-simhash)
14. [CMS Token Auto-Rotation](#14-token-rotation)
15. [Webflow CMS Reader](#15-webflow)
16. [GitHub Pages CMS Reader](#16-github)
17. [White-Label Foundation](#17-whitelabel)
18. [Content Freshness Detection](#18-freshness)
19. [Google PageSpeed Insights API](#19-pagespeed)
20. [Complete Implementation Checklist](#20-checklist)

---

## 1. FINAL DATABASE SCHEMA

This is the **complete schema** including all missing columns identified across all analysis.

```sql
-- ============================================================
-- MIGRATION: 005_phase3_complete.sql
-- Run this after existing migrations
-- ============================================================

-- ── ORGANIZATIONS: Add white-label columns ─────────────────
ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS white_label BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS brand_name TEXT,
  ADD COLUMN IF NOT EXISTS brand_logo_url TEXT,
  ADD COLUMN IF NOT EXISTS brand_primary_color TEXT DEFAULT '#6366f1',
  ADD COLUMN IF NOT EXISTS custom_domain TEXT,
  ADD COLUMN IF NOT EXISTS weekly_digest_enabled BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS weekly_digest_day TEXT DEFAULT 'monday';

-- ── SITES: Add all missing columns ─────────────────────────
ALTER TABLE sites
  ADD COLUMN IF NOT EXISTS next_scheduled_crawl TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS gsc_connected BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS gsc_property_url TEXT,
  ADD COLUMN IF NOT EXISTS gsc_access_token_encrypted TEXT,
  ADD COLUMN IF NOT EXISTS gsc_refresh_token_encrypted TEXT,
  ADD COLUMN IF NOT EXISTS gsc_token_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS indexnow_key TEXT DEFAULT gen_random_uuid()::text,
  ADD COLUMN IF NOT EXISTS pagespeed_enabled BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS cms_token_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS cms_token_refresh_encrypted TEXT;

-- ── CRAWLS: Add all missing columns ────────────────────────
ALTER TABLE crawls
  ADD COLUMN IF NOT EXISTS scrapfly_credits_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS layer_stats JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS orphan_pages_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS cancel_reason TEXT,
  ADD COLUMN IF NOT EXISTS pagespeed_sampled INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS previous_crawl_id UUID REFERENCES crawls(id);

-- ── PAGES: Add ALL missing columns ─────────────────────────
ALTER TABLE pages
  ADD COLUMN IF NOT EXISTS inp_ms INTEGER,
  ADD COLUMN IF NOT EXISTS field_lcp_ms INTEGER,
  ADD COLUMN IF NOT EXISTS field_inp_ms INTEGER,
  ADD COLUMN IF NOT EXISTS field_cls_score NUMERIC(4,3),
  ADD COLUMN IF NOT EXISTS field_ttfb_ms INTEGER,
  ADD COLUMN IF NOT EXISTS data_source TEXT DEFAULT 'lab',
  ADD COLUMN IF NOT EXISTS crawl_source TEXT DEFAULT 'crawler',
  ADD COLUMN IF NOT EXISTS geo_score SMALLINT,
  ADD COLUMN IF NOT EXISTS page_type TEXT DEFAULT 'generic',
  ADD COLUMN IF NOT EXISTS is_duplicate_of TEXT,
  ADD COLUMN IF NOT EXISTS canonical_chain_length SMALLINT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS canonical_chain_circular BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS redirect_chain_length SMALLINT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS redirect_chain_loop BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS has_viewport BOOLEAN,
  ADD COLUMN IF NOT EXISTS html_lang TEXT,
  ADD COLUMN IF NOT EXISTS favicon_present BOOLEAN,
  ADD COLUMN IF NOT EXISTS web_manifest_present BOOLEAN,
  ADD COLUMN IF NOT EXISTS charset TEXT,
  ADD COLUMN IF NOT EXISTS mixed_content_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS duplicate_meta_tags BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS hreflang_tags JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS hreflang_has_x_default BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS x_robots_tag TEXT,
  ADD COLUMN IF NOT EXISTS content_security_policy BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS hsts_present BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS response_headers JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS is_https BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS images_non_modern_format INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS nofollow_links_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS heading_hierarchy_errors INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS is_spa_shell BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS schema_dates_stale JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS last_modified_date TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS days_since_modified INTEGER,
  ADD COLUMN IF NOT EXISTS pagespeed_score SMALLINT,
  ADD COLUMN IF NOT EXISTS pagespeed_lcp_ms INTEGER,
  ADD COLUMN IF NOT EXISTS pagespeed_cls NUMERIC(4,3),
  ADD COLUMN IF NOT EXISTS primary_keyword TEXT,
  ADD COLUMN IF NOT EXISTS link_rel_attributes JSONB DEFAULT '[]';

-- ── ISSUES: Add missing columns ────────────────────────────
ALTER TABLE issues
  ADD COLUMN IF NOT EXISTS priority_score INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS estimated_score_gain INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS safety_flags TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS fix_attempt_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS bulk_fix_group_id UUID;

-- ── FIX VERSIONS (snapshots for every applied fix) ─────────
CREATE TABLE IF NOT EXISTS fix_versions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id      UUID REFERENCES issues(id) NOT NULL,
  attempt_number INTEGER NOT NULL DEFAULT 1,
  before_value  TEXT,
  after_value   TEXT,
  proposed_fix  TEXT,
  ai_confidence NUMERIC(3,2),
  explanation   TEXT,
  implementation_hint TEXT,
  status        TEXT DEFAULT 'generated',
  applied_at    TIMESTAMPTZ,
  verified_at   TIMESTAMPTZ,
  rolled_back_at TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- ── GSC PERFORMANCE DATA ────────────────────────────────────
CREATE TABLE IF NOT EXISTS gsc_data (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id       UUID REFERENCES sites(id) NOT NULL,
  org_id        UUID REFERENCES organizations(id) NOT NULL,
  page_url      TEXT NOT NULL,
  query         TEXT NOT NULL,
  date          DATE NOT NULL,
  clicks        INTEGER DEFAULT 0,
  impressions   INTEGER DEFAULT 0,
  ctr           NUMERIC(5,4),
  position      NUMERIC(6,2),
  created_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE(site_id, page_url, query, date)
);

-- ── COMPETITOR TRACKING ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS competitors (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id       UUID REFERENCES sites(id) NOT NULL,
  org_id        UUID REFERENCES organizations(id) NOT NULL,
  domain        TEXT NOT NULL,
  name          TEXT,
  last_crawl_id UUID REFERENCES crawls(id),
  last_audited_at TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- ── DIGEST LOG ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS digest_log (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        UUID REFERENCES organizations(id) NOT NULL,
  site_id       UUID REFERENCES sites(id),
  sent_at       TIMESTAMPTZ DEFAULT now(),
  recipient_email TEXT NOT NULL,
  summary       JSONB
);

-- ── MISSING INDEXES ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_pages_site_crawl ON pages(site_id, crawl_id);
CREATE INDEX IF NOT EXISTS idx_issues_site_severity ON issues(site_id, severity);
CREATE INDEX IF NOT EXISTS idx_issues_type ON issues(type);
CREATE INDEX IF NOT EXISTS idx_issues_bulk_group ON issues(bulk_fix_group_id) WHERE bulk_fix_group_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gsc_data_site_url ON gsc_data(site_id, page_url);
CREATE INDEX IF NOT EXISTS idx_gsc_data_site_date ON gsc_data(site_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_fix_versions_issue ON fix_versions(issue_id);
CREATE INDEX IF NOT EXISTS idx_crawls_site_status ON crawls(site_id, status);
CREATE INDEX IF NOT EXISTS idx_crawls_next_scheduled ON sites(next_scheduled_crawl) WHERE next_scheduled_crawl IS NOT NULL;

-- ── RLS ON NEW TABLES ───────────────────────────────────────
ALTER TABLE fix_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE digest_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "org_fix_versions" ON fix_versions
  FOR ALL USING (
    EXISTS (SELECT 1 FROM issues i WHERE i.id = issue_id AND i.org_id = (auth.jwt() ->> 'org_id')::uuid)
  );

CREATE POLICY "org_gsc_data" ON gsc_data
  FOR ALL USING (org_id = (auth.jwt() ->> 'org_id')::uuid);

CREATE POLICY "org_competitors" ON competitors
  FOR ALL USING (org_id = (auth.jwt() ->> 'org_id')::uuid);
```

---

## 2. SPA PRERENDER DETECTION

This is the **#1 issue found on strategynavigator.ai** — React/Vue/Angular sites that return an empty HTML shell to crawlers. Critical new issue type.

```python
# packages/crawler/extractor.py — ADD THIS METHOD to SEOExtractor

def _detect_spa_shell(self) -> dict:
    """
    Detect if this page is a JavaScript SPA shell with no real content.
    Google's mobile-first indexer sees exactly what we see here.
    A React app returning <div id="root"></div> = invisible to Google.
    """
    body = self.soup.find("body")
    if not body:
        return {"is_spa_shell": False}

    body_text = body.get_text(separator=" ", strip=True)
    word_count = len(body_text.split())

    # Check for common SPA root elements
    spa_roots = body.find_all(id=["root", "app", "__next", "gatsby-focus-wrapper"])
    has_spa_root = len(spa_roots) > 0

    # Check for React/Vue/Angular signatures in head
    head = self.soup.find("head") or self.soup
    scripts = head.find_all("script", src=True)
    framework_scripts = [s["src"] for s in scripts
                         if any(fw in s.get("src", "").lower()
                                for fw in ["react", "vue", "angular", "svelte", "next", "gatsby", "vite", "webpack"])]

    # A page is a SPA shell if:
    # - It has a known SPA root element
    # - AND visible word count is < 50 (almost no real content)
    # - AND it loads a JS framework bundle
    is_spa = (
        has_spa_root
        and word_count < 50
        and (len(framework_scripts) > 0 or word_count < 10)
    )

    # Also check: title/H1 set correctly despite being SPA
    # A pre-rendered SPA can have a real title and H1 — those are fine
    title = self.soup.find("title")
    has_real_title = title and len(title.get_text(strip=True)) > 5

    return {
        "is_spa_shell": is_spa,
        "spa_word_count": word_count,
        "spa_has_real_title": has_real_title,
        "spa_framework_scripts": framework_scripts[:3],
    }


# packages/crawler/issue_generator.py — ADD to _check_technical()

def _check_spa(self, page) -> list[Issue]:
    """Detect SPA pages that need pre-rendering for SEO."""
    issues = []

    if page.get("is_spa_shell"):
        issues.append(Issue(
            page_url=page["url"],
            type="spa_no_prerender",
            category="technical",
            severity=self.CRITICAL,
            impact_score=95,
            current_value=(
                f"Page returns empty HTML shell ({page.get('spa_word_count', 0)} words visible). "
                f"Google sees no content. Fix: add vite-plugin-prerender or react-snap."
            ),
            fix_type="manual",
            proposed_fix_metadata={
                "fix_options": [
                    "vite-plugin-prerender (Vite projects)",
                    "react-snap (Create React App)",
                    "Next.js (full SSR/SSG solution)",
                    "Prerender.io (service, no code change)",
                ],
                "priority": "P0 — Every affected page is invisible to Google"
            }
        ))

    return issues
```

### Issue-Specific Claude Prompt for SPA Fix

```python
# packages/ai_engine/prompts.py — ADD TO ISSUE_PROMPTS dict

"spa_no_prerender": """
You are an SEO-focused frontend developer. A client's site is a React SPA that returns
an empty HTML shell to search engine crawlers. Google cannot index their pages.

Site URL: {url}
Framework detected: {framework}
Current visible word count: {word_count}

Generate a concrete implementation plan (not generic advice) for how to fix this:
1. Identify the exact build tool being used from the URL/domain context
2. Give the exact package name and install command
3. Give a minimal code example showing the configuration
4. Estimate time to implement: X hours

Respond in JSON:
{{
  "recommended_solution": "vite-plugin-prerender | react-snap | nextjs_migration | prerender_io",
  "install_command": "npm install --save-dev ...",
  "config_example": "// exact code to add to their config file",
  "estimated_hours": 4,
  "explanation": "Why this is the right choice for their stack"
}}
""",
```

---

## 3. STALE SCHEMA DATE DETECTION

Real issue found on strategynavigator.ai: `priceValidUntil="2025-12-31"` was expired for 4 months. Auto-fixable.

```python
# packages/crawler/extractor.py — ADD THIS METHOD to SEOExtractor

def _detect_stale_schema_dates(self) -> dict:
    """
    Detect JSON-LD schema dates that have expired or will expire soon.
    priceValidUntil, validThrough, expires — if past today = broken rich results.
    Google silently stops showing rich snippets when these expire.
    """
    from datetime import datetime, timezone, timedelta

    stale_dates = []
    today = datetime.now(timezone.utc).date()
    warning_threshold = today + timedelta(days=30)  # Warn 30 days before expiry

    DATE_FIELDS = [
        "priceValidUntil", "validThrough", "expires",
        "availabilityEnds", "eventEndDate", "validFrom",
        "offerExpiry", "discountDeadline",
    ]

    for script in self.soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = [data] if isinstance(data, dict) else data

            for item in items:
                if not isinstance(item, dict):
                    continue
                self._find_stale_dates_recursive(item, stale_dates, DATE_FIELDS, today, warning_threshold)

        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "schema_dates_stale": stale_dates,
        "schema_has_stale_dates": len(stale_dates) > 0,
    }

def _find_stale_dates_recursive(self, obj, results, date_fields, today, warning_threshold):
    """Recursively find date fields in nested schema objects."""
    from datetime import date as date_type
    import dateutil.parser

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in date_fields and isinstance(value, str):
                try:
                    parsed_date = dateutil.parser.parse(value).date()
                    status = None
                    if parsed_date < today:
                        status = "expired"
                    elif parsed_date <= warning_threshold:
                        status = "expiring_soon"

                    if status:
                        results.append({
                            "field": key,
                            "value": value,
                            "parsed_date": str(parsed_date),
                            "status": status,
                            "days_expired": (today - parsed_date).days if status == "expired" else 0,
                        })
                except (ValueError, OverflowError):
                    pass
            elif isinstance(value, (dict, list)):
                self._find_stale_dates_recursive(value, results, date_fields, today, warning_threshold)
    elif isinstance(obj, list):
        for item in obj:
            self._find_stale_dates_recursive(item, results, date_fields, today, warning_threshold)


# packages/crawler/issue_generator.py — ADD to generate()

def _check_schema_dates(self, page) -> list[Issue]:
    """Detect expired or soon-to-expire schema dates."""
    issues = []
    stale_dates = page.get("schema_dates_stale", [])

    if not stale_dates:
        return issues

    expired = [d for d in stale_dates if d.get("status") == "expired"]
    expiring_soon = [d for d in stale_dates if d.get("status") == "expiring_soon"]

    if expired:
        issues.append(Issue(
            page_url=page["url"],
            type="stale_schema_date",
            category="schema",
            severity=self.HIGH,
            impact_score=70,
            current_value=(
                f"{len(expired)} expired schema date(s): "
                + ", ".join(f'{d["field"]}={d["value"]} ({d["days_expired"]}d ago)' for d in expired[:3])
            ),
            fix_type="auto",
            proposed_fix_metadata={"stale_dates": expired, "fix": "Update dates to current year"},
        ))

    if expiring_soon:
        issues.append(Issue(
            page_url=page["url"],
            type="schema_date_expiring",
            category="schema",
            severity=self.MEDIUM,
            impact_score=40,
            current_value=(
                f"{len(expiring_soon)} schema date(s) expiring within 30 days: "
                + ", ".join(f'{d["field"]}={d["value"]}' for d in expiring_soon[:3])
            ),
            fix_type="auto",
        ))

    return issues


# packages/ai_engine/prompts.py — AI prompt for auto-fix

"stale_schema_date": """
You are a schema markup expert. A page has expired JSON-LD dates that are causing Google
to stop showing rich snippets in search results.

Page URL: {url}
Expired fields: {stale_dates}
Today's date: {today}

Generate updated values for each expired field. Rules:
- priceValidUntil: set to end of current year ({current_year}-12-31)
- validThrough: set to 1 year from today
- expires: set to 6 months from today
- eventEndDate: this is a real date — DO NOT change it, flag for human review

Respond in JSON:
{{
  "updates": [
    {{"field": "priceValidUntil", "old_value": "2025-12-31", "new_value": "2026-12-31"}},
    ...
  ],
  "needs_human_review": false,
  "explanation": "Why these updates are safe to auto-apply"
}}
""",
```

---

## 4. ADDITIVE SCORING MODEL

Replace the current deduction model (floors at 0, can't distinguish bad from terrible) with a positive-score model.

```python
# packages/crawler/score_calculator.py — REPLACE calculate_page_score()

def calculate_page_score(page: dict) -> int:
    """
    Additive scoring model (0-100).
    Each factor earns points when present and correct.
    Bad pages score differently — a 15/100 is distinguishably worse than 25/100.
    """

    # Define scoring factors: (name, max_points, earned_condition)
    factors = [
        # CRITICAL FACTORS (40 pts total)
        ("title_good",          15, bool(page.get("title")) and 20 <= page.get("title_length", 0) <= 65),
        ("not_noindex",         10, "noindex" not in page.get("robots_directive", "").lower()),
        ("is_https",             8, page.get("is_https", True)),
        ("has_viewport",         7, page.get("has_viewport", True)),

        # HIGH FACTORS (30 pts total)
        ("meta_description",    10, bool(page.get("meta_description")) and 50 <= page.get("meta_description_length", 0) <= 165),
        ("has_h1",               8, page.get("h1_count", 0) == 1),
        ("no_broken_links",      6, page.get("broken_links_count", 0) == 0),
        ("has_incoming_links",   6, page.get("incoming_links_count", 0) > 0),

        # MEDIUM FACTORS (20 pts total)
        ("has_canonical",        5, bool(page.get("canonical_url"))),
        ("schema_valid",         5, bool(page.get("schema_types")) and page.get("schema_valid", True)),
        ("no_duplicate_meta",    4, not page.get("duplicate_meta_tags", False)),
        ("not_spa_shell",        4, not page.get("is_spa_shell", False)),
        ("no_stale_schema",      2, not page.get("schema_has_stale_dates", False)),

        # LOW FACTORS (10 pts total)
        ("has_html_lang",        3, bool(page.get("html_lang"))),
        ("has_og_tags",          3, bool(page.get("og_title"))),
        ("no_mixed_content",     2, page.get("mixed_content_count", 0) == 0),
        ("good_crawl_depth",     2, page.get("crawl_depth", 0) <= 4),
    ]

    total_possible = sum(f[1] for f in factors)  # Should be 100
    total_earned = sum(f[1] for f in factors if f[2])

    # Performance bonus (up to +5 from CWV field data)
    lcp = page.get("field_lcp_ms") or page.get("lcp_ms", 0)
    if lcp and lcp > 0:
        if lcp <= 2500:
            total_earned += 5
        elif lcp <= 4000:
            total_earned += 2
        # Poor LCP (>4000) adds nothing

    return max(0, min(100, int(total_earned / total_possible * 100)))


def calculate_site_score(pages: list[dict]) -> int:
    """
    Site-level score: weighted average with critical-page penalty.
    """
    if not pages:
        return 0

    scores = [p.get("seo_score", 0) for p in pages]

    # Weighted: lower scores drag more
    p25 = sorted(scores)[len(scores) // 4]   # 25th percentile
    p75 = sorted(scores)[len(scores) * 3 // 4]  # 75th percentile
    avg = sum(scores) / len(scores)

    # Blend: 60% average, 20% p25 (penalize worst pages), 20% p75 (reward good pages)
    blended = 0.6 * avg + 0.2 * p25 + 0.2 * p75

    # Extra penalty if many SPA shell pages
    spa_count = sum(1 for p in pages if p.get("is_spa_shell"))
    if spa_count > len(pages) * 0.3:  # >30% SPA shells = major penalty
        blended *= 0.7

    return max(0, min(100, int(blended)))
```

---

## 5. FIX VERIFICATION — DELAYED CELERY TASK

The current 5-second sleep is broken. CMS caches need 5-30 minutes to propagate.

```python
# workers/tasks/fix_verification.py — NEW FILE

from celery import shared_task
from datetime import datetime, timezone
import asyncio
import structlog

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=3)
def verify_fix_delayed(self, issue_id: str, site_id: str, attempt: int = 1):
    """
    Verify that a fix was applied successfully.
    Called 5 minutes after fix application, retried at 30m and 2h if needed.
    """
    asyncio.run(_async_verify(issue_id, site_id, attempt))


async def _async_verify(issue_id: str, site_id: str, attempt: int):
    issue = await db.get_issue(issue_id)
    site = await db.get_site(site_id)

    if not issue or not issue.applied_at:
        logger.warning("verify_skip_no_apply", issue_id=issue_id)
        return

    # Re-fetch the page — use Jina for speed
    from packages.crawler.layers.jina_layer import JinaLayer
    jina = JinaLayer(api_key=settings.JINA_API_KEY)
    result = await jina.fetch_for_seo(issue.page_url)

    if not result:
        logger.warning("verify_refetch_failed", issue_id=issue_id, attempt=attempt)
        # Retry with longer delay
        _schedule_retry(issue_id, site_id, attempt)
        return

    from packages.crawler.extractor import SEOExtractor
    signals = SEOExtractor(result.get("html", ""), issue.page_url).extract_all()

    verified = _check_fix_applied(issue, signals)

    if verified:
        await db.update_issue(issue_id,
            fix_status="verified",
            verified_at=datetime.now(timezone.utc),
            verified_score=signals.get("seo_score")
        )
        logger.info("fix_verified", issue_id=issue_id, attempt=attempt)
    else:
        if attempt >= 3:
            # Give up after 3 attempts (covers: 5min, 30min, 2hr)
            await db.update_issue(issue_id, fix_status="verification_failed")
            logger.warning("fix_verification_exhausted", issue_id=issue_id)
        else:
            _schedule_retry(issue_id, site_id, attempt)


def _schedule_retry(issue_id: str, site_id: str, attempt: int):
    """Schedule next verification attempt with exponential backoff."""
    delays = {1: 300, 2: 1800, 3: 7200}  # 5min, 30min, 2hr
    delay = delays.get(attempt + 1, 7200)
    verify_fix_delayed.apply_async(
        args=[issue_id, site_id, attempt + 1],
        countdown=delay
    )


def _check_fix_applied(issue, signals: dict) -> bool:
    """Check if the proposed fix is now present in the re-crawled page."""
    itype = issue.type
    proposed = issue.proposed_fix or ""

    checks = {
        "missing_meta_description": lambda: bool(signals.get("meta_description")),
        "missing_title": lambda: bool(signals.get("title")),
        "title_too_long": lambda: signals.get("title_length", 999) <= 65,
        "title_too_short": lambda: signals.get("title_length", 0) >= 20,
        "missing_canonical": lambda: bool(signals.get("canonical_url")),
        "missing_schema": lambda: bool(signals.get("schema_types")),
        "invalid_schema": lambda: signals.get("schema_valid", False),
        "images_missing_alt": lambda: signals.get("images_missing_alt", 999) == 0,
        "stale_schema_date": lambda: not signals.get("schema_has_stale_dates", True),
        "missing_html_lang": lambda: bool(signals.get("html_lang")),
        "missing_viewport": lambda: signals.get("has_viewport", False),
    }

    check_fn = checks.get(itype)
    if check_fn:
        try:
            return check_fn()
        except Exception:
            return False

    # For unknown types, assume verified if fix was applied
    return True


# workers/tasks/fix.py — MODIFY apply_fix() to schedule verification

async def apply_fix(issue_id: str, site_id: str, org_id: str):
    """Apply an AI-generated fix via CMS API."""
    # ... existing apply logic ...

    # After successful apply, schedule verification
    from workers.tasks.fix_verification import verify_fix_delayed
    verify_fix_delayed.apply_async(
        args=[issue_id, site_id, 1],
        countdown=300  # First check: 5 minutes
    )
    logger.info("fix_verification_scheduled", issue_id=issue_id, delay="5min")
```

---

## 6. GOOGLE SEARCH CONSOLE INTEGRATION

The biggest missing feature. GSC turns guesses into facts: "This issue is costing you 980 clicks/month."

```python
# packages/integrations/gsc.py — NEW FILE

import httpx
import structlog
from datetime import datetime, timedelta
from packages.shared.encryption import decrypt_credential

logger = structlog.get_logger()

GSC_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GSC_TOKEN_URL = "https://oauth2.googleapis.com/token"
GSC_API_BASE = "https://searchconsole.googleapis.com/webmasters/v3"

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


class GSCClient:
    """
    Google Search Console API client.
    Fetches real click/impression/CTR/position data per page.
    """

    def __init__(self, site, settings):
        self.site = site
        self.settings = settings
        self._access_token: str | None = None

    async def get_access_token(self) -> str:
        """Get valid access token, refresh if expired."""
        if self.site.gsc_token_expires_at:
            expires_at = self.site.gsc_token_expires_at
            if datetime.utcnow() < expires_at - timedelta(minutes=5):
                # Token still valid
                if self._access_token:
                    return self._access_token

        # Refresh using refresh token
        refresh_token = decrypt_credential(
            str(self.site.org_id),
            self.site.gsc_refresh_token_encrypted,
            self.site.gsc_token_iv or ""
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(GSC_TOKEN_URL, data={
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            data = resp.json()

        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)

        # Update token expiry in DB
        await db.update_site(str(self.site.id), {
            "gsc_token_expires_at": datetime.utcnow() + timedelta(seconds=expires_in)
        })

        return self._access_token

    async def fetch_performance(
        self,
        start_date: str,
        end_date: str,
        dimensions: list[str] = ["page", "query"],
        row_limit: int = 5000,
    ) -> list[dict]:
        """
        Fetch search performance data.
        Returns list of {page, query, clicks, impressions, ctr, position}.
        """
        token = await self.get_access_token()
        property_url = self.site.gsc_property_url

        async with httpx.AsyncClient(timeout=60) as client:
            all_rows = []
            start_row = 0

            while True:
                resp = await client.post(
                    f"{GSC_API_BASE}/sites/{property_url}/searchAnalytics/query",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "startDate": start_date,
                        "endDate": end_date,
                        "dimensions": dimensions,
                        "rowLimit": min(row_limit, 25000),
                        "startRow": start_row,
                        "dataState": "final",
                    }
                )

                if resp.status_code == 401:
                    # Token expired mid-request — refresh and retry once
                    self._access_token = None
                    token = await self.get_access_token()
                    continue

                resp.raise_for_status()
                data = resp.json()
                rows = data.get("rows", [])
                all_rows.extend(rows)

                if len(rows) < 25000:
                    break  # No more pages
                start_row += len(rows)

            return [self._normalize_row(row, dimensions) for row in all_rows]

    def _normalize_row(self, row: dict, dimensions: list[str]) -> dict:
        keys = row.get("keys", [])
        result = {}
        for i, dim in enumerate(dimensions):
            result[dim] = keys[i] if i < len(keys) else None
        result.update({
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": round(row.get("ctr", 0), 4),
            "position": round(row.get("position", 0), 2),
        })
        return result

    async def get_coverage_issues(self) -> dict:
        """Get index coverage report from GSC."""
        token = await self.get_access_token()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GSC_API_BASE}/sites/{self.site.gsc_property_url}/urlInspection/index:inspect",
                headers={"Authorization": f"Bearer {token}"},
            )
            return resp.json() if resp.status_code == 200 else {}


# workers/tasks/gsc_sync.py — NEW FILE

from celery import shared_task
import asyncio
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_gsc_data(self, site_id: str):
    """
    Fetch 90 days of GSC data for a site.
    Called after each crawl if GSC is connected.
    """
    asyncio.run(_async_gsc_sync(site_id))


async def _async_gsc_sync(site_id: str):
    site = await db.get_site(site_id)
    if not site.gsc_connected or not site.gsc_refresh_token_encrypted:
        logger.info("gsc_not_connected", site_id=site_id)
        return

    from packages.integrations.gsc import GSCClient
    client = GSCClient(site, settings)

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=90)

    try:
        rows = await client.fetch_performance(
            start_date=str(start_date),
            end_date=str(end_date),
            dimensions=["page", "query"],
        )

        if not rows:
            logger.info("gsc_no_data", site_id=site_id)
            return

        # Upsert to gsc_data table
        await db.upsert_gsc_data(site_id, site.org_id, rows)
        logger.info("gsc_sync_complete", site_id=site_id, rows=len(rows))

        # Generate GSC-based insights
        await _generate_gsc_insights(site_id, rows)

    except Exception as e:
        logger.error("gsc_sync_failed", site_id=site_id, error=str(e))


async def _generate_gsc_insights(site_id: str, rows: list[dict]):
    """
    Create high-value insight issues from GSC data.
    These are the most actionable issues in the entire platform.
    """
    from collections import defaultdict

    # Group by page URL
    by_page = defaultdict(lambda: {"clicks": 0, "impressions": 0, "queries": []})
    for row in rows:
        url = row.get("page", "")
        by_page[url]["clicks"] += row["clicks"]
        by_page[url]["impressions"] += row["impressions"]
        by_page[url]["queries"].append(row)

    gsc_issues = []

    for url, data in by_page.items():
        clicks = data["clicks"]
        impressions = data["impressions"]
        ctr = clicks / impressions if impressions > 0 else 0
        top_queries = sorted(data["queries"], key=lambda x: x["impressions"], reverse=True)[:5]

        # HIGH IMPRESSIONS + LOW CTR = broken title/meta
        if impressions > 500 and ctr < 0.02:
            missed_clicks = int(impressions * 0.05) - clicks  # What 5% CTR would be
            gsc_issues.append({
                "page_url": url,
                "type": "low_ctr_high_impressions",
                "category": "gsc",
                "severity": "high",
                "impact_score": min(90, 50 + missed_clicks // 10),
                "current_value": (
                    f"{impressions:,} impressions, {ctr*100:.1f}% CTR "
                    f"(est. {missed_clicks:,} missed clicks/month). "
                    f"Top query: '{top_queries[0]['query'] if top_queries else 'unknown'}'"
                ),
                "fix_type": "semi_auto",
                "proposed_fix_metadata": {
                    "impressions": impressions,
                    "clicks": clicks,
                    "ctr": ctr,
                    "top_queries": top_queries,
                    "missed_clicks_estimate": missed_clicks,
                }
            })

        # HIGH POSITION (3-10) + HIGH IMPRESSIONS = near top 3 opportunity
        for query_row in top_queries[:3]:
            position = query_row.get("position", 99)
            q_impressions = query_row.get("impressions", 0)
            if 3 < position <= 10 and q_impressions > 200:
                gsc_issues.append({
                    "page_url": url,
                    "type": "ranking_opportunity",
                    "category": "gsc",
                    "severity": "medium",
                    "impact_score": 60,
                    "current_value": (
                        f"Ranking #{position:.0f} for '{query_row['query']}' "
                        f"({q_impressions:,} impressions/month). "
                        f"Moving to top 3 could 3-5x your clicks."
                    ),
                    "fix_type": "semi_auto",
                    "proposed_fix_metadata": {"query": query_row["query"], "position": position}
                })

    if gsc_issues:
        # Get latest crawl for this site
        latest_crawl = await db.get_latest_crawl(site_id)
        if latest_crawl:
            await db.bulk_insert_issues(latest_crawl.id, site_id, site.org_id, gsc_issues)
            logger.info("gsc_issues_created", site_id=site_id, count=len(gsc_issues))


# apps/api/routers/gsc.py — NEW ROUTER

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
import httpx

router = APIRouter(prefix="/gsc")


@router.get("/auth/url")
async def get_gsc_auth_url(site_id: str, user=Depends(get_current_user)):
    """Return Google OAuth URL for GSC connection."""
    state = f"{site_id}:{user.org_id}"  # CSRF protection
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.API_URL}/gsc/auth/callback",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = "https://accounts.google.com/o/oauth2/auth?" + "&".join(f"{k}={v}" for k, v in params.items())
    return {"auth_url": url}


@router.get("/auth/callback")
async def gsc_auth_callback(code: str, state: str):
    """Handle GSC OAuth callback — exchange code for tokens."""
    site_id, org_id = state.split(":", 1)

    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": f"{settings.API_URL}/gsc/auth/callback",
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        tokens = resp.json()

    # Encrypt and store tokens
    from packages.shared.encryption import encrypt_credential
    access_enc, access_iv = encrypt_credential(org_id, tokens["access_token"])
    refresh_enc, refresh_iv = encrypt_credential(org_id, tokens.get("refresh_token", ""))

    from datetime import datetime, timedelta
    await db.update_site(site_id, {
        "gsc_connected": True,
        "gsc_access_token_encrypted": access_enc,
        "gsc_refresh_token_encrypted": refresh_enc,
        "gsc_token_iv": refresh_iv,
        "gsc_token_expires_at": datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600)),
    })

    return RedirectResponse(f"{settings.FRONTEND_URL}/sites/{site_id}?gsc=connected")


@router.get("/properties")
async def list_gsc_properties(site_id: str, user=Depends(get_current_user)):
    """List all GSC properties for this user's Google account."""
    site = await db.get_site(site_id)
    if not site.gsc_connected:
        raise HTTPException(400, "GSC not connected")

    from packages.integrations.gsc import GSCClient
    client = GSCClient(site, settings)
    token = await client.get_access_token()

    async with httpx.AsyncClient() as http:
        resp = await http.get(
            "https://www.googleapis.com/webmasters/v3/sites",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = resp.json()

    return {"properties": [s["siteUrl"] for s in data.get("siteEntry", [])]}


@router.post("/sync")
async def trigger_gsc_sync(site_id: str, user=Depends(get_current_user)):
    """Manually trigger GSC data sync."""
    from workers.tasks.gsc_sync import sync_gsc_data
    sync_gsc_data.delay(site_id)
    return {"status": "syncing"}
```

---

## 7. SCHEDULED CRAWLS — CELERY BEAT

Users need automatic re-crawls. Without this, they forget, stop logging in, and churn.

```python
# workers/tasks/scheduled.py — NEW FILE

from celery import shared_task
from celery.schedules import crontab
from datetime import datetime, timezone, timedelta
import asyncio
import structlog

logger = structlog.get_logger()


@shared_task
def trigger_scheduled_crawls():
    """
    Runs every hour. Finds sites due for a crawl and triggers them.
    Frequency options: daily | weekly | monthly
    """
    asyncio.run(_async_trigger_scheduled())


async def _async_trigger_scheduled():
    now = datetime.now(timezone.utc)
    sites = await db.get_sites_due_for_crawl(now)

    for site in sites:
        try:
            # Create crawl record
            crawl_id = await db.create_crawl(
                site_id=str(site.id),
                org_id=str(site.org_id),
                trigger="scheduled",
                status="queued"
            )

            # Dispatch Celery task
            from workers.tasks.crawl import run_site_crawl
            run_site_crawl.delay(str(site.id), crawl_id)

            # Update next scheduled crawl
            next_crawl = _calculate_next_crawl(site.crawl_frequency, now)
            await db.update_site(str(site.id), {"next_scheduled_crawl": next_crawl})

            logger.info("scheduled_crawl_triggered",
                       site_id=str(site.id), next_crawl=str(next_crawl))

        except Exception as e:
            logger.error("scheduled_crawl_failed", site_id=str(site.id), error=str(e))


def _calculate_next_crawl(frequency: str, from_time: datetime) -> datetime:
    """Calculate when the next crawl should be."""
    intervals = {
        "daily":   timedelta(days=1),
        "weekly":  timedelta(weeks=1),
        "monthly": timedelta(days=30),
    }
    delta = intervals.get(frequency, timedelta(weeks=1))
    return from_time + delta


# In celery_app.py — ADD to beat_schedule:
# "trigger-scheduled-crawls": {
#     "task": "workers.tasks.scheduled.trigger_scheduled_crawls",
#     "schedule": crontab(minute=0),  # Every hour on the hour
# },


# Database helper — packages/db/sites.py

async def get_sites_due_for_crawl(now: datetime) -> list:
    """Get all sites that are due for a scheduled crawl."""
    query = """
    SELECT * FROM sites
    WHERE status = 'active'
    AND crawl_frequency != 'never'
    AND (
        next_scheduled_crawl IS NULL
        OR next_scheduled_crawl <= $1
    )
    AND NOT EXISTS (
        SELECT 1 FROM crawls c
        WHERE c.site_id = sites.id
        AND c.status IN ('queued', 'running')
    )
    ORDER BY next_scheduled_crawl ASC NULLS FIRST
    LIMIT 50
    """
    return await db.fetch_all(query, now)


# apps/api/routers/sites.py — ADD endpoint to configure schedule

@router.patch("/{site_id}/schedule")
async def update_crawl_schedule(
    site_id: str,
    body: ScheduleUpdateRequest,
    user=Depends(get_current_user)
):
    """Update crawl schedule for a site."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    frequency_map = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30),
        "never": None,
    }

    if body.frequency not in frequency_map:
        raise HTTPException(400, f"Invalid frequency: {body.frequency}")

    delta = frequency_map[body.frequency]
    next_crawl = (now + delta) if delta else None

    await db.update_site(site_id, {
        "crawl_frequency": body.frequency,
        "next_scheduled_crawl": next_crawl,
    })

    return {"status": "ok", "next_crawl": next_crawl}
```

---

## 8. WEEKLY SEO DIGEST EMAIL

The #1 retention feature. Users never cancel a tool that emails them weekly progress.

```python
# workers/tasks/digest.py — NEW FILE

from celery import shared_task
from celery.schedules import crontab
import asyncio
import structlog

logger = structlog.get_logger()


@shared_task
def send_weekly_digests():
    """Send weekly SEO digest to all active users. Runs Monday 9 AM UTC."""
    asyncio.run(_async_send_all_digests())


async def _async_send_all_digests():
    orgs = await db.get_orgs_with_digest_enabled()
    for org in orgs:
        try:
            await _send_org_digest(org)
        except Exception as e:
            logger.error("digest_failed", org_id=str(org.id), error=str(e))


async def _send_org_digest(org):
    sites = await db.get_sites_for_org(str(org.id))
    if not sites:
        return

    digest_data = []
    for site in sites:
        # Get last 2 crawls for comparison
        crawls = await db.get_recent_crawls(str(site.id), limit=2)
        if not crawls:
            continue

        latest = crawls[0]
        previous = crawls[1] if len(crawls) > 1 else None

        score_change = 0
        if previous and previous.seo_score and latest.seo_score:
            score_change = latest.seo_score - previous.seo_score

        # Get top 3 issues to fix this week
        top_issues = await db.get_top_issues(str(site.id), str(latest.id), limit=3)

        digest_data.append({
            "site_name": site.name,
            "site_domain": site.domain,
            "current_score": latest.seo_score,
            "score_change": score_change,
            "issues_found": latest.issues_found,
            "pages_crawled": latest.pages_crawled,
            "top_issues": [
                {
                    "type": i.type,
                    "severity": i.severity,
                    "description": i.current_value[:100],
                    "fix_type": i.fix_type,
                }
                for i in top_issues
            ],
        })

    if not digest_data:
        return

    # Get org users to email
    users = await db.get_org_users(str(org.id))
    for user in users:
        await _send_digest_email(user.email, org, digest_data)
        await db.log_digest_sent(str(org.id), user.email, digest_data)


async def _send_digest_email(email: str, org, digest_data: list):
    """Send digest via Resend."""
    import resend

    # Build summary
    total_sites = len(digest_data)
    improved = sum(1 for s in digest_data if s["score_change"] > 0)
    declined = sum(1 for s in digest_data if s["score_change"] < 0)
    total_issues = sum(s["issues_found"] for s in digest_data)

    subject = f"📊 Your weekly SEO digest — {total_sites} site{'s' if total_sites > 1 else ''} tracked"
    if improved > 0:
        subject = f"📈 Score improved on {improved} site{'s' if improved > 1 else ''} this week"
    elif declined > 0:
        subject = f"⚠️ SEO score declined — action needed"

    html_body = _build_digest_html(org, digest_data, improved, declined, total_issues)

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": f"{org.brand_name or 'AutoSEO'} <digest@{settings.EMAIL_DOMAIN}>",
        "to": email,
        "subject": subject,
        "html": html_body,
    })


def _build_digest_html(org, digest_data, improved, declined, total_issues) -> str:
    """Build the weekly digest HTML email."""
    brand = org.brand_name or "AutoSEO"
    color = org.brand_primary_color or "#6366f1"

    sites_html = ""
    for site in digest_data:
        score = site["current_score"] or 0
        change = site["score_change"]
        change_icon = "📈" if change > 0 else ("📉" if change < 0 else "➡️")
        change_color = "#22c55e" if change > 0 else ("#ef4444" if change < 0 else "#6b7280")

        top_fix_html = ""
        for issue in site["top_issues"]:
            fix_badge = "⚡ Auto" if issue["fix_type"] == "auto" else ("🔧 Semi-auto" if issue["fix_type"] == "semi_auto" else "👋 Manual")
            top_fix_html += f"""
            <tr>
              <td style="padding:8px 0;color:#374151;font-size:14px;">{issue['type'].replace('_',' ').title()}</td>
              <td style="padding:8px 0;color:#6b7280;font-size:12px;">{fix_badge}</td>
            </tr>
            """

        sites_html += f"""
        <div style="background:#f9fafb;border-radius:8px;padding:20px;margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <h3 style="margin:0;font-size:16px;color:#111827;">{site['site_name']}</h3>
            <span style="font-size:24px;font-weight:bold;color:{color};">{score}<span style="font-size:14px;color:#6b7280;">/100</span></span>
          </div>
          <p style="color:{change_color};margin:4px 0;font-size:14px;">{change_icon} {'+' if change > 0 else ''}{change} points this week</p>
          {'<table style="width:100%;margin-top:12px;">' + top_fix_html + '</table>' if top_fix_html else ''}
        </div>
        """

    return f"""
    <!DOCTYPE html><html><body style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
      <div style="background:{color};border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
        <h1 style="color:white;margin:0;font-size:24px;">{brand} Weekly Digest</h1>
        <p style="color:rgba(255,255,255,0.8);margin:8px 0 0;">Your SEO performance this week</p>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:24px;">
        <div style="text-align:center;background:#f0fdf4;border-radius:8px;padding:16px;">
          <div style="font-size:28px;font-weight:bold;color:#22c55e;">{improved}</div>
          <div style="font-size:12px;color:#6b7280;">Sites Improved</div>
        </div>
        <div style="text-align:center;background:#fff7ed;border-radius:8px;padding:16px;">
          <div style="font-size:28px;font-weight:bold;color:#f97316;">{total_issues}</div>
          <div style="font-size:12px;color:#6b7280;">Issues Found</div>
        </div>
        <div style="text-align:center;background:#fef2f2;border-radius:8px;padding:16px;">
          <div style="font-size:28px;font-weight:bold;color:#ef4444;">{declined}</div>
          <div style="font-size:12px;color:#6b7280;">Sites Declined</div>
        </div>
      </div>
      {sites_html}
      <div style="text-align:center;margin-top:24px;padding:16px;border-top:1px solid #e5e7eb;">
        <a href="{settings.FRONTEND_URL}/dashboard" style="background:{color};color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;">
          View Full Dashboard →
        </a>
        <p style="color:#9ca3af;font-size:12px;margin-top:16px;">
          <a href="{settings.FRONTEND_URL}/settings/notifications" style="color:#9ca3af;">Manage digest settings</a>
        </p>
      </div>
    </body></html>
    """


# Add to celery_app.py beat_schedule:
# "send-weekly-digests": {
#     "task": "workers.tasks.digest.send_weekly_digests",
#     "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Monday 9 AM UTC
# },
```

---

## 9. FRONTEND: WHAT CHANGED TAB (CRAWL DIFF UI)

The diff API exists (`GET /crawls/{id}/diff`) but there's no UI. This is the retention feature.

```tsx
// apps/web/src/components/CrawlDiff.tsx — NEW COMPONENT

import { useQuery } from "@tanstack/react-query";
import { TrendingUp, TrendingDown, Plus, Minus, Edit3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface DiffData {
  new_pages: string[];
  removed_pages: string[];
  score_improved: Array<{ url: string; old_score: number; new_score: number }>;
  score_declined: Array<{ url: string; old_score: number; new_score: number }>;
  title_changed: Array<{ url: string; old_title: string; new_title: string }>;
  new_issues: Array<{ type: string; severity: string; page_url: string }>;
  resolved_issues: Array<{ type: string; page_url: string }>;
  previous_crawl_id: string;
  previous_crawl_date: string;
}

export function CrawlDiff({ crawlId }: { crawlId: string }) {
  const { data, isLoading } = useQuery<DiffData>({
    queryKey: ["crawl-diff", crawlId],
    queryFn: () => fetch(`/api/crawls/${crawlId}/diff`).then(r => r.json()),
  });

  if (isLoading) return <div className="p-4 text-center text-gray-500">Comparing with previous crawl...</div>;
  if (!data?.previous_crawl_id) {
    return (
      <div className="p-8 text-center bg-gray-50 rounded-lg">
        <p className="text-gray-500">No previous crawl to compare against.</p>
        <p className="text-sm text-gray-400 mt-1">Run a second crawl to see what changed.</p>
      </div>
    );
  }

  const totalChanges = (data.new_pages?.length || 0) + (data.removed_pages?.length || 0) +
    (data.score_improved?.length || 0) + (data.score_declined?.length || 0) +
    (data.title_changed?.length || 0);

  if (totalChanges === 0) {
    return (
      <div className="p-8 text-center bg-green-50 rounded-lg">
        <div className="text-3xl mb-2">✅</div>
        <p className="font-semibold text-green-800">No changes since last crawl</p>
        <p className="text-sm text-green-600 mt-1">
          Compared against crawl from {new Date(data.previous_crawl_date).toLocaleDateString()}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Plus className="text-green-500" size={16} />}
          label="New Pages" value={data.new_pages?.length || 0} color="green" />
        <StatCard icon={<Minus className="text-red-500" size={16} />}
          label="Removed Pages" value={data.removed_pages?.length || 0} color="red" />
        <StatCard icon={<TrendingUp className="text-blue-500" size={16} />}
          label="Score Improved" value={data.score_improved?.length || 0} color="blue" />
        <StatCard icon={<TrendingDown className="text-orange-500" size={16} />}
          label="Score Declined" value={data.score_declined?.length || 0} color="orange" />
      </div>

      {/* Score Changes */}
      {(data.score_declined?.length || 0) > 0 && (
        <DiffSection title="⚠️ Score Declined" color="red">
          {data.score_declined.map(item => (
            <DiffRow key={item.url}>
              <span className="text-sm truncate flex-1">{item.url}</span>
              <ScoreChange old={item.old_score} new_={item.new_score} />
            </DiffRow>
          ))}
        </DiffSection>
      )}

      {(data.score_improved?.length || 0) > 0 && (
        <DiffSection title="✅ Score Improved" color="green">
          {data.score_improved.map(item => (
            <DiffRow key={item.url}>
              <span className="text-sm truncate flex-1">{item.url}</span>
              <ScoreChange old={item.old_score} new_={item.new_score} />
            </DiffRow>
          ))}
        </DiffSection>
      )}

      {/* Title Changes */}
      {(data.title_changed?.length || 0) > 0 && (
        <DiffSection title="📝 Title Changes" color="purple" icon={<Edit3 size={16} />}>
          {data.title_changed.map(item => (
            <DiffRow key={item.url} className="flex-col items-start gap-1">
              <span className="text-xs text-gray-500 truncate w-full">{item.url}</span>
              <div className="flex gap-2 text-sm">
                <span className="text-red-500 line-through">{item.old_title}</span>
                <span className="text-gray-400">→</span>
                <span className="text-green-600">{item.new_title}</span>
              </div>
            </DiffRow>
          ))}
        </DiffSection>
      )}

      {/* New Issues */}
      {(data.new_issues?.length || 0) > 0 && (
        <DiffSection title="🆕 New Issues Found" color="orange">
          {data.new_issues.slice(0, 10).map((issue, i) => (
            <DiffRow key={i}>
              <Badge variant={issue.severity === "critical" ? "destructive" : "secondary"}>
                {issue.severity}
              </Badge>
              <span className="text-sm flex-1">{issue.type.replace(/_/g, " ")}</span>
              <span className="text-xs text-gray-400 truncate max-w-[200px]">{issue.page_url}</span>
            </DiffRow>
          ))}
          {data.new_issues.length > 10 &&
            <p className="text-sm text-gray-500 text-center pt-2">
              +{data.new_issues.length - 10} more new issues
            </p>
          }
        </DiffSection>
      )}

      <p className="text-xs text-gray-400 text-center">
        Compared against crawl from {new Date(data.previous_crawl_date).toLocaleDateString()}
      </p>
    </div>
  );
}

// Helper components
function StatCard({ icon, label, value, color }: any) {
  const colors = { green: "bg-green-50 text-green-800", red: "bg-red-50 text-red-800",
    blue: "bg-blue-50 text-blue-800", orange: "bg-orange-50 text-orange-800" };
  return (
    <div className={`rounded-lg p-4 ${colors[color]}`}>
      <div className="flex items-center gap-2 mb-1">{icon}<span className="text-xs">{label}</span></div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}

function DiffSection({ title, color, children }: any) {
  const borders = { red: "border-red-200", green: "border-green-200",
    purple: "border-purple-200", orange: "border-orange-200" };
  return (
    <div className={`border rounded-lg overflow-hidden ${borders[color]}`}>
      <div className="px-4 py-3 bg-gray-50 font-medium text-sm">{title}</div>
      <div className="divide-y">{children}</div>
    </div>
  );
}

function DiffRow({ children, className = "" }: any) {
  return <div className={`flex items-center gap-3 px-4 py-3 ${className}`}>{children}</div>;
}

function ScoreChange({ old, new_ }: { old: number; new_: number }) {
  const diff = new_ - old;
  return (
    <div className="flex items-center gap-2 text-sm font-mono">
      <span className="text-gray-500">{old}</span>
      <span className="text-gray-400">→</span>
      <span className={diff > 0 ? "text-green-600 font-bold" : "text-red-600 font-bold"}>{new_}</span>
      <span className={diff > 0 ? "text-green-500" : "text-red-500"}>({diff > 0 ? "+" : ""}{diff})</span>
    </div>
  );
}
```

---

## 10. FRONTEND: AGGREGATED ISSUES VIEW

The current UI shows individual issues (300 "missing meta description" rows). This groups them.

```tsx
// apps/web/src/components/AggregatedIssues.tsx — NEW COMPONENT

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Zap, Wrench, Hand } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface AggregatedIssue {
  type: string;
  severity: string;
  count: number;
  impact_score: number;
  fix_type: string;
  category: string;
  sample_urls: string[];
  estimated_score_gain: number;
  can_bulk_fix: boolean;
  example_fix?: string;
}

export function AggregatedIssues({ siteId }: { siteId: string }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [bulkApplying, setBulkApplying] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery<AggregatedIssue[]>({
    queryKey: ["issues-aggregated", siteId],
    queryFn: () => fetch(`/api/issues/aggregated?site_id=${siteId}`).then(r => r.json()),
  });

  const toggle = (type: string) => {
    const next = new Set(expanded);
    next.has(type) ? next.delete(type) : next.add(type);
    setExpanded(next);
  };

  const applyBulkFix = async (type: string) => {
    setBulkApplying(type);
    try {
      await fetch("/api/fixes/bulk-apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ site_id: siteId, issue_type: type }),
      });
      refetch();
    } finally {
      setBulkApplying(null);
    }
  };

  if (isLoading) return <div className="p-4 text-center text-gray-400">Loading issues...</div>;

  const critical = data?.filter(i => i.severity === "critical") || [];
  const high = data?.filter(i => i.severity === "high") || [];
  const medium = data?.filter(i => i.severity === "medium") || [];
  const low = data?.filter(i => i.severity === "low") || [];

  const totalIssues = data?.reduce((sum, i) => sum + i.count, 0) || 0;
  const autoFixable = data?.filter(i => i.can_bulk_fix) || [];

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">{totalIssues}</div>
          <div className="text-xs text-gray-500">Total Issues</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-gray-900">{data?.length || 0}</div>
          <div className="text-xs text-gray-500">Unique Issue Types</div>
        </div>
        <div className="bg-green-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-green-700">{autoFixable.length}</div>
          <div className="text-xs text-green-600">Auto-Fixable Types</div>
        </div>
      </div>

      {/* Quick wins: auto-fixable */}
      {autoFixable.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h3 className="font-semibold text-green-800 mb-3 flex items-center gap-2">
            <Zap size={16} className="text-green-600" />
            Quick Wins — {autoFixable.reduce((s, i) => s + i.count, 0)} issues fixable automatically
          </h3>
          <div className="space-y-2">
            {autoFixable.map(issue => (
              <div key={issue.type} className="flex items-center justify-between bg-white rounded p-3">
                <div>
                  <span className="text-sm font-medium">{issue.type.replace(/_/g, " ")}</span>
                  <span className="text-xs text-gray-500 ml-2">({issue.count} pages)</span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="border-green-300 text-green-700 hover:bg-green-100"
                  disabled={bulkApplying === issue.type}
                  onClick={() => applyBulkFix(issue.type)}
                >
                  {bulkApplying === issue.type ? "Fixing..." : `Fix all ${issue.count}`}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Issue groups by severity */}
      {[
        { issues: critical, label: "Critical", color: "red", emoji: "🔴" },
        { issues: high, label: "High", color: "orange", emoji: "🟠" },
        { issues: medium, label: "Medium", color: "yellow", emoji: "🟡" },
        { issues: low, label: "Low", color: "gray", emoji: "⚪" },
      ].filter(g => g.issues.length > 0).map(({ issues, label, emoji }) => (
        <div key={label}>
          <h3 className="font-semibold text-gray-700 mb-2 text-sm">
            {emoji} {label} — {issues.length} issue type{issues.length > 1 ? "s" : ""},
            {" "}{issues.reduce((s, i) => s + i.count, 0)} pages affected
          </h3>
          <div className="space-y-2">
            {issues.sort((a, b) => b.impact_score - a.impact_score).map(issue => (
              <IssueRow
                key={issue.type}
                issue={issue}
                expanded={expanded.has(issue.type)}
                onToggle={() => toggle(issue.type)}
                onBulkFix={() => applyBulkFix(issue.type)}
                applying={bulkApplying === issue.type}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function IssueRow({ issue, expanded, onToggle, onBulkFix, applying }: any) {
  const fixIcon = issue.fix_type === "auto" ? <Zap size={12} /> :
    issue.fix_type === "semi_auto" ? <Wrench size={12} /> : <Hand size={12} />;
  const fixLabel = { auto: "Auto", semi_auto: "Semi-auto", manual: "Manual" }[issue.fix_type as string] || "Manual";

  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50"
        onClick={onToggle}
      >
        {expanded ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}

        <div className="flex-1 min-w-0">
          <span className="font-medium text-sm">{issue.type.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}</span>
          <span className="text-gray-500 text-sm ml-2">({issue.count} pages)</span>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs flex items-center gap-1">
            {fixIcon}{fixLabel}
          </Badge>
          {issue.estimated_score_gain > 0 && (
            <span className="text-xs text-green-600 font-medium">+{issue.estimated_score_gain} pts</span>
          )}
          {issue.can_bulk_fix && (
            <Button size="sm" variant="ghost" className="text-xs h-7"
              onClick={(e) => { e.stopPropagation(); onBulkFix(); }}
              disabled={applying}>
              {applying ? "..." : "Fix all"}
            </Button>
          )}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t bg-gray-50">
          <p className="text-xs text-gray-500 mt-3 mb-2">Affected pages (sample):</p>
          <div className="space-y-1">
            {issue.sample_urls?.slice(0, 5).map((url: string) => (
              <a key={url} href={url} target="_blank" rel="noopener"
                className="block text-xs text-blue-600 hover:underline truncate">{url}</a>
            ))}
          </div>
          {issue.example_fix && (
            <div className="mt-3 bg-white border rounded p-3">
              <p className="text-xs text-gray-500 mb-1">Example fix:</p>
              <p className="text-sm">{issue.example_fix}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## 11. FRONTEND: SCORE TREND CHART

Users need to see their score over time to feel progress.

```tsx
// apps/web/src/components/ScoreTrendChart.tsx — NEW COMPONENT

import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { format } from "date-fns";

interface CrawlSummary {
  id: string;
  completed_at: string;
  seo_score: number;
  issues_found: number;
  pages_crawled: number;
  trigger: string;
}

export function ScoreTrendChart({ siteId }: { siteId: string }) {
  const { data: crawls } = useQuery<CrawlSummary[]>({
    queryKey: ["crawls-history", siteId],
    queryFn: () => fetch(`/api/crawls?site_id=${siteId}&limit=20`).then(r => r.json()),
  });

  const chartData = crawls
    ?.filter(c => c.seo_score !== null)
    .map(c => ({
      date: format(new Date(c.completed_at), "MMM d"),
      score: c.seo_score,
      issues: c.issues_found,
      id: c.id,
    }))
    .reverse() || [];

  if (chartData.length < 2) {
    return (
      <div className="h-48 flex items-center justify-center bg-gray-50 rounded-lg">
        <p className="text-gray-400 text-sm">Run at least 2 crawls to see the trend</p>
      </div>
    );
  }

  const latest = chartData[chartData.length - 1];
  const previous = chartData[chartData.length - 2];
  const change = latest.score - previous.score;

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between">
        <div>
          <span className="text-4xl font-bold text-gray-900">{latest.score}</span>
          <span className="text-gray-400 ml-1">/100</span>
        </div>
        <div className={`flex items-center gap-1 text-sm font-medium ${change > 0 ? "text-green-600" : change < 0 ? "text-red-500" : "text-gray-400"}`}>
          {change > 0 ? "↑" : change < 0 ? "↓" : "→"} {Math.abs(change)} pts vs last crawl
        </div>
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#9ca3af" }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#9ca3af" }} />
          <Tooltip
            contentStyle={{ borderRadius: "8px", border: "1px solid #e5e7eb", fontSize: "12px" }}
            formatter={(value: any) => [`${value}/100`, "SEO Score"]}
          />
          <ReferenceLine y={80} stroke="#22c55e" strokeDasharray="3 3" label={{ value: "Good", position: "right", fontSize: 10 }} />
          <ReferenceLine y={50} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "Fair", position: "right", fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ fill: "#6366f1", r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## 12. INDEXNOW INTEGRATION

After applying a fix, notify search engines immediately instead of waiting days.

```python
# packages/integrations/indexnow.py — NEW FILE

import httpx
import structlog

logger = structlog.get_logger()

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"


async def notify_indexnow(urls: list[str], site_domain: str, api_key: str) -> bool:
    """
    Notify IndexNow protocol that URLs have been updated.
    Bing indexes within hours. Google is slower but does honor it.
    Cost: free, instant.
    """
    if not urls or not api_key:
        return False

    # Deduplicate and limit to 10,000 per call
    unique_urls = list(set(urls))[:10000]

    payload = {
        "host": site_domain.replace("https://", "").replace("http://", "").rstrip("/"),
        "key": api_key,
        "urlList": unique_urls,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(INDEXNOW_ENDPOINT, json=payload)

            if resp.status_code in (200, 202):
                logger.info("indexnow_notified",
                           domain=site_domain, url_count=len(unique_urls))
                return True
            else:
                logger.warning("indexnow_failed",
                              domain=site_domain, status=resp.status_code)
                return False

    except Exception as e:
        logger.error("indexnow_error", domain=site_domain, error=str(e))
        return False


# workers/tasks/fix.py — ADD after successful fix application:

# After fix is verified as applied:
async def _notify_after_fix(issue, site):
    """Notify IndexNow after a fix is applied to a page."""
    if site.indexnow_key:
        from packages.integrations.indexnow import notify_indexnow
        await notify_indexnow(
            urls=[issue.page_url],
            site_domain=site.domain,
            api_key=site.indexnow_key,
        )
```

---

## 13. TRUE SIMHASH + LSH DUPLICATE DETECTION

Current catches ~80% (exact normalized text). This catches near-duplicates (product pages, paginated archives).

```python
# packages/crawler/simhash.py — NEW FILE (replaces inline simhash in extractor)

import hashlib
import struct
from typing import Optional


def compute_simhash(text: str, hash_bits: int = 64) -> int:
    """
    Compute SimHash fingerprint for a text.
    Similar texts produce similar hashes (small Hamming distance).
    """
    tokens = _tokenize(text)
    if not tokens:
        return 0

    vector = [0] * hash_bits

    for token in tokens:
        # Hash each token with weight 1
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(hash_bits):
            if h & (1 << i):
                vector[i] += 1
            else:
                vector[i] -= 1

    # Build fingerprint
    fingerprint = 0
    for i in range(hash_bits):
        if vector[i] >= 0:
            fingerprint |= (1 << i)

    return fingerprint


def hamming_distance(h1: int, h2: int) -> int:
    """Count differing bits between two hashes."""
    return bin(h1 ^ h2).count("1")


def is_near_duplicate(h1: int, h2: int, threshold: int = 4) -> bool:
    """Two hashes with Hamming distance <= threshold are near-duplicates."""
    return hamming_distance(h1, h2) <= threshold


def _tokenize(text: str) -> list[str]:
    """Tokenize text into shingles for more accurate fingerprinting."""
    import re
    # Remove HTML remnants, normalize
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text.lower().strip())

    words = text.split()
    if len(words) < 3:
        return words

    # Use 3-shingles (3-word n-grams) for better accuracy than unigrams
    shingles = []
    for i in range(len(words) - 2):
        shingles.append(f"{words[i]} {words[i+1]} {words[i+2]}")

    return shingles


class LSHDuplicateDetector:
    """
    Locality-Sensitive Hashing for O(n) near-duplicate detection.
    Much faster than O(n²) pairwise comparison.

    Algorithm:
    1. Split 64-bit SimHash into 8 bands of 8 bits each
    2. Pages with matching bands go into the same bucket
    3. Only compare pages in the same bucket
    4. This reduces comparisons from n² to ~n*k where k=avg bucket size
    """

    BANDS = 8      # Number of hash bands
    ROWS = 8       # Bits per band (8 bands × 8 bits = 64 bits total)

    def __init__(self):
        self.buckets: dict[tuple, list[str]] = {}  # band_key → [page_urls]
        self.hashes: dict[str, int] = {}            # url → hash

    def add_page(self, url: str, content_hash: str):
        """Add a page to the LSH index."""
        if not content_hash:
            return
        h = int(content_hash, 16)
        self.hashes[url] = h

        # Add to band buckets
        for band in range(self.BANDS):
            start_bit = band * self.ROWS
            band_value = (h >> start_bit) & ((1 << self.ROWS) - 1)
            bucket_key = (band, band_value)
            if bucket_key not in self.buckets:
                self.buckets[bucket_key] = []
            self.buckets[bucket_key].append(url)

    def find_duplicates(self, threshold: int = 4) -> list[tuple[str, str, int]]:
        """
        Find all near-duplicate pairs.
        Returns: [(url_a, url_b, hamming_distance), ...]
        """
        candidates = set()  # Avoid comparing the same pair twice

        for bucket_urls in self.buckets.values():
            if len(bucket_urls) < 2:
                continue
            # Compare all pairs in this bucket
            for i in range(len(bucket_urls)):
                for j in range(i + 1, len(bucket_urls)):
                    pair = (min(bucket_urls[i], bucket_urls[j]),
                            max(bucket_urls[i], bucket_urls[j]))
                    candidates.add(pair)

        duplicates = []
        for url_a, url_b in candidates:
            h1 = self.hashes.get(url_a, 0)
            h2 = self.hashes.get(url_b, 0)
            dist = hamming_distance(h1, h2)
            if dist <= threshold:
                duplicates.append((url_a, url_b, dist))

        return sorted(duplicates, key=lambda x: x[2])  # Sort by similarity


# packages/crawler/analyzer.py — REPLACE detect_duplicates()

def detect_duplicates(pages: list[dict]) -> list[dict]:
    """
    O(n log n) near-duplicate detection using LSH.
    Replaces the O(n²) pairwise comparison.
    """
    from packages.crawler.simhash import LSHDuplicateDetector

    detector = LSHDuplicateDetector()

    # Build index
    for page in pages:
        if page.get("content_hash"):
            detector.add_page(page["url"], page["content_hash"])

    # Find duplicates
    duplicate_pairs = detector.find_duplicates(threshold=4)

    # Build URL → duplicate map
    dup_map = {}
    for url_a, url_b, distance in duplicate_pairs:
        # Mark the one with lower incoming links as the duplicate
        # (the more-linked page is canonical)
        dup_map[url_a] = url_b
        dup_map[url_b] = url_a

    # Apply to pages
    for page in pages:
        if page["url"] in dup_map:
            page["is_duplicate_of"] = dup_map[page["url"]]
            page["duplicate_hamming_distance"] = next(
                (d for a, b, d in duplicate_pairs
                 if a == page["url"] or b == page["url"]), None
            )

    return pages
```

---

## 14. CMS TOKEN AUTO-ROTATION

WordPress/Shopify tokens expire. Silent failures destroy client trust.

```python
# workers/tasks/token_health.py — NEW FILE

from celery import shared_task
import asyncio
import structlog
from datetime import datetime, timezone, timedelta

logger = structlog.get_logger()


@shared_task
def check_expiring_tokens():
    """
    Run daily. Check all CMS and GSC tokens for expiry.
    Send alerts for tokens expiring in < 7 days.
    """
    asyncio.run(_async_check_tokens())


async def _async_check_tokens():
    now = datetime.now(timezone.utc)
    warning_threshold = now + timedelta(days=7)

    sites = await db.get_all_connected_sites()

    for site in sites:
        issues = []

        # Check GSC token
        if site.gsc_connected and site.gsc_token_expires_at:
            if site.gsc_token_expires_at < now:
                issues.append(("gsc", "expired"))
            elif site.gsc_token_expires_at < warning_threshold:
                issues.append(("gsc", "expiring_soon"))

        # Check CMS token expiry
        if site.cms_token_expires_at:
            if site.cms_token_expires_at < now:
                issues.append(("cms", "expired"))
            elif site.cms_token_expires_at < warning_threshold:
                issues.append(("cms", "expiring_soon"))

        # Try to auto-refresh GSC (it has refresh tokens)
        if any(t == "gsc" for t, _ in issues):
            try:
                await _refresh_gsc_token(site)
                issues = [(t, s) for t, s in issues if t != "gsc"]
                logger.info("gsc_token_refreshed", site_id=str(site.id))
            except Exception as e:
                logger.error("gsc_token_refresh_failed", site_id=str(site.id), error=str(e))

        # Send alerts for unresolvable issues
        if issues:
            org_users = await db.get_org_users(str(site.org_id))
            for token_type, status in issues:
                for user in org_users[:1]:  # Only notify owner
                    await _send_token_alert(
                        user.email, site, token_type, status
                    )


async def _refresh_gsc_token(site) -> None:
    """Attempt to refresh GSC access token using refresh token."""
    from packages.integrations.gsc import GSCClient
    client = GSCClient(site, settings)
    await client.get_access_token()  # This internally refreshes if needed


async def _send_token_alert(email: str, site, token_type: str, status: str):
    """Send token expiry warning email."""
    import resend
    resend.api_key = settings.RESEND_API_KEY

    type_names = {"gsc": "Google Search Console", "cms": "CMS (WordPress/Shopify)"}
    type_name = type_names.get(token_type, token_type)

    subject = f"⚠️ {site.name}: {type_name} connection needs attention"
    html = f"""
    <p>Your <strong>{type_name}</strong> connection for <strong>{site.name}</strong>
    has {'expired' if status == 'expired' else 'less than 7 days left before expiry'}.</p>
    <p>AutoSEO cannot access your site's data until you reconnect.</p>
    <a href="{settings.FRONTEND_URL}/sites/{site.id}/settings"
       style="background:#6366f1;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;">
      Reconnect Now →
    </a>
    """

    resend.Emails.send({
        "from": f"AutoSEO <alerts@{settings.EMAIL_DOMAIN}>",
        "to": email,
        "subject": subject,
        "html": html,
    })


# Add to celery_app.py beat_schedule:
# "check-expiring-tokens": {
#     "task": "workers.tasks.token_health.check_expiring_tokens",
#     "schedule": crontab(hour=8, minute=0),  # 8 AM daily
# },
```

---

## 15. WEBFLOW CMS READER

Listed as supported but code is `pass`. Agencies use Webflow heavily.

```python
# packages/crawler/layers/cms_layer.py — ADD read_webflow() METHOD

async def read_webflow(self, site) -> list[dict]:
    """
    Read pages from Webflow CMS API v2.
    Webflow API: https://developers.webflow.com/reference
    """
    token = decrypt_credential(
        str(site.org_id),
        site.cms_token_encrypted,
        site.cms_token_iv or ""
    )
    site_id_webflow = site.cms_endpoint  # Webflow Site ID

    pages = []
    async with httpx.AsyncClient(
        timeout=30,
        headers={
            "Authorization": f"Bearer {token}",
            "accept-version": "2.0.0",
        }
    ) as client:
        # Fetch all pages
        resp = await client.get(f"https://api.webflow.com/v2/sites/{site_id_webflow}/pages")
        if resp.status_code != 200:
            logger.warning("webflow_pages_failed", status=resp.status_code)
        else:
            for page in resp.json().get("pages", []):
                # Get page SEO metadata
                pages.append({
                    "url": f"https://{site.domain}{page.get('slug', '')}",
                    "title": page.get("seo", {}).get("title") or page.get("title", ""),
                    "meta_description": page.get("seo", {}).get("description", ""),
                    "source": "webflow_api",
                    "cms_id": page.get("id"),
                    "slug": page.get("slug"),
                    "is_draft": page.get("draft", False),
                    "last_published": page.get("lastPublished"),
                })

        # Fetch CMS collections (blog posts, products, etc.)
        collections_resp = await client.get(
            f"https://api.webflow.com/v2/sites/{site_id_webflow}/collections"
        )
        if collections_resp.status_code == 200:
            for collection in collections_resp.json().get("collections", []):
                coll_id = collection["id"]
                coll_slug = collection.get("slug", "items")

                # Fetch items with pagination
                offset = 0
                while True:
                    items_resp = await client.get(
                        f"https://api.webflow.com/v2/collections/{coll_id}/items",
                        params={"offset": offset, "limit": 100}
                    )
                    if items_resp.status_code != 200:
                        break
                    data = items_resp.json()
                    items = data.get("items", [])

                    for item in items:
                        if item.get("archived") or item.get("draft"):
                            continue
                        field_data = item.get("fieldData", {})
                        pages.append({
                            "url": f"https://{site.domain}/{coll_slug}/{field_data.get('slug', item['id'])}",
                            "title": field_data.get("name", field_data.get("title", "")),
                            "meta_description": field_data.get("meta-description", field_data.get("description", ""))[:200],
                            "content": str(field_data.get("content", field_data.get("body", "")))[:5000],
                            "source": "webflow_api",
                            "cms_id": item["id"],
                            "collection": collection.get("name"),
                        })

                    total = data.get("pagination", {}).get("total", 0)
                    offset += len(items)
                    if offset >= total or not items:
                        break

    logger.info("webflow_read_complete",
                site_id=str(site.id), pages=len(pages))
    return pages
```

---

## 16. CONTENT FRESHNESS DETECTION

Stale content hurts rankings. Google's freshness algorithm rewards updated content.

```python
# packages/crawler/extractor.py — ADD to extract_all()

def _detect_content_freshness(self) -> dict:
    """
    Detect when a page was last updated and flag stale content.
    Sources: <time> tags, schema dateModified, meta article:modified_time, lastmod in sitemap.
    """
    from datetime import datetime, timezone
    import dateutil.parser

    today = datetime.now(timezone.utc)
    last_modified = None

    # Check various date signals
    # 1. Schema.org dateModified
    for script in self.soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for item in items:
                if isinstance(item, dict) and item.get("dateModified"):
                    try:
                        last_modified = dateutil.parser.parse(item["dateModified"]).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        pass
        except Exception:
            pass

    # 2. article:modified_time meta tag
    if not last_modified:
        meta_modified = self.soup.find("meta", attrs={"property": "article:modified_time"})
        if meta_modified and meta_modified.get("content"):
            try:
                last_modified = dateutil.parser.parse(meta_modified["content"]).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

    # 3. <time> tag with datetime attribute
    if not last_modified:
        time_tags = self.soup.find_all("time", datetime=True)
        for tag in time_tags:
            try:
                dt = dateutil.parser.parse(tag["datetime"]).replace(tzinfo=timezone.utc)
                if last_modified is None or dt > last_modified:
                    last_modified = dt
            except (ValueError, KeyError):
                pass

    days_since = None
    if last_modified:
        days_since = (today - last_modified).days

    return {
        "last_modified_date": last_modified,
        "days_since_modified": days_since,
    }


# packages/crawler/issue_generator.py — ADD content freshness check

def _check_freshness(self, page) -> list[Issue]:
    issues = []
    days_since = page.get("days_since_modified")
    page_type = page.get("page_type", "generic")

    if days_since is None:
        return issues  # Can't detect, skip

    # Don't flag utility pages (contact, about, etc.) for staleness
    if page_type in ("utility", "homepage"):
        return issues

    STALE_THRESHOLDS = {
        "article": 365,    # Blog posts stale after 1 year
        "product": 180,    # Product pages stale after 6 months
        "generic": 730,    # Generic pages stale after 2 years
        "faq": 365,
    }
    threshold = STALE_THRESHOLDS.get(page_type, 730)

    if days_since > threshold:
        issues.append(Issue(
            page_url=page["url"],
            type="stale_content",
            category="content",
            severity=self.MEDIUM,
            impact_score=35,
            current_value=f"Last updated {days_since} days ago (threshold: {threshold} days for {page_type} pages)",
            fix_type="manual",
            proposed_fix_metadata={
                "last_modified": str(page.get("last_modified_date", "unknown")),
                "days_stale": days_since - threshold,
                "recommendation": "Review and update this content to keep it fresh",
            }
        ))

    return issues
```

---

## 17. GOOGLE PAGESPEED INSIGHTS API

Get real Google Lighthouse scores, not approximations.

```python
# packages/integrations/pagespeed.py — NEW FILE

import httpx
import structlog
from typing import Optional

logger = structlog.get_logger()

PSI_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


async def run_pagespeed(
    url: str,
    api_key: str,
    strategy: str = "mobile"
) -> Optional[dict]:
    """
    Run Google PageSpeed Insights for a URL.
    Returns Lighthouse scores and Core Web Vitals.
    Free: 25,000 queries/day per API key.
    """
    params = {
        "url": url,
        "strategy": strategy,  # mobile | desktop
        "key": api_key,
        "category": ["performance", "seo", "best-practices", "accessibility"],
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(PSI_API_URL, params=params)

            if resp.status_code != 200:
                logger.warning("pagespeed_api_failed", url=url, status=resp.status_code)
                return None

            data = resp.json()
            lr = data.get("lighthouseResult", {})
            cats = lr.get("categories", {})
            audits = lr.get("audits", {})

            return {
                # Category scores (0-100)
                "performance_score": int((cats.get("performance", {}).get("score", 0) or 0) * 100),
                "seo_score": int((cats.get("seo", {}).get("score", 0) or 0) * 100),
                "accessibility_score": int((cats.get("accessibility", {}).get("score", 0) or 0) * 100),
                "best_practices_score": int((cats.get("best-practices", {}).get("score", 0) or 0) * 100),
                # Core Web Vitals
                "lcp_ms": audits.get("largest-contentful-paint", {}).get("numericValue"),
                "fcp_ms": audits.get("first-contentful-paint", {}).get("numericValue"),
                "cls": audits.get("cumulative-layout-shift", {}).get("numericValue"),
                "tbt_ms": audits.get("total-blocking-time", {}).get("numericValue"),
                "speed_index": audits.get("speed-index", {}).get("numericValue"),
                "ttfb_ms": audits.get("server-response-time", {}).get("numericValue"),
                # Strategy used
                "strategy": strategy,
                # Opportunities (top 3 performance improvements)
                "opportunities": [
                    {
                        "id": audit_id,
                        "title": audit.get("title", ""),
                        "description": audit.get("description", "")[:200],
                        "savings_ms": audit.get("details", {}).get("overallSavingsMs", 0),
                    }
                    for audit_id, audit in audits.items()
                    if audit.get("details", {}).get("type") == "opportunity"
                    and audit.get("score", 1) < 0.9
                ][:5],
            }

    except Exception as e:
        logger.error("pagespeed_error", url=url, error=str(e))
        return None


# workers/tasks/crawl.py — ADD pagespeed sampling after crawl

async def _run_pagespeed_sample(crawl_id: str, site_id: str, pages: list[dict]):
    """
    Run PageSpeed on a sample of important pages after crawl.
    Sample: homepage + up to 4 highest-traffic pages from GSC.
    """
    if not settings.GOOGLE_API_KEY:
        return

    from packages.integrations.pagespeed import run_pagespeed

    # Always test homepage
    site = await db.get_site(site_id)
    urls_to_test = [site.domain]

    # Add top pages from GSC if available
    gsc_top = await db.get_top_gsc_pages(site_id, limit=4)
    urls_to_test.extend([p.page_url for p in gsc_top])

    sampled = 0
    for url in urls_to_test[:5]:
        result = await run_pagespeed(url, settings.GOOGLE_API_KEY, "mobile")
        if result:
            # Update the page record with PSI data
            await db.update_page_pagespeed(
                crawl_id=crawl_id,
                url=url,
                pagespeed_score=result["performance_score"],
                pagespeed_lcp_ms=result.get("lcp_ms"),
                pagespeed_cls=result.get("cls"),
            )
            sampled += 1

    await db.update_crawl(crawl_id, pagespeed_sampled=sampled)
    logger.info("pagespeed_sampling_done", crawl_id=crawl_id, sampled=sampled)
```

---

## 18. WHITE-LABEL FOUNDATION

Agencies are your biggest customers. Give them enough to resell.

```python
# packages/shared/white_label.py — NEW FILE

async def get_branding(org_id: str) -> dict:
    """
    Get white-label branding for an organization.
    Used in emails, PDFs, and API responses.
    """
    org = await db.get_org(org_id)
    if not org:
        return _default_branding()

    if org.white_label and org.brand_name:
        return {
            "name": org.brand_name,
            "logo_url": org.brand_logo_url or "",
            "primary_color": org.brand_primary_color or "#6366f1",
            "email_domain": f"@{org.custom_domain}" if org.custom_domain else settings.EMAIL_DOMAIN,
            "app_url": f"https://{org.custom_domain}" if org.custom_domain else settings.FRONTEND_URL,
            "is_white_label": True,
        }

    return _default_branding()


def _default_branding() -> dict:
    return {
        "name": "AutoSEO",
        "logo_url": f"{settings.CDN_URL}/logo.png",
        "primary_color": "#6366f1",
        "email_domain": settings.EMAIL_DOMAIN,
        "app_url": settings.FRONTEND_URL,
        "is_white_label": False,
    }


# apps/api/routers/organizations.py — ADD white-label settings endpoint

@router.patch("/settings/white-label")
async def update_white_label(
    body: WhiteLabelSettingsRequest,
    user=Depends(get_current_user_admin)  # Admin only
):
    """Update white-label settings. Agency plan only."""
    org = await db.get_org(str(user.org_id))
    if org.plan != "agency":
        raise HTTPException(403, "White-label requires Agency plan")

    await db.update_org(str(user.org_id), {
        "white_label": body.enabled,
        "brand_name": body.brand_name,
        "brand_logo_url": body.logo_url,
        "brand_primary_color": body.primary_color,
        "custom_domain": body.custom_domain,
    })

    return {"status": "ok"}
```

---

## 19. COMPLETE BACKEND ENDPOINT MANIFEST

All API endpoints that need to exist. Check each one off.

```python
# apps/api/routers/__init__.py — COMPLETE ROUTER MANIFEST

# ── AUTH ─────────────────────────────────────────────────
# POST /auth/signup
# POST /auth/login
# POST /auth/logout
# GET  /auth/me
# POST /auth/refresh

# ── SITES ────────────────────────────────────────────────
# GET    /sites              (list org's sites)
# POST   /sites              (add site)
# GET    /sites/{id}         (get site + latest crawl summary)
# PATCH  /sites/{id}         (update site settings)
# DELETE /sites/{id}         (remove site)
# PATCH  /sites/{id}/schedule (set crawl frequency)
# POST   /sites/{id}/crawl   (trigger manual crawl)
# GET    /sites/{id}/score-trend (last 20 crawl scores)

# ── CRAWLS ───────────────────────────────────────────────
# GET  /crawls?site_id=&limit= (list crawls)
# GET  /crawls/{id}            (single crawl + stats)
# DELETE /crawls/{id}          (cancel running crawl)
# GET  /crawls/{id}/diff       (compare to previous crawl) ✅ DONE
# GET  /crawls/{id}/progress   (SSE stream)

# ── PAGES ────────────────────────────────────────────────
# GET  /pages?crawl_id=&page=&per_page= (paginated pages)
# GET  /pages/{id}                      (single page detail)

# ── ISSUES ───────────────────────────────────────────────
# GET  /issues?site_id=&severity=&fix_type=&page= (paginated issues)
# GET  /issues/aggregated?site_id=                (grouped by type) ✅ DONE
# GET  /issues/{id}

# ── FIXES ────────────────────────────────────────────────
# POST /fixes/{issue_id}/apply       (apply a fix)
# POST /fixes/{issue_id}/reject      (reject AI fix, request new)
# POST /fixes/{issue_id}/rollback    (undo applied fix)
# POST /fixes/bulk-apply             (apply fix type to all affected pages)
# GET  /fixes/{issue_id}/versions    (fix attempt history)

# ── SNIPPET ─────────────────────────────────────────────
# POST /snippet/collect (PUBLIC — no auth, rate limited)
# GET  /snippet/install-code?site_id= (get embed code for site)

# ── GSC ─────────────────────────────────────────────────
# GET  /gsc/auth/url?site_id=         (get OAuth URL)
# GET  /gsc/auth/callback             (OAuth callback)
# GET  /gsc/properties?site_id=       (list GSC properties)
# POST /gsc/sync?site_id=             (trigger manual sync)
# GET  /gsc/data?site_id=&page_url=   (get GSC data for a page)

# ── ORGANIZATIONS ────────────────────────────────────────
# GET    /org                     (get current org)
# PATCH  /org                     (update org settings)
# GET    /org/members             (list members)
# POST   /org/invite              (invite member)
# DELETE /org/members/{user_id}   (remove member)
# PATCH  /org/settings/white-label

# ── REPORTS ─────────────────────────────────────────────
# POST /reports/generate?site_id=&crawl_id=  (generate PDF)
# GET  /reports/{id}                          (download PDF)

# ── WEBHOOKS ────────────────────────────────────────────
# POST /webhooks/stripe
# POST /webhooks/github

# ── HEALTH ──────────────────────────────────────────────
# GET  /health
# GET  /health/workers   (Celery worker status)
```

---

## 20. COMPLETE IMPLEMENTATION CHECKLIST

Execute in this exact order. Each item can be a separate PR.

```
WEEK 1 — SCORING + NEW ISSUE TYPES
[ ] Replace calculate_page_score() with additive model (Section 4)
[ ] Add _detect_spa_shell() to SEOExtractor
[ ] Add _detect_stale_schema_dates() to SEOExtractor
[ ] Add _detect_content_freshness() to SEOExtractor
[ ] Add spa_no_prerender issue type to IssueGenerator
[ ] Add stale_schema_date issue type to IssueGenerator
[ ] Add stale_content issue type to IssueGenerator
[ ] Add issue-specific Claude prompts for spa_no_prerender, stale_schema_date
[ ] Run migration 005_phase3_complete.sql
[ ] TEST: Crawl strategynavigator.ai → confirm 3 real issues detected correctly

WEEK 2 — FIX VERIFICATION + SIMHASH
[ ] Replace 5-second sleep with verify_fix_delayed Celery task (Section 5)
[ ] Implement LSHDuplicateDetector (Section 13)
[ ] Replace detect_duplicates() with LSH version
[ ] Add compute_simhash() and store as hex in pages.content_hash
[ ] TEST: Verify fix scheduling works (check Celery beat logs)
[ ] TEST: Run LSH on site with product pages — confirm near-duplicates found

WEEK 3 — SCHEDULED CRAWLS + EMAIL DIGEST
[ ] Add trigger_scheduled_crawls Celery beat task (Section 7)
[ ] Add check_expiring_tokens Celery beat task (Section 14)
[ ] Add send_weekly_digests Celery beat task (Section 8)
[ ] Add PATCH /sites/{id}/schedule endpoint
[ ] TEST: Set crawl to 'daily', advance clock, verify crawl triggers
[ ] TEST: Send test digest email manually

WEEK 4 — GSC INTEGRATION
[ ] Create Google Cloud project + enable Search Console API
[ ] Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET to Doppler
[ ] Implement GSCClient class (Section 6)
[ ] Add /gsc/* router to FastAPI
[ ] Implement sync_gsc_data Celery task
[ ] Implement _generate_gsc_insights() — creates low_ctr_high_impressions issues
[ ] Add gsc_data table via migration
[ ] TEST: Connect GSC for strategynavigator.ai → sync 90 days → see GSC insights

WEEK 5 — FRONTEND DIFF UI + AGGREGATION UI
[ ] Add CrawlDiff.tsx component (Section 9)
[ ] Add AggregatedIssues.tsx component (Section 10)
[ ] Add ScoreTrendChart.tsx component (Section 11)
[ ] Wire CrawlDiff into the crawl results page (new "What Changed" tab)
[ ] Replace flat issues list with AggregatedIssues on main issues page
[ ] Add score trend chart to site dashboard
[ ] TEST: Verify all 3 components render correctly with real data

WEEK 6 — WEBFLOW + PAGESPEED + INDEXNOW
[ ] Add read_webflow() to CMSReader (Section 15)
[ ] Add read_github_pages() stub (or full implementation)
[ ] Implement run_pagespeed() (Section 17)
[ ] Add _run_pagespeed_sample() to crawl orchestrator
[ ] Implement notify_indexnow() (Section 12)
[ ] Wire IndexNow notification into fix.py after successful apply
[ ] TEST: Connect a Webflow test site → crawl → confirm pages fetched via API

WEEK 7 — WHITE-LABEL + POLISH
[ ] Add white-label settings to organizations table
[ ] Add white_label.py shared package (Section 18)
[ ] Thread branding through email templates (digest, alerts, fix notifications)
[ ] Add PATCH /org/settings/white-label endpoint
[ ] Add white-label settings UI to agency plan settings page
[ ] TEST: Set custom brand name → send test digest → verify branding appears

WEEK 8 — QUALITY + HARDENING
[ ] Add 30 unit tests for all new issue types
[ ] Add integration test: full crawl → SPA detection → stale schema → GSC insights
[ ] Load test: crawl 1000-page site with 10 concurrent users
[ ] Verify Redis connection pool under load (check connection count)
[ ] Verify SSE doesn't poll DB (verify Redis pub/sub is used)
[ ] Review all API endpoints for missing auth guards
[ ] GDPR: test data export endpoint, test data deletion endpoint
[ ] Deploy to production, monitor Sentry for 24h
```

---

## APPENDIX A: ENVIRONMENT VARIABLES (COMPLETE LIST)

```bash
# Core
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx          # Backend only, NEVER frontend
SUPABASE_ANON_KEY=xxx                  # Safe for frontend
DATABASE_URL=postgresql+asyncpg://...  # Direct DB URL for SQLAlchemy

# AI
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-sonnet-4-6      # CORRECT model string as of April 2026

# Crawling
JINA_API_KEY=xxx                       # Optional, 100 RPM vs 20 RPM free
SCRAPFLY_API_KEY=scp-xxx

# Google
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_API_KEY=xxx                     # For PageSpeed Insights API

# Infra
REDIS_URL=redis://xxx.upstash.io       # Upstash Redis
FRONTEND_URL=https://app.autoseo.com
API_URL=https://api.autoseo.com
CDN_URL=https://cdn.autoseo.com

# External services
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
RESEND_API_KEY=re_xxx
EMAIL_DOMAIN=autoseo.com

# Storage
CLOUDFLARE_R2_ACCESS_KEY=xxx
CLOUDFLARE_R2_SECRET_KEY=xxx
CLOUDFLARE_R2_BUCKET=autoseo-storage
CLOUDFLARE_R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com

# Security
DOPPLER_MASTER_ENCRYPTION_KEY=64-char-hex  # AES-256 master key — NEVER commit
SENTRY_DSN=https://xxx@sentry.io/xxx

# GitHub App
GITHUB_APP_ID=xxx
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----...

# Feature Flags
PAGESPEED_ENABLED=true
INDEXNOW_ENABLED=true
WEEKLY_DIGEST_ENABLED=true
```

---

## APPENDIX B: REQUIREMENTS.TXT (COMPLETE)

```
# FastAPI + Async
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic==2.9.2
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.0
python-multipart==0.0.12

# Celery
celery[redis]==5.4.0
redis==5.2.0

# HTTP
httpx==0.28.1
aiohttp==3.11.10

# Crawling
crawl4ai==0.4.247          # Use latest stable
camoufox[geoip]==0.4.2
scrapfly-sdk==0.8.71

# HTML Parsing
beautifulsoup4==4.12.3
lxml==5.3.0

# AI
anthropic==0.40.0

# Auth
python-jose[cryptography]==3.3.0
cryptography==44.0.0
passlib[bcrypt]==1.7.4

# External APIs
stripe==11.4.0
resend==2.5.0
python-dateutil==2.9.0

# Hashing / Similarity
xxhash==3.5.0
numpy==2.2.0                # For SimHash vector math

# Logging / Observability
structlog==24.4.0
sentry-sdk[fastapi]==2.19.2

# Dev / Testing
pytest==8.3.4
pytest-asyncio==0.24.0
httpx[testing]==0.28.1
factory-boy==3.3.1
```

---

## APPENDIX C: DOCKER COMPOSE (LOCAL DEV)

```yaml
# infra/docker-compose.yml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: infra/Dockerfile.api
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379/0
    env_file: .env.local
    depends_on: [redis, postgres]
    volumes:
      - .:/app
    command: uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: .
      dockerfile: infra/Dockerfile.worker
    environment:
      - REDIS_URL=redis://redis:6379/0
    env_file: .env.local
    depends_on: [redis, postgres]
    command: celery -A workers.celery_app worker --loglevel=info --concurrency=2

  beat:
    build:
      context: .
      dockerfile: infra/Dockerfile.worker
    environment:
      - REDIS_URL=redis://redis:6379/0
    env_file: .env.local
    depends_on: [redis]
    command: celery -A workers.celery_app beat --loglevel=info

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

  postgres:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: autoseo
      POSTGRES_USER: autoseo
      POSTGRES_PASSWORD: autoseo_dev
    volumes:
      - pgdata:/var/lib/postgresql/data

  flower:
    image: mher/flower
    ports: ["5555:5555"]
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on: [redis]

volumes:
  pgdata:
```

---

## APPENDIX D: CELERY APP (FINAL WITH ALL TASKS)

```python
# workers/celery_app.py — FINAL VERSION

from celery import Celery
from celery.schedules import crontab
from workers.config import settings

app = Celery(
    "autoseo",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.tasks.crawl",
        "workers.tasks.ai_analysis",
        "workers.tasks.fix",
        "workers.tasks.fix_verification",
        "workers.tasks.gsc_sync",
        "workers.tasks.scheduled",
        "workers.tasks.digest",
        "workers.tasks.token_health",
        "workers.tasks.report",
    ]
)

app.conf.update(
    task_serializer="json",
    result_expires=3600,
    worker_max_tasks_per_child=50,    # Prevent browser memory leaks
    task_soft_time_limit=1800,        # 30 min warning
    task_time_limit=3600,             # 1 hour hard kill
    worker_prefetch_multiplier=1,     # Don't prefetch — crawl tasks are heavy
    task_acks_late=True,              # ACK after task completes, not when received
    worker_send_task_events=True,     # Enable Flower monitoring
    task_send_sent_event=True,
)

app.conf.beat_schedule = {
    # Scheduled crawls — check every hour
    "trigger-scheduled-crawls": {
        "task": "workers.tasks.scheduled.trigger_scheduled_crawls",
        "schedule": crontab(minute=0),
    },
    # Weekly email digest — Monday 9 AM UTC
    "send-weekly-digests": {
        "task": "workers.tasks.digest.send_weekly_digests",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
    },
    # Token health check — daily 8 AM UTC
    "check-expiring-tokens": {
        "task": "workers.tasks.token_health.check_expiring_tokens",
        "schedule": crontab(hour=8, minute=0),
    },
    # GSC sync for all connected sites — daily 3 AM UTC
    "sync-all-gsc": {
        "task": "workers.tasks.gsc_sync.sync_all_gsc_sites",
        "schedule": crontab(hour=3, minute=0),
    },
}
```

---

*Plan version 5.0 — April 2026 — Complete and definitive.*
*Sources: v2/v3/v4 plans, gap analysis v1, PDF critical analysis, strategynavigator.ai real-world testing.*
