ALTER TABLE crawls
    ADD COLUMN IF NOT EXISTS urls_discovered INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS urls_skipped INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS crawl_limit INTEGER,
    ADD COLUMN IF NOT EXISTS coverage_reason TEXT,
    ADD COLUMN IF NOT EXISTS coverage_details JSONB;

UPDATE crawls
SET
    crawl_limit = COALESCE(crawl_limit, pages_total),
    urls_discovered = COALESCE(NULLIF(urls_discovered, 0), pages_total, pages_crawled, 0),
    urls_skipped = COALESCE(urls_skipped, 0),
    coverage_reason = COALESCE(coverage_reason, 'Historical crawl; detailed coverage was not recorded yet.')
WHERE coverage_reason IS NULL;
