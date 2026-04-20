-- ============================================
-- AutoSEO Database Schema — Initial Migration
-- Version 1.0 — All tables, indexes, RLS, functions
-- ============================================

-- ORGANIZATIONS
CREATE TABLE IF NOT EXISTS organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'starter',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- USERS
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY,
    org_id      UUID REFERENCES organizations(id),
    role        TEXT NOT NULL DEFAULT 'member',
    email       TEXT NOT NULL,
    full_name   TEXT,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- SITES
CREATE TABLE IF NOT EXISTS sites (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID REFERENCES organizations(id) NOT NULL,
    name          TEXT NOT NULL,
    domain        TEXT NOT NULL,
    connection_type TEXT NOT NULL DEFAULT 'crawler',
    cms_token_encrypted TEXT,
    cms_token_iv  TEXT,
    cms_endpoint  TEXT,
    github_installation_id BIGINT,
    github_repo   TEXT,
    github_branch TEXT DEFAULT 'main',
    snippet_token UUID DEFAULT gen_random_uuid(),
    gsc_property_url TEXT,
    gsc_token_encrypted TEXT,
    crawl_frequency TEXT DEFAULT 'weekly',
    crawl_max_pages INTEGER DEFAULT 500,
    respect_robots_txt BOOLEAN DEFAULT true,
    crawl_delay_ms INTEGER DEFAULT 1000,
    status        TEXT DEFAULT 'pending',
    last_crawled_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- CRAWLS
CREATE TABLE IF NOT EXISTS crawls (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id       UUID REFERENCES sites(id) NOT NULL,
    org_id        UUID REFERENCES organizations(id) NOT NULL,
    status        TEXT DEFAULT 'queued',
    trigger       TEXT DEFAULT 'scheduled',
    pages_crawled INTEGER DEFAULT 0,
    pages_total   INTEGER,
    issues_found  INTEGER DEFAULT 0,
    seo_score     SMALLINT,
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    duration_ms   INTEGER,
    error_message TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- PAGES
CREATE TABLE IF NOT EXISTS pages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crawl_id      UUID REFERENCES crawls(id) NOT NULL,
    site_id       UUID REFERENCES sites(id) NOT NULL,
    org_id        UUID REFERENCES organizations(id) NOT NULL,
    url           TEXT NOT NULL,
    status_code   SMALLINT,
    redirect_url  TEXT,
    redirect_chain JSONB,
    crawl_depth   SMALLINT,
    response_time_ms INTEGER,
    title         TEXT,
    title_length  SMALLINT,
    meta_description TEXT,
    meta_description_length SMALLINT,
    canonical_url TEXT,
    canonical_chain JSONB,
    robots_directive TEXT,
    h1_count      SMALLINT,
    h1_text       TEXT[],
    h2_count      SMALLINT,
    h3_count      SMALLINT,
    heading_structure JSONB,
    word_count    INTEGER,
    content_hash  TEXT,
    internal_links_count INTEGER,
    external_links_count INTEGER,
    broken_links_count INTEGER,
    incoming_links_count INTEGER,
    images_count  INTEGER,
    images_missing_alt INTEGER,
    images_large  INTEGER,
    og_title      TEXT,
    og_description TEXT,
    og_image      TEXT,
    twitter_card  TEXT,
    schema_types  TEXT[],
    schema_valid  BOOLEAN,
    schema_errors JSONB,
    lcp_ms        INTEGER,
    fid_ms        INTEGER,
    cls_score     NUMERIC(4,3),
    ttfb_ms       INTEGER,
    performance_score SMALLINT,
    hreflang_tags JSONB,
    hreflang_errors TEXT[],
    seo_score     SMALLINT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ISSUES
CREATE TABLE IF NOT EXISTS issues (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crawl_id      UUID REFERENCES crawls(id) NOT NULL,
    site_id       UUID REFERENCES sites(id) NOT NULL,
    org_id        UUID REFERENCES organizations(id) NOT NULL,
    page_id       UUID REFERENCES pages(id),
    type          TEXT NOT NULL,
    category      TEXT NOT NULL,
    severity      TEXT NOT NULL,
    impact_score  SMALLINT NOT NULL,
    current_value TEXT,
    fix_type      TEXT NOT NULL DEFAULT 'manual',
    fix_status    TEXT DEFAULT 'pending',
    proposed_fix  TEXT,
    proposed_fix_metadata JSONB,
    ai_confidence NUMERIC(3,2),
    applied_at    TIMESTAMPTZ,
    applied_by    UUID REFERENCES users(id),
    verified_at   TIMESTAMPTZ,
    verified_score SMALLINT,
    rollback_value TEXT,
    rolled_back_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- CHANGE LOG (append-only audit trail)
CREATE TABLE IF NOT EXISTS change_log (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID REFERENCES organizations(id) NOT NULL,
    site_id       UUID REFERENCES sites(id) NOT NULL,
    issue_id      UUID REFERENCES issues(id),
    action        TEXT NOT NULL,
    actor_type    TEXT NOT NULL,
    actor_id      UUID,
    old_value     TEXT,
    new_value     TEXT,
    metadata      JSONB,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- JS SNIPPET EVENTS
CREATE TABLE IF NOT EXISTS snippet_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id       UUID REFERENCES sites(id) NOT NULL,
    org_id        UUID REFERENCES organizations(id) NOT NULL,
    page_url      TEXT NOT NULL,
    title         TEXT,
    meta_description TEXT,
    canonical_url TEXT,
    h1_text       TEXT,
    schema_json   TEXT,
    lcp_ms        INTEGER,
    cls_score     NUMERIC(4,3),
    ttfb_ms       INTEGER,
    user_agent    TEXT,
    viewport_width SMALLINT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- API KEYS
CREATE TABLE IF NOT EXISTS api_keys (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID REFERENCES organizations(id) NOT NULL,
    name          TEXT NOT NULL,
    key_hash      TEXT NOT NULL UNIQUE,
    key_prefix    TEXT NOT NULL,
    scopes        TEXT[] NOT NULL,
    last_used_at  TIMESTAMPTZ,
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_pages_crawl_id ON pages(crawl_id);
CREATE INDEX IF NOT EXISTS idx_pages_site_id ON pages(site_id);
CREATE INDEX IF NOT EXISTS idx_pages_org_id ON pages(org_id);
CREATE INDEX IF NOT EXISTS idx_issues_site_id ON issues(site_id);
CREATE INDEX IF NOT EXISTS idx_issues_org_id ON issues(org_id);
CREATE INDEX IF NOT EXISTS idx_issues_fix_status ON issues(fix_status);
CREATE INDEX IF NOT EXISTS idx_issues_site_status ON issues(site_id, fix_status);
CREATE INDEX IF NOT EXISTS idx_crawls_site_id ON crawls(site_id);
CREATE INDEX IF NOT EXISTS idx_crawls_org_id ON crawls(org_id);
CREATE INDEX IF NOT EXISTS idx_change_log_site_id ON change_log(site_id);
CREATE INDEX IF NOT EXISTS idx_snippet_events_site_id ON snippet_events(site_id, created_at DESC);
