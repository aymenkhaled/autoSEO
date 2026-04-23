CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;

ALTER TABLE sites
    ADD COLUMN IF NOT EXISTS ownership_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS verification_method TEXT,
    ADD COLUMN IF NOT EXISTS verification_token TEXT,
    ADD COLUMN IF NOT EXISTS verification_requested_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;

ALTER TABLE pages
    ADD COLUMN IF NOT EXISTS etag TEXT,
    ADD COLUMN IF NOT EXISTS last_modified TEXT;

ALTER TABLE snippet_events
    ADD COLUMN IF NOT EXISTS inp_ms INTEGER,
    ADD COLUMN IF NOT EXISTS fcp_ms INTEGER,
    ADD COLUMN IF NOT EXISTS device_type TEXT;

ALTER TABLE change_log ADD COLUMN IF NOT EXISTS metadata JSONB;

CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    keyword TEXT NOT NULL,
    target_url TEXT,
    intent TEXT DEFAULT 'informational',
    priority SMALLINT DEFAULT 1,
    added_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS keyword_rankings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id UUID REFERENCES keywords(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    position SMALLINT,
    previous_position SMALLINT,
    search_volume INTEGER,
    cpc_usd NUMERIC(8,2),
    difficulty SMALLINT,
    url TEXT,
    serp_features TEXT[],
    country TEXT DEFAULT 'US',
    device TEXT DEFAULT 'desktop',
    checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    domain TEXT NOT NULL,
    name TEXT,
    seo_score SMALLINT,
    keywords_count INTEGER,
    backlinks_count INTEGER,
    added_by UUID REFERENCES users(id),
    last_analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS backlinks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) NOT NULL,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    source_url TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    target_url TEXT NOT NULL,
    anchor_text TEXT,
    is_dofollow BOOLEAN DEFAULT TRUE,
    domain_rating SMALLINT,
    is_new BOOLEAN DEFAULT FALSE,
    is_lost BOOLEAN DEFAULT FALSE,
    first_seen_at TIMESTAMPTZ DEFAULT now(),
    last_seen_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    user_id UUID REFERENCES users(id),
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    status TEXT NOT NULL DEFAULT 'pending',
    invited_by UUID REFERENCES users(id),
    invited_at TIMESTAMPTZ DEFAULT now(),
    accepted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS issue_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID REFERENCES issues(id) NOT NULL,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    user_id UUID REFERENCES users(id) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    user_id UUID REFERENCES users(id) NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    data JSONB,
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL UNIQUE,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    email_enabled BOOLEAN DEFAULT TRUE,
    slack_enabled BOOLEAN DEFAULT FALSE,
    in_app_enabled BOOLEAN DEFAULT TRUE,
    slack_webhook_url TEXT,
    email_crawl_complete BOOLEAN DEFAULT TRUE,
    email_new_issues BOOLEAN DEFAULT TRUE,
    email_fix_applied BOOLEAN DEFAULT TRUE,
    email_weekly_digest BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scheduled_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    site_id UUID REFERENCES sites(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'weekly',
    format TEXT NOT NULL DEFAULT 'pdf',
    recipients TEXT[] NOT NULL,
    schedule_cron TEXT,
    last_sent_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    user_id UUID REFERENCES users(id),
    event_type TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    secret TEXT NOT NULL,
    events TEXT[] NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID REFERENCES webhooks(id) NOT NULL,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    event TEXT NOT NULL,
    payload JSONB NOT NULL,
    status_code SMALLINT,
    response_body TEXT,
    duration_ms INTEGER,
    success BOOLEAN,
    attempted_at TIMESTAMPTZ DEFAULT now(),
    next_retry_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ai_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0,
    task_type TEXT,
    crawl_id UUID REFERENCES crawls(id),
    issue_id UUID REFERENCES issues(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fix_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID REFERENCES issues(id) NOT NULL,
    site_id UUID REFERENCES sites(id) NOT NULL,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    captured_value TEXT,
    applied_value TEXT,
    applied_by UUID REFERENCES users(id),
    action TEXT NOT NULL DEFAULT 'apply',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS page_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) NOT NULL,
    org_id UUID REFERENCES organizations(id) NOT NULL,
    page_id UUID REFERENCES pages(id),
    public_url TEXT NOT NULL,
    source_page_id TEXT NOT NULL,
    source_path TEXT,
    source_url TEXT,
    connection_type TEXT NOT NULL,
    metadata JSONB,
    last_synced_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

WITH ranked_active_crawls AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY site_id
            ORDER BY created_at DESC NULLS LAST, started_at DESC NULLS LAST, id DESC
        ) AS active_rank
    FROM crawls
    WHERE status IN ('queued', 'running', 'cancelling')
)
UPDATE crawls
SET
    status = 'failed',
    completed_at = COALESCE(completed_at, now()),
    error_message = COALESCE(error_message, 'Closed by migration before enforcing one active crawl per site')
FROM ranked_active_crawls
WHERE crawls.id = ranked_active_crawls.id
  AND ranked_active_crawls.active_rank > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_crawls_one_active_per_site
    ON crawls(site_id)
    WHERE status IN ('queued', 'running', 'cancelling');

CREATE UNIQUE INDEX IF NOT EXISTS uq_pages_crawl_url
    ON pages(crawl_id, url);

CREATE UNIQUE INDEX IF NOT EXISTS uq_page_sources_site_public_url
    ON page_sources(site_id, public_url);

CREATE INDEX IF NOT EXISTS idx_page_sources_page_id ON page_sources(page_id);
CREATE INDEX IF NOT EXISTS idx_fix_versions_issue_id ON fix_versions(issue_id);
CREATE INDEX IF NOT EXISTS idx_fix_versions_site_id ON fix_versions(site_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_created_at ON notifications(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_webhook_attempted_at ON webhook_deliveries(webhook_id, attempted_at DESC);
