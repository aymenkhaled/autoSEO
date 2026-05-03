# AutoSEO — Autonomous SEO Agent

## Overview
AutoSEO is an autonomous SEO platform that crawls websites, detects issues with AI analysis, and automatically applies fixes directly to your CMS. Built with React 19 + Vite frontend, FastAPI backend, PostgreSQL, and Supabase Auth.

## Running Services
- **Frontend** — React/Vite on port 5000 (`cd apps/web && npm run dev`)
- **Backend API** — FastAPI on port 8000 (`cd apps/api && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`)
- **Production** — root `npm run build` builds `apps/web`; root `npm run start` serves FastAPI and the built frontend together on `$PORT`

## Database
- **Replit PostgreSQL** connected via `DATABASE_URL` env var
- Tables are created on API startup via SQLAlchemy `Base.metadata.create_all`
- `config.py` auto-converts URL to asyncpg format

## Authentication
- **Supabase Auth** — email/password + Google OAuth
- Frontend uses Supabase JS client (`apps/web/src/lib/supabase.ts`)
- Backend validates local JWTs with `SUPABASE_JWT_SECRET` and validates Supabase sessions through Supabase Auth when needed
- New users auto-provisioned with their own org on first sign-in
- `/auth/sync` endpoint for post-login user sync

## Environment Variables
| Variable | Purpose | Status |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection | Auto-provisioned |
| `SUPABASE_JWT_SECRET` | Backend JWT validation | Configured |
| `VITE_SUPABASE_URL` | Frontend Supabase URL | Configured |
| `VITE_SUPABASE_ANON_KEY` | Frontend Supabase key | Configured |
| `ANTHROPIC_API_KEY` | Claude AI features | Needed |
| `STRIPE_SECRET_KEY` | Billing | Needed |
| `STRIPE_WEBHOOK_SECRET` | Billing webhooks | Needed |
| `REDIS_URL` | Queue/cache | Needed |
| `DATAFORSEO_LOGIN` | Keyword rank tracking | Needed |
| `AHREFS_API_KEY` | Backlink monitoring | Needed |
| `RESEND_API_KEY` | Email delivery | Needed |

## Frontend Pages (17 total)
| Route | Page | Status |
|---|---|---|
| `/` | Landing | Built |
| `/login` | Login | Built + Supabase |
| `/signup` | Sign Up | Built + email confirm handling |
| `/privacy` | Privacy Policy | Built |
| `/terms` | Terms of Service | Built |
| `/dashboard` | Overview | Built |
| `/dashboard/sites` | Sites Grid | Built |
| `/dashboard/sites/:id` | Site Detail (6 tabs) | Built |
| `/dashboard/issues` | Issues List | Built |
| `/dashboard/fixes` | AI Fixes | Built |
| `/dashboard/analytics` | Analytics Charts | Built |
| `/dashboard/keywords` | Keyword Tracking | Built |
| `/dashboard/competitors` | Competitor Analysis | Built |
| `/dashboard/reports` | Reports | Built |
| `/dashboard/team` | Team Management | Built |
| `/dashboard/integrations` | CMS Integrations | Built |
| `/dashboard/api-keys` | API Keys | Built |
| `/dashboard/billing` | Billing | Built |
| `/dashboard/settings` | Settings | Built |

## Backend Routers (14 total)
`auth`, `sites`, `crawls`, `issues`, `fixes`, `snippet`, `webhooks`, `analytics`, `keywords`, `competitors`, `notifications`, `team`, `api_keys`, `usage`, `change_log`

## Packages Built
| Package | Status | Needs API Key |
|---|---|---|
| `packages/ai_engine/engine.py` | Fully implemented with stubs | `ANTHROPIC_API_KEY` |
| `packages/cms_adapters/wordpress.py` | Fully implemented | WordPress credentials |
| `packages/cms_adapters/github_adapter.py` | Fully implemented | `GITHUB_APP_ID` |
| `packages/crawler/` | 4-layer crawler | `SCRAPFLY_API_KEY` (optional) |
| `packages/snippet/snippet.js` | JS monitoring snippet | None |

## AI Engine (packages/ai_engine/engine.py)
- `generate_fix()` — generates SEO fixes using Claude (falls back to stubs without API key)
- `generate_content_brief()` — creates keyword-targeted content briefs
- `generate_fixes_bulk()` — concurrent fix generation for multiple issues
- Tier system: Tier 1 (auto-apply), Tier 2 (one-click), Tier 3 (manual)
- Cost tracking per call (tokens + USD)
- Uses Claude Haiku for simple fixes, Sonnet for complex ones

## CMS Adapters
- **WordPress** — REST API with Application Password/JWT auth. Detects Yoast/Rank Math. Reads + writes.
- **GitHub** — Creates fix branches + PRs for Next.js, Astro, Hugo, Jekyll sites
- Factory: `get_adapter(connection_type, **kwargs)`

## How to Enable Email Login Without Confirmation
For development/testing, go to your Supabase dashboard:
https://supabase.com/dashboard/project/qqzdoyqeftbqoldhheut/auth/providers
→ "Email" → disable "Confirm email"
After disabling, users can sign up and log in immediately without confirming their email.

## Architecture
| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite 8 + TypeScript + Tailwind CSS v4 |
| State | Zustand + TanStack Query |
| Auth | Supabase Auth (email + Google OAuth) |
| Backend | FastAPI + SQLAlchemy async; production serves frontend assets and `/api/*` routes from one autoscale service |
| Database | PostgreSQL (Replit) + 22 models |
| Queue | Celery + Redis |
| AI | Anthropic Claude (Haiku/Sonnet) |
| Crawler | Crawl4AI + Camoufox + ScrapFly |
| Payments | Stripe (subscriptions + metered) |

## Bug Fixes Applied (May 2026)
- **`models/tables.py`** — Replaced all 69 `datetime.utcnow` column defaults/onupdates with `lambda: datetime.now(timezone.utc)` (Python 3.12 deprecation fix); added `timezone` to datetime import.
- **`services/stripe_service.py`** — Fixed `stripe.error.StripeError` → `stripe.StripeError` for Stripe SDK v15.x compatibility (error classes moved to top-level namespace in v5+).
- **`workers/tasks/report.py`** — Added Celery/Redis noop fallback (matching crawl.py and fix.py patterns) so the module imports cleanly without a running Redis instance.
- **`services/crawl_budget.py`** — Removed dead double-assignment (`requested_at = None` immediately overwritten on next line).
- **`routers/competitors.py`** (May 2026 audit) — Fixed `DELETE /competitors/{id}` 500 error: FK violation from `competitor_page_comparisons` table. Added `delete(CompetitorPageComparison).where(...)` before `db.delete(comp)`. Also added `from sqlalchemy import delete` import.

## API Audit Summary (May 2026 — 3-hour deep-dive)
Comprehensive end-to-end testing of 60+ API endpoints against the live database. All findings:

### Confirmed Working (200/201/204)
Every endpoint called by `apps/web/src/lib/api-client.ts` returns correct responses:
- Auth: login, me, org, sync ✅
- Sites: CRUD, summary, pages, setup, opportunities, connection, verify, verify/check ✅
- Crawls: list, get, trigger, cancel (DELETE), SSE progress ✅
- Issues: list, aggregated, prioritized, root-cause-fix, get ✅
- Fixes: apply, rollback, versions ✅
- Connections: status, capabilities, test, save (PUT), remove, certify ✅
- Search Console: connect-url, status, sync (404 when not connected = correct), performance ✅
- Analytics: connect-url, status, sync (404 when not connected = correct), performance ✅
- PageSpeed: list, run ✅
- IndexNow: status, setup, submit (409 when not verified = correct) ✅
- Competitors: list, add, delete (FIXED), analyze, compare-pages ✅
- Keywords: list, create, delete, history, import, opportunities ✅
- Content Briefs: list, create, github-pr (403 when ownership not verified = correct) ✅
- AI Visibility: list, run ✅
- Autopilot: next-actions, run, digest/preview, digest/send ✅
- Agency: clients, create-client, get-client, assign-site ✅
- Notifications: list, mark-read, mark-all-read, preferences, update-preferences ✅
- Webhooks: list, create, update, delete, test, deliveries ✅
- API Keys: list, create (validates scopes), revoke ✅
- Team: list, invite, remove, update-role ✅
- Snippet: install-code, insights, collect ✅
- Reports: list, create, generate, digest/preview, share-link ✅
- GitHub: install-url, complete-install, repo-analysis ✅
- Dashboard: org/dashboard ✅
- Usage, Change-log, System readiness, Crawl budget ✅
- Proof, Autopilot, AI-Visibility, Integrations/certification ✅

### Confirmed Non-Bugs (expected behavior)
- `POST /sites/{id}/search-console/sync` → 404 "not connected" (site has no GSC) ✅
- `POST /sites/{id}/analytics/sync` → 404 "not connected" (site has no GA4) ✅
- `POST /sites/{id}/indexnow/submit` → 409 "key not verified" (correct gate) ✅
- `POST /fixes/apply` → 400 "no proposed fix" (issue has no AI fix yet) ✅
- `POST /fixes/rollback` → 400 "only deployed fixes" (issue is pending) ✅
- `POST /content-briefs/{id}/github-pr` → 403 "verify ownership first" (correct) ✅
- `GET /sites/{id}/github/repo-analysis` → 404 when site has no GitHub config ✅
- `GET crawl/progress` → SSE streaming (not JSON, correct) ✅
- `POST api-keys` with invalid scopes → 400 with scope list (correct validation) ✅

## Phase 2 — Crawler Build Plan v4 / Gap Analysis (April 2026)
Implemented from gap-analysis files:
- **Crawler**: URL normalization & dedup (`packages/crawler/url_utils.py`); SSRF protection (private/loopback IPs blocked); concurrent fetching with `asyncio.Semaphore(5)`; crawl cancellation via `DELETE /crawls/{id}` (worker checks DB status between batches of 25); HTTP status codes & response headers threaded through Jina layer; real broken-link tracking (4xx/5xx URLs persisted as zero-score pages).
- **Extractor**: page-type classification (homepage / product / article / utility / category) with type-aware thin-content thresholds; heading hierarchy violation detection (e.g. H1→H3 skip); non-modern image format detection (jpg/png without webp/avif fallback); HTTP-header signals (`X-Robots-Tag`, HSTS, `Link: rel=canonical`); new issue types: `http_404`, `server_error`, `blocked_content`, `heading_hierarchy_skip`, `non_modern_image_format`.
- **Crawl dispatch**: `POST /crawls` now actually triggers the crawl (Celery when `REDIS_URL` set, else FastAPI BackgroundTasks for dev).
- **Snippet**: collects INP & FCP (Gap 16 — Core Web Vitals since 2024), stored in `snippet_events.inp_ms / fcp_ms`; device-type detection (`device_type` column); History API patching for instant SPA detection; `pagehide` snapshot to capture final CLS; `data-sample` attribute for client-side sampling; respects `navigator.doNotTrack`.
- **Snippet endpoint**: in-process IP rate limit (120/min/IP), bot User-Agent filtering (Googlebot, SEMrush, curl, …), DNT honouring.
- **AI engine**: issue-specific prompt templates (Gap 21) for `missing_meta_description`, `title_too_short/long`, `missing_title`, `missing_h1`, `images_missing_alt_text`, `missing_canonical`, `missing_schema`, `meta_description_too_long`. Generic prompt is the fallback.
- **Lifespan migration**: additive `ALTER TABLE … ADD COLUMN IF NOT EXISTS` for new snippet columns runs on startup (no Alembic dependency).

Deferred (low-impact for current credit budget): robots.txt cache (Gap 2), conditional GET (Gap 5), crawl budget allocator (Gap 6), keyword cannibalization detection (Gap 13), fix versioning (Gap 22), verification delay (Gap 23), Claude rate limits (Gap 24), HMAC snippet tokens (Security 2), KMS encryption (Security 4).

## What's Needed Next (API Keys Required)
1. `ANTHROPIC_API_KEY` → enables real AI fix generation (stubs work without it)
2. `STRIPE_SECRET_KEY` → enables real billing enforcement
3. `DATAFORSEO_LOGIN` → enables live keyword rank tracking
4. `AHREFS_API_KEY` → enables backlink monitoring
5. `RESEND_API_KEY` → enables email notifications
