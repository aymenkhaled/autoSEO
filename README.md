# AutoSEO

AutoSEO is a `FastAPI + React + Postgres` SEO operations app for crawling sites, grouping root-cause issues, reviewing fixes, and managing integrations.

## Local Modes

The app supports two browser auth modes:

- `Supabase auth`: enabled when `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set in `apps/web/.env.local`.
- `Local JWT auth`: used automatically when those frontend Supabase vars are missing. The React app uses the FastAPI `register/login/me` routes instead.

## Files You Need

- Root backend env: [`.env.example`](/C:/Users/khale/Desktop/alexis%20project/autoSEO/.env.example)
- Frontend env example: [`apps/web/.env.local.example`](/C:/Users/khale/Desktop/alexis%20project/autoSEO/apps/web/.env.local.example)

Copy them to:

- `C:\Users\khale\Desktop\alexis project\autoSEO\.env`
- `C:\Users\khale\Desktop\alexis project\autoSEO\apps\web\.env.local`

## Minimum Local Setup

### 1. Start local services

Docker is only used here to provide Postgres and Redis locally:

```powershell
docker compose -f infra/docker-compose.yml up -d postgres redis
```

### 2. Install dependencies

Backend:

```powershell
python -m pip install -r apps/api/requirements.txt
```

Frontend:

```powershell
cd apps/web
npm install
```

### 3. Configure env

For easiest local testing, use local auth and local Postgres first.

Root `.env`:

```env
DATABASE_URL=postgresql://autoseo:devpassword@localhost:5432/autoseo_dev
REDIS_URL=redis://localhost:6379/0
SUPABASE_JWT_SECRET=super-secret-jwt-token-for-local-dev-minimum-32-chars-long!!
FRONTEND_URL=http://127.0.0.1:5000
API_URL=http://127.0.0.1:8000
ENVIRONMENT=development
DEBUG=true

# Optional but required for AI-powered GitHub PR fixes
ANTHROPIC_API_KEY=
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_APP_SLUG=
GITHUB_WEBHOOK_SECRET=
```

Frontend `apps/web/.env.local`:

```env
# Leave Supabase vars empty to use local JWT auth in the browser.
```

If you want Supabase browser auth instead, add:

```env
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
```

## Run The App

### Option A: Vite frontend + FastAPI backend

Backend:

```powershell
cd apps/api
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd apps/web
npm run dev
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

### Option B: Built frontend served by FastAPI

```powershell
cd apps/web
npm run build
cd ..\api
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Open [http://127.0.0.1:8001](http://127.0.0.1:8001).

## Smoke Test Flow

### Local-auth flow

1. Open the app.
2. Create an account with email/password.
3. Confirm you land in the dashboard without any Supabase browser env.
4. Add a site.
5. Open the site workspace and review the `Setup / Audit / Pages / Fixes` tabs.
6. Run a crawl.
7. Confirm grouped issues appear.
8. Open `Fixes` and confirm AI readiness is truthful if Anthropic is not configured.
9. Open `Reports`, `Team`, and `Billing` and confirm readiness states are honest.
10. Create an API key and call the API from the examples shown in the UI.

### Diamond business-impact flow

1. Crawl a site first so AutoSEO has pages and grouped root causes.
2. Open the site `Setup` tab and connect Search Console for clicks, impressions, CTR, and indexing.
3. Connect GA4 by opening the GA4 connect URL, then complete the callback with the numeric GA4 property ID.
4. Run `Sync 90 days` for Search Console and GA4.
5. Run `PageSpeed` for mobile/desktop checks on the top pages.
6. Prepare `IndexNow`, upload the generated key file to the site root, then run setup again to verify it.
7. Open the site `Audit` tab and confirm `Next best opportunities` now mixes crawler issues, GSC demand, GA4 revenue, PageSpeed/Core Web Vitals, and IndexNow readiness.
8. Open `Reports`, generate an on-demand report, then use `Digest Preview` and `Share Link` to review the weekly client-facing action summary.
9. Open `Keywords`, paste a CSV with `keyword,position,previous_position,volume,url,country,device,date`, and confirm ranking history appears.
10. Open `Competitors`, add a competitor, then run page-vs-page comparison against one crawled page.

### AI-powered GitHub PR flow

1. Add a site and run a crawl.
2. Open the site `Audit` tab and review grouped root causes.
3. Generate the ownership verification meta tag, add it to the site's `<head>`, deploy once, then click `Check Verification`.
4. Open `Integrations`, choose the site, and select `GitHub`.
5. Preferred SaaS path: install the AutoSEO GitHub App on one selected repo, paste the installation ID plus owner/repo/branch/project root/build command, then complete setup.
6. Advanced fallback: use a fine-grained GitHub token limited to one repo with Contents and Pull Requests read/write.
7. Return to the site `Audit` tab, click `Preview AI fix`, review risk/files/missing data, then click `Create GitHub PR`.
8. Review and merge the PR in GitHub, deploy the site, then crawl again. AutoSEO should treat the fix as proven only after the recrawl removes the issue group.

### Verification commands

Backend compile/import:

```powershell
C:\Python313\python.exe -m compileall apps/api packages workers
C:\Python313\python.exe -c "import sys; sys.path.insert(0, 'apps/api'); import main; print('import-ok')"
```

Frontend build:

```powershell
cd apps/web
npm run build
```

## Notes

- Redis is optional for basic browsing, but background workers and queue-backed flows use it when available.
- Stripe checkout/portal, PDF rendering, and invite delivery remain intentionally deferred until they are fully wired. Weekly digest email can send through Resend when `RESEND_API_KEY` is configured and workers are running.
- AI fix generation requires `ANTHROPIC_API_KEY`. Without it, the app now shows readiness states instead of fake placeholder fixes.
- GA4 uses the Google Analytics Data API with read-only `analytics.readonly` scope. Search Console remains read-only too.
- PageSpeed checks use the PageSpeed Insights endpoint and optional CrUX API key for real-user field metrics.
- IndexNow submissions stay blocked until the generated key file is publicly verified on the site host.
