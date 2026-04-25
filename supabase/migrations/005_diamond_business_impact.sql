CREATE TABLE IF NOT EXISTS google_analytics_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    property_id TEXT NOT NULL,
    property_name TEXT,
    token_encrypted TEXT NOT NULL,
    token_iv TEXT NOT NULL,
    scopes TEXT[] NOT NULL,
    expires_at TIMESTAMPTZ,
    connected_by UUID REFERENCES users(id),
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS google_analytics_sync_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    connection_id UUID REFERENCES google_analytics_connections(id),
    status TEXT NOT NULL DEFAULT 'running',
    days INTEGER NOT NULL DEFAULT 90,
    rows_synced INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics_page_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    sync_run_id UUID REFERENCES google_analytics_sync_runs(id),
    page_url TEXT NOT NULL,
    date_start TEXT NOT NULL,
    date_end TEXT NOT NULL,
    sessions NUMERIC(12,2) NOT NULL DEFAULT 0,
    active_users NUMERIC(12,2) NOT NULL DEFAULT 0,
    views NUMERIC(12,2) NOT NULL DEFAULT 0,
    key_events NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_revenue NUMERIC(12,2) NOT NULL DEFAULT 0,
    transactions NUMERIC(12,2) NOT NULL DEFAULT 0,
    engagement_rate NUMERIC(8,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pagespeed_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    page_url TEXT NOT NULL,
    strategy TEXT NOT NULL DEFAULT 'mobile',
    status TEXT NOT NULL DEFAULT 'running',
    performance_score SMALLINT,
    accessibility_score SMALLINT,
    best_practices_score SMALLINT,
    seo_score SMALLINT,
    lcp_ms INTEGER,
    inp_ms INTEGER,
    cls_score NUMERIC(6,4),
    fcp_ms INTEGER,
    ttfb_ms INTEGER,
    total_blocking_time_ms INTEGER,
    speed_index_ms INTEGER,
    opportunities JSONB,
    diagnostics JSONB,
    crux_metrics JSONB,
    screenshot TEXT,
    error_message TEXT,
    checked_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS indexnow_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    key TEXT NOT NULL,
    key_location TEXT NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_verified_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS indexnow_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    key_id UUID REFERENCES indexnow_keys(id),
    urls TEXT[] NOT NULL,
    status_code SMALLINT,
    success BOOLEAN,
    response_body TEXT,
    submitted_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS competitor_page_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    competitor_id UUID REFERENCES competitors(id) NOT NULL,
    site_page_url TEXT NOT NULL,
    competitor_page_url TEXT NOT NULL,
    site_score SMALLINT,
    competitor_score SMALLINT,
    gaps JSONB,
    site_signals JSONB,
    competitor_signals JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    name TEXT NOT NULL,
    contact_email TEXT,
    brand_name TEXT,
    logo_url TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_share_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    token TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    snapshot JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_google_analytics_connections_site
    ON google_analytics_connections(site_id);
CREATE INDEX IF NOT EXISTS idx_google_analytics_connections_org
    ON google_analytics_connections(org_id);
CREATE INDEX IF NOT EXISTS idx_google_analytics_sync_runs_site
    ON google_analytics_sync_runs(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_page_metrics_site_page
    ON analytics_page_metrics(site_id, page_url);
CREATE INDEX IF NOT EXISTS idx_analytics_page_metrics_site_revenue
    ON analytics_page_metrics(site_id, total_revenue DESC);
CREATE INDEX IF NOT EXISTS idx_pagespeed_runs_site_url
    ON pagespeed_runs(site_id, page_url, strategy);
CREATE INDEX IF NOT EXISTS idx_pagespeed_runs_site_checked
    ON pagespeed_runs(site_id, checked_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_indexnow_keys_site
    ON indexnow_keys(site_id);
CREATE INDEX IF NOT EXISTS idx_indexnow_submissions_site
    ON indexnow_submissions(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_competitor_page_comparisons_competitor
    ON competitor_page_comparisons(competitor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_clients_org
    ON clients(org_id);
CREATE INDEX IF NOT EXISTS idx_report_share_links_site
    ON report_share_links(site_id, created_at DESC);
