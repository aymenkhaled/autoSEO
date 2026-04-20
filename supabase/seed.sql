-- ============================================
-- AutoSEO Seed Data — Development Only
-- ============================================

-- Dev organization
INSERT INTO organizations (id, name, slug, plan) VALUES 
    ('00000000-0000-0000-0000-000000000001', 'Dev Organization', 'dev-org', 'pro')
ON CONFLICT (id) DO NOTHING;

-- Dev user
INSERT INTO users (id, org_id, role, email, full_name) VALUES 
    ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'owner', 'dev@autoseo.local', 'Dev User')
ON CONFLICT (id) DO NOTHING;

-- Sample site
INSERT INTO sites (id, org_id, name, domain, connection_type, status) VALUES 
    ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', 'Example Blog', 'https://example.com', 'crawler', 'active')
ON CONFLICT (id) DO NOTHING;
