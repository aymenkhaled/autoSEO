CREATE TABLE IF NOT EXISTS fix_proof_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    issue_type TEXT,
    snapshot_type TEXT NOT NULL,
    pr_url TEXT,
    branch TEXT,
    seo_score SMALLINT,
    pages_crawled INTEGER DEFAULT 0,
    open_issue_count INTEGER DEFAULT 0,
    grouped_issue_count INTEGER DEFAULT 0,
    gsc_clicks NUMERIC(12,2) DEFAULT 0,
    gsc_impressions NUMERIC(12,2) DEFAULT 0,
    gsc_ctr NUMERIC(8,6) DEFAULT 0,
    gsc_position NUMERIC(8,3) DEFAULT 0,
    ga_sessions NUMERIC(12,2) DEFAULT 0,
    ga_key_events NUMERIC(12,2) DEFAULT 0,
    ga_revenue NUMERIC(12,2) DEFAULT 0,
    pagespeed_score SMALLINT,
    evidence JSONB,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS autopilot_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id),
    status TEXT NOT NULL DEFAULT 'completed',
    run_type TEXT NOT NULL DEFAULT 'manual',
    summary TEXT,
    next_actions JSONB,
    provider_health JSONB,
    created_by UUID REFERENCES users(id),
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_visibility_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    prompt TEXT NOT NULL,
    target_entity TEXT,
    competitor_domains TEXT[],
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_visibility_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    prompt_id UUID REFERENCES ai_visibility_prompts(id),
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    visibility_score SMALLINT,
    entity_score SMALLINT,
    citation_score SMALLINT,
    competitor_mentions JSONB,
    missing_context JSONB,
    recommendations JSONB,
    evidence JSONB,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    source_opportunity_id UUID REFERENCES site_opportunities(id),
    page_url TEXT NOT NULL,
    target_keyword TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'brief_ready',
    brief JSONB NOT NULL,
    github_pr_url TEXT,
    github_branch TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS keyword_provider_sync_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'skipped_provider_missing',
    keywords_synced INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    data JSONB,
    created_by UUID REFERENCES users(id),
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crawl_log_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    filename TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    rows_ingested INTEGER NOT NULL DEFAULT 0,
    summary JSONB,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crawl_log_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    import_id UUID REFERENCES crawl_log_imports(id) NOT NULL,
    url TEXT NOT NULL,
    method TEXT,
    status_code SMALLINT,
    user_agent TEXT,
    bot_family TEXT,
    bytes_sent INTEGER,
    requested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS client_sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    client_id UUID REFERENCES clients(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fix_proof_snapshots_site_created
    ON fix_proof_snapshots(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fix_proof_snapshots_site_issue
    ON fix_proof_snapshots(site_id, issue_type);
CREATE INDEX IF NOT EXISTS idx_autopilot_runs_org_created
    ON autopilot_runs(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_autopilot_runs_site_created
    ON autopilot_runs(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_visibility_prompts_site
    ON ai_visibility_prompts(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_visibility_runs_site_created
    ON ai_visibility_runs(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_briefs_site_created
    ON content_briefs(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_keyword_provider_sync_runs_site
    ON keyword_provider_sync_runs(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_log_imports_site_created
    ON crawl_log_imports(site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_log_entries_site_url
    ON crawl_log_entries(site_id, url);
CREATE INDEX IF NOT EXISTS idx_crawl_log_entries_site_bot
    ON crawl_log_entries(site_id, bot_family);
CREATE UNIQUE INDEX IF NOT EXISTS idx_client_sites_client_site
    ON client_sites(client_id, site_id);
CREATE INDEX IF NOT EXISTS idx_client_sites_org
    ON client_sites(org_id);
