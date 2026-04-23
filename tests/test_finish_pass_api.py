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
    Issue,
    IssueComment,
    Keyword,
    KeywordRanking,
    Notification,
    Organization,
    Page,
    PageSource,
    ScheduledReport,
    Site,
    SnippetEvent,
    User,
)
from packages.shared.notifications import notify_org_users
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
