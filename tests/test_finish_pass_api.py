from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from main import app
from models.database import AsyncSessionLocal, engine
from models.tables import (
    AiUsage,
    ApiKey,
    ChangeLog,
    Competitor,
    Crawl,
    FixProofSnapshot,
    Issue,
    IssueComment,
    Keyword,
    KeywordRanking,
    Notification,
    Organization,
    Page,
    PageSource,
    ScheduledReport,
    SearchConsolePageMetric,
    Site,
    SnippetEvent,
    ConnectionCertification,
    User,
)
from packages.shared.notifications import notify_org_users
from packages.shared.patch_safety import validate_file_changes
from services.crawl_budget import parse_log_lines
from routers.auth import create_access_token
from workers.tasks.fix import _run_ai_analysis_async


def run(coro):
    async def _runner():
        try:
            return await coro
        finally:
            await engine.dispose()

    return asyncio.run(_runner())


async def api_request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


async def seed_user(plan: str = "free"):
    async with AsyncSessionLocal() as session:
        org = Organization(name="Test Org", slug=f"test-org-{uuid.uuid4().hex[:8]}", plan=plan)
        session.add(org)
        await session.flush()
        user = User(
            id=uuid.uuid4(),
            org_id=org.id,
            role="owner",
            email=f"owner-{uuid.uuid4().hex[:6]}@example.com",
            full_name="Owner User",
            password_hash="hashed-password",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, org


def auth_headers(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


def test_system_readiness_uses_local_auth_without_supabase():
    response = run(api_request("GET", "/api/v1/system/readiness"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["auth_mode"] == "local_jwt"
    assert payload["providers"]["anthropic"] is False
    assert payload["webhook_delivery_available"] is True
    assert payload["features"]["billing"]["state"] in {"saved_only", "setup_required"}
    assert payload["providers"]["github_app"] is False


def test_register_login_defaults_new_org_to_free_plan():
    email = f"local-{uuid.uuid4().hex[:8]}@example.com"
    response = run(api_request(
        "POST",
        "/api/v1/auth/register",
        json={"email": email, "password": "secretpass123", "full_name": "Local User"},
    ))
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]

    me = run(api_request("GET", "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}))
    assert me.status_code == 200
    org = run(api_request("GET", "/api/v1/auth/org", headers={"Authorization": f"Bearer {token}"}))
    assert org.status_code == 200
    assert org.json()["plan"] == "free"
    assert org.json()["name"] == "Local User's Organization"

    login = run(api_request("POST", "/api/v1/auth/login", json={"email": email, "password": "secretpass123"}))
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_site_delete_blocks_active_crawl_then_deletes_related_records():
    user, org = run(seed_user())

    async def seed_site_graph():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Delete Me", domain="https://delete-me.test", connection_type="crawler")
            session.add(site)
            await session.flush()

            active_crawl = Crawl(site_id=site.id, org_id=org.id, status="running", trigger="manual")
            session.add(active_crawl)
            await session.commit()
            return site.id, active_crawl.id

    site_id, active_crawl_id = run(seed_site_graph())
    blocked = run(api_request("DELETE", f"/api/v1/sites/{site_id}", headers=auth_headers(user)))
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["crawl_id"] == str(active_crawl_id)

    async def finish_crawl_and_add_related_rows():
        async with AsyncSessionLocal() as session:
            site = await session.get(Site, site_id)
            crawl = await session.get(Crawl, active_crawl_id)
            crawl.status = "completed"
            crawl.completed_at = datetime.now(timezone.utc)
            site.last_crawled_at = datetime.now(timezone.utc)

            page = Page(crawl_id=crawl.id, site_id=site.id, org_id=org.id, url=f"{site.domain}/page", title="Page")
            session.add(page)
            await session.flush()

            issue = Issue(
                crawl_id=crawl.id,
                site_id=site.id,
                org_id=org.id,
                page_id=page.id,
                type="missing_title",
                category="meta",
                severity="medium",
                impact_score=50,
                fix_type="auto",
                fix_status="deployed",
                current_value="Old",
                proposed_fix="New title",
                applied_at=datetime.now(timezone.utc),
            )
            session.add(issue)
            await session.flush()

            session.add_all([
                IssueComment(issue_id=issue.id, org_id=org.id, user_id=user.id, body="Needs review"),
                ChangeLog(org_id=org.id, site_id=site.id, issue_id=issue.id, action="created", actor_type="system"),
                AiUsage(org_id=org.id, crawl_id=crawl.id, issue_id=issue.id, model="claude-sonnet-4-5", total_tokens=10, cost_usd=0.01, prompt_tokens=5, completion_tokens=5),
                PageSource(site_id=site.id, org_id=org.id, page_id=page.id, public_url=page.url, source_page_id="cms-1", connection_type="crawler"),
                SnippetEvent(site_id=site.id, org_id=org.id, page_url=page.url),
                Keyword(org_id=org.id, site_id=site.id, keyword="autoseo test"),
                Competitor(org_id=org.id, site_id=site.id, domain="competitor.test"),
                ScheduledReport(org_id=org.id, site_id=site.id, name="Weekly", recipients=["team@example.com"]),
            ])
            await session.flush()

            keyword = (await session.execute(select(Keyword).where(Keyword.site_id == site.id))).scalar_one()
            session.add(KeywordRanking(keyword_id=keyword.id, site_id=site.id, org_id=org.id))
            await session.commit()

    run(finish_crawl_and_add_related_rows())

    deleted = run(api_request("DELETE", f"/api/v1/sites/{site_id}", headers=auth_headers(user)))
    assert deleted.status_code == 200, deleted.text
    payload = deleted.json()
    assert payload["site_name"] == "Delete Me"
    assert payload["deleted_counts"]["site"] == 1
    assert payload["deleted_counts"]["issues"] == 1
    assert payload["deleted_counts"]["pages"] == 1
    assert payload["deleted_counts"]["crawls"] == 1
    assert payload["deleted_counts"]["keywords"] == 1
    assert payload["deleted_counts"]["competitors"] == 1

    async def assert_site_missing():
        async with AsyncSessionLocal() as session:
            assert await session.get(Site, site_id) is None

    run(assert_site_missing())


def test_usage_counts_deployed_and_legacy_applied():
    user, org = run(seed_user())

    async def seed_usage_rows():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Usage Site", domain="https://usage.test", connection_type="crawler")
            session.add(site)
            await session.flush()
            crawl = Crawl(site_id=site.id, org_id=org.id, status="completed", created_at=datetime.now(timezone.utc))
            session.add(crawl)
            await session.flush()
            for status_value in ("deployed", "applied"):
                session.add(
                    Issue(
                        crawl_id=crawl.id,
                        site_id=site.id,
                        org_id=org.id,
                        type="missing_title",
                        category="meta",
                        severity="medium",
                        impact_score=50,
                        fix_type="auto",
                        fix_status=status_value,
                        applied_at=datetime.now(timezone.utc),
                    )
                )
            await session.commit()

    run(seed_usage_rows())
    response = run(api_request("GET", "/api/v1/usage", headers=auth_headers(user)))
    assert response.status_code == 200
    assert response.json()["usage"]["ai_fixes"]["used"] == 2
    assert response.json()["plan"] == "free"


def test_api_key_cannot_access_jwt_only_routes():
    user, org = run(seed_user())
    raw_key = "autoseo_test_scope_key"

    async def seed_api_key():
        async with AsyncSessionLocal() as session:
            session.add(
                ApiKey(
                    org_id=org.id,
                    name="Test Key",
                    key_hash=hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
                    key_prefix=raw_key[:12],
                    scopes=["read:sites"],
                )
            )
            await session.commit()

    run(seed_api_key())

    response = run(api_request("GET", "/api/v1/team", headers={"X-AutoSEO-Key": raw_key}))
    assert response.status_code == 403
    assert "user session" in response.json()["detail"].lower()


def test_missing_ai_provider_reclassifies_auto_issue_as_manual():
    user, org = run(seed_user())

    async def seed_ai_issue():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="AI Site", domain="https://ai-site.test", connection_type="crawler")
            session.add(site)
            await session.flush()
            crawl = Crawl(site_id=site.id, org_id=org.id, status="completed")
            session.add(crawl)
            await session.flush()
            page = Page(crawl_id=crawl.id, site_id=site.id, org_id=org.id, url=f"{site.domain}/pricing", title="Pricing", h1_text=["Pricing"])
            session.add(page)
            await session.flush()
            issue = Issue(
                crawl_id=crawl.id,
                site_id=site.id,
                org_id=org.id,
                page_id=page.id,
                type="missing_meta_description",
                category="meta",
                severity="medium",
                impact_score=40,
                fix_type="auto",
                fix_status="pending",
            )
            session.add(issue)
            await session.commit()
            return str(crawl.id), str(site.id), issue.id

    crawl_id, site_id, issue_id = run(seed_ai_issue())
    run(_run_ai_analysis_async(crawl_id, site_id))

    async def fetch_issue():
        async with AsyncSessionLocal() as session:
            return await session.get(Issue, issue_id)

    issue = run(fetch_issue())
    assert issue.fix_type == "manual"
    assert issue.proposed_fix is None
    assert issue.proposed_fix_metadata["ai_status"] == "provider_unavailable"


def test_notify_org_users_persists_notification_payload():
    user, org = run(seed_user())

    async def create_notification():
        async with AsyncSessionLocal() as session:
            created = await notify_org_users(
                session,
                org.id,
                notification_type="webhook.delivery",
                title="Webhook failed",
                body="A delivery failed.",
                data={"site_id": "site-123", "webhook_id": "wh-123"},
            )
            await session.commit()
            saved = (await session.execute(select(Notification).where(Notification.org_id == org.id))).scalars().all()
            return created, saved

    created, saved = run(create_notification())
    assert created == 1
    assert saved[0].type == "webhook.delivery"
    assert saved[0].data["webhook_id"] == "wh-123"


def test_writable_connection_requires_site_verification():
    user, org = run(seed_user())

    async def seed_site():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="GitHub Site", domain="https://github-site.test", connection_type="crawler")
            session.add(site)
            await session.commit()
            return site.id

    site_id = run(seed_site())
    response = run(api_request(
        "PUT",
        f"/api/v1/sites/{site_id}/connection",
        headers=auth_headers(user),
        json={
            "connection_type": "github",
            "owner": "owner",
            "repo": "repo",
            "branch": "main",
            "github_token": "ghp_test",
        },
    ))
    assert response.status_code == 403
    assert "Verify site ownership" in response.json()["detail"]


def test_root_cause_workflow_reports_missing_github_requirements():
    user, org = run(seed_user())

    async def seed_issue():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="SPA Site", domain="https://spa-site.test", connection_type="crawler")
            session.add(site)
            await session.flush()
            crawl = Crawl(site_id=site.id, org_id=org.id, status="completed")
            session.add(crawl)
            await session.flush()
            page = Page(crawl_id=crawl.id, site_id=site.id, org_id=org.id, url=f"{site.domain}/pricing")
            session.add(page)
            await session.flush()
            session.add(
                Issue(
                    crawl_id=crawl.id,
                    site_id=site.id,
                    org_id=org.id,
                    page_id=page.id,
                    type="spa_no_prerender",
                    category="rendering",
                    severity="critical",
                    impact_score=95,
                    fix_type="manual",
                    fix_status="pending",
                )
            )
            await session.commit()
            return site.id

    site_id = run(seed_issue())
    response = run(api_request(
        "POST",
        "/api/v1/issues/root-cause-fix",
        headers=auth_headers(user),
        json={"site_id": str(site_id), "issue_type": "spa_no_prerender", "mode": "plan"},
    ))
    assert response.status_code == 200, response.text
    workflow = response.json()["fix_workflow"]
    assert workflow["can_create_github_pr"] is False
    assert workflow["can_preview_ai"] is False
    assert any("GitHub" in item for item in workflow["missing_requirements"])
    assert any("Verify" in item for item in workflow["missing_requirements"])
    assert workflow["manual_steps"]


def test_github_app_install_url_reports_missing_platform_config():
    user, org = run(seed_user())

    async def seed_site():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="App Site", domain="https://app-site.test")
            session.add(site)
            await session.commit()
            return site.id

    site_id = run(seed_site())
    response = run(api_request(
        "GET",
        f"/api/v1/github/app/install-url?site_id={site_id}",
        headers=auth_headers(user),
    ))
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is False
    assert payload["install_url"] is None
    assert payload["requires_verification"] is True


def test_patch_safety_blocks_secret_and_lockfile_changes():
    result = validate_file_changes([
        {
            "path": "package-lock.json",
            "action": "update",
            "summary": "Do not touch lockfile",
            "content": "{}",
        },
        {
            "path": "src/seo.ts",
            "action": "update",
            "summary": "Bad secret",
            "content": "export const token = 'ghp_secret';",
        },
    ])
    assert result.ok is False
    assert any("protected file" in error for error in result.errors)
    assert any("token-looking" in error for error in result.errors)


def test_api_key_root_cause_fix_requires_write_fixes_scope():
    user, org = run(seed_user())
    raw_key = "autoseo_read_issues_only"

    async def seed_key_and_site():
        async with AsyncSessionLocal() as session:
            session.add(
                ApiKey(
                    org_id=org.id,
                    name="Read Issues Key",
                    key_hash=hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
                    key_prefix=raw_key[:12],
                    scopes=["read:issues"],
                )
            )
            site = Site(org_id=org.id, name="Scope Site", domain="https://scope.test")
            session.add(site)
            await session.commit()
            return site.id

    site_id = run(seed_key_and_site())
    response = run(api_request(
        "POST",
        "/api/v1/issues/root-cause-fix",
        headers={"X-AutoSEO-Key": raw_key},
        json={"site_id": str(site_id), "issue_type": "missing_sitemap", "mode": "plan"},
    ))
    assert response.status_code == 403
    assert "write:fixes" in response.json()["detail"]


def test_crawl_response_exposes_coverage_fields():
    user, org = run(seed_user())

    async def seed_crawl():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Coverage Site", domain="https://coverage.test")
            session.add(site)
            await session.flush()
            crawl = Crawl(
                site_id=site.id,
                org_id=org.id,
                status="completed",
                trigger="manual",
                pages_crawled=10,
                pages_total=10,
                urls_discovered=30,
                urls_skipped=20,
                crawl_limit=10,
                coverage_reason="AutoSEO discovered 30 safe URLs but scanned 10 because this site's crawl limit is 10.",
                coverage_details={"reason": "crawl_limit_reached"},
            )
            session.add(crawl)
            await session.commit()
            return crawl.id

    crawl_id = run(seed_crawl())
    response = run(api_request("GET", f"/api/v1/crawls/{crawl_id}", headers=auth_headers(user)))
    assert response.status_code == 200
    payload = response.json()
    assert payload["urls_discovered"] == 30
    assert payload["urls_skipped"] == 20
    assert payload["crawl_limit"] == 10
    assert payload["coverage_details"]["reason"] == "crawl_limit_reached"


def test_search_console_status_is_clear_when_disconnected():
    user, org = run(seed_user())

    async def seed_site():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="GSC Site", domain="https://gsc-site.test")
            session.add(site)
            await session.commit()
            return site.id

    site_id = run(seed_site())
    status_response = run(api_request("GET", f"/api/v1/sites/{site_id}/search-console/status", headers=auth_headers(user)))
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["connected"] is False
    assert payload["readiness"] == "setup_required"
    assert payload["scope"] == "https://www.googleapis.com/auth/webmasters.readonly"

    connect_response = run(api_request("GET", f"/api/v1/google/search-console/connect-url?site_id={site_id}", headers=auth_headers(user)))
    assert connect_response.status_code == 200
    assert connect_response.json()["configured"] is False
    assert connect_response.json()["connect_url"] is None


def test_prioritized_issues_include_search_console_impact():
    user, org = run(seed_user())

    async def seed_priority_rows():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Priority Site", domain="https://priority.test", ownership_verified=True)
            session.add(site)
            await session.flush()
            crawl = Crawl(site_id=site.id, org_id=org.id, status="completed")
            session.add(crawl)
            await session.flush()
            page = Page(crawl_id=crawl.id, site_id=site.id, org_id=org.id, url="https://priority.test/pricing", title="Pricing")
            session.add(page)
            await session.flush()
            session.add(Issue(
                crawl_id=crawl.id,
                site_id=site.id,
                org_id=org.id,
                page_id=page.id,
                type="duplicate_title",
                category="meta",
                severity="medium",
                impact_score=60,
                fix_type="manual",
                fix_status="pending",
            ))
            session.add(SearchConsolePageMetric(
                org_id=org.id,
                site_id=site.id,
                page_url=page.url,
                date_start="2026-01-01",
                date_end="2026-03-31",
                clicks=20,
                impressions=5000,
                ctr=0.004,
                position=8.4,
            ))
            await session.commit()
            return site.id

    site_id = run(seed_priority_rows())
    response = run(api_request("GET", f"/api/v1/issues/prioritized?site_id={site_id}", headers=auth_headers(user)))
    assert response.status_code == 200, response.text
    issue = response.json()["issues"][0]
    assert issue["type"] == "duplicate_title"
    assert issue["gsc_impact"]["impressions"] == 5000
    assert issue["gsc_impact"]["estimated_click_loss"] > 0
    assert issue["priority_score"] > 100


def test_site_opportunities_combine_gsc_and_snippet_signals():
    user, org = run(seed_user())

    async def seed_opportunity_rows():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Opportunity Site", domain="https://opportunity.test")
            session.add(site)
            await session.flush()
            crawl = Crawl(site_id=site.id, org_id=org.id, status="completed")
            session.add(crawl)
            await session.flush()
            page = Page(crawl_id=crawl.id, site_id=site.id, org_id=org.id, url="https://opportunity.test/page", title="Crawler title")
            session.add(page)
            await session.flush()
            session.add(SearchConsolePageMetric(
                org_id=org.id,
                site_id=site.id,
                page_url=page.url,
                date_start="2026-01-01",
                date_end="2026-03-31",
                clicks=4,
                impressions=1200,
                ctr=0.003,
                position=6.2,
            ))
            for _ in range(3):
                session.add(SnippetEvent(
                    site_id=site.id,
                    org_id=org.id,
                    page_url=page.url,
                    title="Rendered title",
                    lcp_ms=4100,
                    inp_ms=260,
                    cls_score=0.04,
                    device_type="mobile",
                ))
            await session.commit()
            return site.id

    site_id = run(seed_opportunity_rows())
    response = run(api_request("GET", f"/api/v1/sites/{site_id}/opportunities", headers=auth_headers(user)))
    assert response.status_code == 200, response.text
    opportunities = response.json()["opportunities"]
    assert any(item["source"] == "gsc" and item["type"] == "high_impressions_low_ctr" for item in opportunities)
    assert any(item["source"] == "snippet" and item["type"] == "runtime_lcp_ms_p75" for item in opportunities)
    assert any(item["source"] == "snippet" and item["type"] == "rendered_title_differs_from_crawl" for item in opportunities)


def test_connection_certification_sandbox_persists_to_capabilities():
    user, org = run(seed_user())

    async def seed_site():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Certified Site", domain="https://certified.test")
            session.add(site)
            await session.commit()
            return site.id

    site_id = run(seed_site())
    response = run(api_request(
        "POST",
        f"/api/v1/sites/{site_id}/connections/wordpress/certify",
        headers=auth_headers(user),
        json={"mode": "sandbox"},
    ))
    assert response.status_code == 200
    assert response.json()["status"] == "sandbox_only"

    capabilities = run(api_request("GET", f"/api/v1/sites/{site_id}/connection/capabilities", headers=auth_headers(user)))
    assert capabilities.status_code == 200
    wordpress = next(item for item in capabilities.json()["capabilities"] if item["connection_type"] == "wordpress")
    assert wordpress["certification"]["status"] == "sandbox_only"

    async def assert_saved():
        async with AsyncSessionLocal() as session:
            certs = (await session.execute(select(ConnectionCertification))).scalars().all()
            assert len(certs) == 1

    run(assert_saved())


def test_generated_report_includes_opportunities_and_search_console_totals():
    user, org = run(seed_user())

    async def seed_report_rows():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Report Site", domain="https://report.test")
            session.add(site)
            await session.flush()
            crawl = Crawl(site_id=site.id, org_id=org.id, status="completed", seo_score=52, issues_found=1, pages_crawled=1, created_at=datetime.now(timezone.utc))
            session.add(crawl)
            await session.flush()
            page = Page(crawl_id=crawl.id, site_id=site.id, org_id=org.id, url="https://report.test/pricing", title="Pricing")
            session.add(page)
            await session.flush()
            session.add(Issue(
                crawl_id=crawl.id,
                site_id=site.id,
                org_id=org.id,
                page_id=page.id,
                type="duplicate_title",
                category="meta",
                severity="medium",
                impact_score=60,
                fix_type="manual",
                fix_status="github_pr_created",
            ))
            session.add(SearchConsolePageMetric(
                org_id=org.id,
                site_id=site.id,
                page_url=page.url,
                date_start="2026-01-01",
                date_end="2026-03-31",
                clicks=10,
                impressions=1000,
                ctr=0.01,
                position=7,
            ))
            await session.commit()
            return site.id

    site_id = run(seed_report_rows())
    response = run(api_request("POST", "/api/v1/reports/generate", headers=auth_headers(user), json={"site_id": str(site_id)}))
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["search_console"]["totals"]["impressions"] == 1000
    assert payload["github_fix_status"]["open_pr_issue_count"] == 1
    assert payload["top_opportunities"]


def test_proof_summary_pairs_snapshots_and_counts_open_groups_only():
    user, org = run(seed_user())

    async def seed_proof_rows():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Proof Site", domain="https://proof.test")
            session.add(site)
            await session.flush()
            crawl = Crawl(site_id=site.id, org_id=org.id, status="completed", seo_score=41, pages_crawled=2)
            session.add(crawl)
            await session.flush()
            page = Page(crawl_id=crawl.id, site_id=site.id, org_id=org.id, url="https://proof.test/page", title="Proof")
            session.add(page)
            await session.flush()
            session.add_all([
                Issue(
                    crawl_id=crawl.id,
                    site_id=site.id,
                    org_id=org.id,
                    page_id=page.id,
                    type="duplicate_title",
                    category="meta",
                    severity="medium",
                    impact_score=60,
                    fix_type="manual",
                    fix_status="pending",
                ),
                Issue(
                    crawl_id=crawl.id,
                    site_id=site.id,
                    org_id=org.id,
                    page_id=page.id,
                    type="missing_title",
                    category="meta",
                    severity="medium",
                    impact_score=50,
                    fix_type="manual",
                    fix_status="deployed_after_merge",
                ),
                FixProofSnapshot(
                    org_id=org.id,
                    site_id=site.id,
                    issue_type="duplicate_title",
                    snapshot_type="before_pr",
                    pr_url="https://github.test/pr/1",
                    branch="autoseo/fix-title",
                    seo_score=41,
                    open_issue_count=1,
                    grouped_issue_count=1,
                    gsc_clicks=10,
                    gsc_impressions=100,
                    ga_revenue=5,
                    pagespeed_score=70,
                ),
                FixProofSnapshot(
                    org_id=org.id,
                    site_id=site.id,
                    issue_type="duplicate_title",
                    snapshot_type="after_recrawl",
                    pr_url="https://github.test/pr/1",
                    branch="autoseo/fix-title",
                    seo_score=80,
                    open_issue_count=0,
                    grouped_issue_count=0,
                    gsc_clicks=14,
                    gsc_impressions=130,
                    ga_revenue=9,
                    pagespeed_score=75,
                ),
            ])
            await session.commit()
            return site.id

    site_id = run(seed_proof_rows())
    response = run(api_request("GET", f"/api/v1/sites/{site_id}/proof", headers=auth_headers(user)))
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["current"]["grouped_issue_count"] == 1
    assert payload["delta"]["seo_score"] == 39
    assert payload["delta"]["grouped_issue_count"] == -1
    assert payload["proof_pairs"][0]["proof_status"] == "proven_after_recrawl"
    assert payload["proof_pairs"][0]["pr_url"] == "https://github.test/pr/1"


def test_digest_send_rejects_api_keys_even_with_write_sites_scope():
    user, org = run(seed_user())
    raw_key = "autoseo_digest_write_sites"

    async def seed_site_and_key():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Digest Site", domain="https://digest.test")
            session.add(site)
            session.add(
                ApiKey(
                    org_id=org.id,
                    name="Digest Key",
                    key_hash=hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
                    key_prefix=raw_key[:12],
                    scopes=["write:sites", "read:sites"],
                )
            )
            await session.commit()
            return site.id

    site_id = run(seed_site_and_key())
    response = run(api_request("POST", f"/api/v1/sites/{site_id}/digest/send", headers={"X-AutoSEO-Key": raw_key}))
    assert response.status_code == 403
    assert "user session" in response.json()["detail"].lower()


def test_keyword_provider_sync_is_honest_when_worker_is_not_wired():
    user, org = run(seed_user())

    async def seed_site():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Keyword Site", domain="https://keyword.test")
            session.add(site)
            await session.commit()
            return site.id

    site_id = run(seed_site())
    response = run(api_request(
        "POST",
        "/api/v1/keywords/sync-provider",
        headers=auth_headers(user),
        json={"site_id": str(site_id), "provider": "dataforseo"},
    ))
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "provider_not_wired"
    assert "did not invent rankings" in payload["message"]


def test_ai_visibility_is_labeled_as_readiness_scoring_only():
    user, org = run(seed_user())

    async def seed_site():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="AI Readiness Site", domain="https://ai-ready.test")
            session.add(site)
            await session.commit()
            return site.id

    site_id = run(seed_site())
    response = run(api_request("GET", f"/api/v1/sites/{site_id}/ai-visibility", headers=auth_headers(user)))
    assert response.status_code == 200
    payload = response.json()
    assert payload["readiness"] == "readiness_scoring_only"
    assert "does not yet query ChatGPT" in payload["message"]


def test_crawl_budget_parser_supports_json_csv_and_redacts_query_params():
    json_log = '{"ClientRequestURI":"/pricing?email=test@example.com","ClientRequestMethod":"GET","EdgeResponseStatus":200,"ClientRequestUserAgent":"Googlebot/2.1"}'
    entries, errors = parse_log_lines(json_log, site_domain="https://logs.test")
    assert not errors
    assert entries[0]["url"] == "https://logs.test/pricing"
    assert entries[0]["bot_family"] == "googlebot"

    csv_log = "ClientRequestURI,ClientRequestMethod,EdgeResponseStatus,ClientRequestUserAgent\n/contact?token=secret,GET,404,bingbot"
    entries, errors = parse_log_lines(csv_log, site_domain="https://logs.test")
    assert not errors
    assert entries[0]["url"] == "https://logs.test/contact"
    assert entries[0]["bot_family"] == "bingbot"


def test_integration_certification_dashboard_is_readable_with_site_scope_key():
    user, org = run(seed_user())
    raw_key = "autoseo_read_sites_certification"

    async def seed_site_cert_and_key():
        async with AsyncSessionLocal() as session:
            site = Site(org_id=org.id, name="Certification Site", domain="https://cert-dashboard.test", connection_type="crawler")
            session.add(site)
            await session.flush()
            session.add(ConnectionCertification(
                org_id=org.id,
                site_id=site.id,
                connection_type="crawler",
                status="production_ready",
                message="Crawler is read-only and certified.",
            ))
            session.add(ApiKey(
                org_id=org.id,
                name="Read Sites Key",
                key_hash=hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
                key_prefix=raw_key[:12],
                scopes=["read:sites"],
            ))
            await session.commit()

    run(seed_site_cert_and_key())
    response = run(api_request("GET", "/api/v1/integrations/certification", headers={"X-AutoSEO-Key": raw_key}))
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_sites"] == 1
    crawler = next(item for item in payload["sites"][0]["certifications"] if item["connection_type"] == "crawler")
    assert crawler["status"] == "production_ready"
