ALTER TABLE sites
    ADD COLUMN IF NOT EXISTS next_scheduled_crawl TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS search_console_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    property_url TEXT NOT NULL,
    token_encrypted TEXT NOT NULL,
    token_iv TEXT NOT NULL,
    scopes TEXT[] NOT NULL,
    expires_at TIMESTAMPTZ,
    connected_by UUID REFERENCES users(id),
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS search_console_sync_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    connection_id UUID REFERENCES search_console_connections(id),
    status TEXT NOT NULL DEFAULT 'running',
    days INTEGER NOT NULL DEFAULT 90,
    pages_synced INTEGER NOT NULL DEFAULT 0,
    queries_synced INTEGER NOT NULL DEFAULT 0,
    inspections_synced INTEGER NOT NULL DEFAULT 0,
    sitemaps_synced INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS search_console_page_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    sync_run_id UUID REFERENCES search_console_sync_runs(id),
    page_url TEXT NOT NULL,
    date_start TEXT NOT NULL,
    date_end TEXT NOT NULL,
    device TEXT,
    country TEXT,
    clicks NUMERIC(12,2) NOT NULL DEFAULT 0,
    impressions NUMERIC(12,2) NOT NULL DEFAULT 0,
    ctr NUMERIC(8,6) NOT NULL DEFAULT 0,
    position NUMERIC(8,3) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS search_console_query_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    sync_run_id UUID REFERENCES search_console_sync_runs(id),
    page_url TEXT,
    query TEXT NOT NULL,
    date_start TEXT NOT NULL,
    date_end TEXT NOT NULL,
    device TEXT,
    country TEXT,
    clicks NUMERIC(12,2) NOT NULL DEFAULT 0,
    impressions NUMERIC(12,2) NOT NULL DEFAULT 0,
    ctr NUMERIC(8,6) NOT NULL DEFAULT 0,
    position NUMERIC(8,3) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS search_console_inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    sync_run_id UUID REFERENCES search_console_sync_runs(id),
    url TEXT NOT NULL,
    verdict TEXT,
    coverage_state TEXT,
    indexing_state TEXT,
    robots_txt_state TEXT,
    page_fetch_state TEXT,
    last_crawl_time TEXT,
    google_canonical TEXT,
    user_canonical TEXT,
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS search_console_sitemaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    sync_run_id UUID REFERENCES search_console_sync_runs(id),
    path TEXT NOT NULL,
    is_pending BOOLEAN,
    is_sitemaps_index BOOLEAN,
    last_submitted TEXT,
    last_downloaded TEXT,
    errors INTEGER DEFAULT 0,
    warnings INTEGER DEFAULT 0,
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS site_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    source TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority_score INTEGER NOT NULL DEFAULT 0,
    impact_label TEXT,
    affected_url TEXT,
    issue_type TEXT,
    data JSONB,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS connection_certifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    connection_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sandbox_only',
    message TEXT,
    details JSONB,
    last_tested_at TIMESTAMPTZ,
    safe_fix_tested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS snippet_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    page_url TEXT,
    insight_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    device_type TEXT,
    metric_name TEXT,
    metric_value NUMERIC(12,3),
    sample_size INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    description TEXT,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_search_console_connections_site
    ON search_console_connections(site_id);
CREATE INDEX IF NOT EXISTS idx_search_console_connections_org
    ON search_console_connections(org_id);
CREATE INDEX IF NOT EXISTS idx_search_console_sync_runs_site
    ON search_console_sync_runs(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gsc_page_metrics_site_page
    ON search_console_page_metrics(site_id, page_url);
CREATE INDEX IF NOT EXISTS idx_gsc_page_metrics_site_impressions
    ON search_console_page_metrics(site_id, impressions DESC);
CREATE INDEX IF NOT EXISTS idx_gsc_query_metrics_site_query
    ON search_console_query_metrics(site_id, query);
CREATE INDEX IF NOT EXISTS idx_gsc_query_metrics_site_page
    ON search_console_query_metrics(site_id, page_url);
CREATE INDEX IF NOT EXISTS idx_gsc_inspections_site_url
    ON search_console_inspections(site_id, url);
CREATE INDEX IF NOT EXISTS idx_gsc_sitemaps_site_path
    ON search_console_sitemaps(site_id, path);
CREATE INDEX IF NOT EXISTS idx_site_opportunities_site_priority
    ON site_opportunities(site_id, priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_site_opportunities_site_status
    ON site_opportunities(site_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_connection_certifications_site_type
    ON connection_certifications(site_id, connection_type);
CREATE INDEX IF NOT EXISTS idx_snippet_insights_site_type
    ON snippet_insights(site_id, insight_type);
