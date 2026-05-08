import ky from 'ky'
import { supabase } from './supabase'
import { SUPABASE_AUTH_ENABLED } from './auth-mode'
import { clearLocalAccessToken, getLocalAccessToken } from './auth-storage'

const API_BASE = typeof window !== 'undefined'
  ? window.location.origin
  : 'http://localhost:8001'

export const api = ky.extend({
  baseUrl: API_BASE,
  prefix: '/api/v1/',
  timeout: 30000,
  hooks: {
    beforeRequest: [
      async ({ request }) => {
        const token = SUPABASE_AUTH_ENABLED && supabase
          ? (await supabase.auth.getSession()).data.session?.access_token
          : getLocalAccessToken()
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`)
        }
      },
    ],
    afterResponse: [
      async ({ response }) => {
        if (response.status === 401) {
          if (SUPABASE_AUTH_ENABLED && supabase) {
            await supabase.auth.signOut()
          } else {
            clearLocalAccessToken()
          }
          if (typeof window === 'undefined') return
          const isAuthScreen = window.location.pathname === '/login' || window.location.pathname === '/signup'
          if (isAuthScreen) return
          window.location.href = '/login'
        }
      },
    ],
  },
})

// --- API Functions ---

// Auth
export const authApi = {
  getMe: () => api.get('auth/me').json<any>(),
  getOrg: () => api.get('auth/org').json<any>(),
  syncUser: (data: { full_name?: string; org_name?: string }) =>
    api.post('auth/sync', { json: data }).json<any>(),
}

export const systemApi = {
  readiness: () => api.get('system/readiness').json<any>(),
}

export const teamApi = {
  list: () => api.get('team').json<any>(),
}

// Sites
export const sitesApi = {
  list: (page = 1, perPage = 20) =>
    api.get('sites', { searchParams: { page, per_page: perPage } }).json<any>(),
  get: (id: string) => api.get(`sites/${id}`).json<any>(),
  summary: (id: string) => api.get(`sites/${id}/summary`).json<any>(),
  create: (data: any) => api.post('sites', { json: data }).json<any>(),
  update: (id: string, data: any) => api.patch(`sites/${id}`, { json: data }).json<any>(),
  delete: (id: string) => api.delete(`sites/${id}`).json<any>(),
  pageDetail: (siteId: string, pageId: string) =>
    api.get(`sites/${siteId}/pages/${pageId}`).json<any>(),
}

// Crawls
export const crawlsApi = {
  list: (siteId?: string, page = 1) =>
    api.get('crawls', { searchParams: { ...(siteId ? { site_id: siteId } : {}), page } }).json<any>(),
  get: (id: string) => api.get(`crawls/${id}`).json<any>(),
  trigger: (siteId: string) =>
    api.post('crawls', { json: { site_id: siteId, trigger: 'manual' } }).json<any>(),
  diff: (crawlId: string) => api.get(`crawls/${crawlId}/diff`).json<any>(),
}

// Issues
export const issuesApi = {
  list: (params: Record<string, any> = {}) =>
    api.get('issues', { searchParams: params }).json<any>(),
  aggregated: (params: Record<string, any> = {}) =>
    api.get('issues/aggregated', { searchParams: params }).json<any>(),
  rootCauseFix: (data: { site_id: string; issue_type: string; mode?: 'plan' | 'ai_preview' | 'github_pr'; business_context?: Record<string, any> }) =>
    api.post('issues/root-cause-fix', { json: data }).json<any>(),
  get: (id: string) => api.get(`issues/${id}`).json<any>(),
  prioritizedIssues: (siteId: string) =>
    api.get('issues/prioritized', { searchParams: { site_id: siteId } }).json<any>(),
}

export const dashboardApi = {
  overview: () => api.get('org/dashboard').json<any>(),
}

// Fixes
export const fixesApi = {
  apply: (issueId: string) =>
    api.post('fixes/apply', { json: { issue_id: issueId, approved: true } }).json<any>(),
  rollback: (issueId: string) =>
    api.post('fixes/rollback', { json: { issue_id: issueId } }).json<any>(),
}

// Connections (per-site CMS credentials)
export type ConnectionType = 'crawler' | 'snippet' | 'wordpress' | 'shopify' | 'webflow' | 'github'

export interface ConnectionPayload {
  connection_type: ConnectionType
  sandbox?: boolean
  site_url?: string
  username?: string
  app_password?: string
  shop_domain?: string
  access_token?: string
  site_id?: string
  token?: string
  owner?: string
  repo?: string
  github_token?: string
  branch?: string
  project_root?: string
  build_command?: string
  package_manager?: string
}

export const connectionsApi = {
  status: (siteId: string) =>
    api.get(`sites/${siteId}/connection`).json<any>(),
  capabilities: (siteId: string) =>
    api.get(`sites/${siteId}/connection/capabilities`).json<any>(),
  test: (siteId: string, payload: ConnectionPayload) =>
    api.post(`sites/${siteId}/connection/test`, { json: payload }).json<any>(),
  save: (siteId: string, payload: ConnectionPayload) =>
    api.put(`sites/${siteId}/connection`, { json: payload }).json<any>(),
  remove: (siteId: string) =>
    api.delete(`sites/${siteId}/connection`),
  certify: (siteId: string, connectionType: ConnectionType, data: any) =>
    api.post(`sites/${siteId}/connections/${connectionType}/certify`, { json: data }).json<any>(),
  certificationDashboard: () =>
    api.get('integrations/certification').json<any>(),
}

export const githubApi = {
  installUrl: (siteId: string) =>
    api.get('github/app/install-url', { searchParams: { site_id: siteId } }).json<any>(),
  completeInstall: (data: {
    site_id: string
    installation_id: number
    owner: string
    repo: string
    branch?: string
    project_root?: string
    build_command?: string
    package_manager?: string
  }) => api.post('github/app/complete-install', { json: data }).json<any>(),
  repoAnalysis: (siteId: string) =>
    api.get(`sites/${siteId}/github/repo-analysis`).json<any>(),
}

export const snippetApi = {
  installCode: (siteId: string) =>
    api.get('snippet/install-code', { searchParams: { site_id: siteId } }).json<any>(),
  insights: (siteId: string) =>
    api.get('snippet/insights', { searchParams: { site_id: siteId } }).json<any>(),
}

export const searchConsoleApi = {
  connectUrl: (siteId: string) =>
    api.get('google/search-console/connect-url', { searchParams: { site_id: siteId } }).json<any>(),
  status: (siteId: string) =>
    api.get(`sites/${siteId}/search-console/status`).json<any>(),
  sync: (siteId: string, data: { days?: number; inspect_limit?: number } = {}) =>
    api.post(`sites/${siteId}/search-console/sync`, { json: data }).json<any>(),
  performance: (siteId: string) =>
    api.get(`sites/${siteId}/search-console/performance`).json<any>(),
}

export const analyticsApi = {
  connectUrl: (siteId: string, propertyId?: string) =>
    api.get('google/analytics/connect-url', { searchParams: { site_id: siteId, ...(propertyId ? { property_id: propertyId } : {}) } }).json<any>(),
  status: (siteId: string) =>
    api.get(`sites/${siteId}/analytics/status`).json<any>(),
  sync: (siteId: string, data: { days?: number } = {}) =>
    api.post(`sites/${siteId}/analytics/sync`, { json: data }).json<any>(),
  performance: (siteId: string) =>
    api.get(`sites/${siteId}/analytics/performance`).json<any>(),
}

export const pageSpeedApi = {
  list: (siteId: string) => api.get(`sites/${siteId}/pagespeed`).json<any>(),
  run: (siteId: string, data: { urls?: string[]; strategies?: string[] } = {}) =>
    api.post(`sites/${siteId}/pagespeed/run`, { json: data }).json<any>(),
}

export const indexNowApi = {
  status: (siteId: string) => api.get(`sites/${siteId}/indexnow/status`).json<any>(),
  setup: (siteId: string) => api.post(`sites/${siteId}/indexnow/setup`).json<any>(),
  submit: (siteId: string, urls: string[]) =>
    api.post(`sites/${siteId}/indexnow/submit`, { json: { urls } }).json<any>(),
}

export const opportunitiesApi = {
  site: (siteId: string) =>
    api.get(`sites/${siteId}/opportunities`).json<any>(),
  prioritizedIssues: (siteId: string) =>
    api.get('issues/prioritized', { searchParams: { site_id: siteId } }).json<any>(),
}

export const proofApi = {
  site: (siteId: string) => api.get(`sites/${siteId}/proof`).json<any>(),
}

export const autopilotApi = {
  nextActions: (siteId?: string) =>
    api.get('autopilot/next-actions', { searchParams: siteId ? { site_id: siteId } : {} }).json<any>(),
  run: (data: { site_id?: string; run_type?: string; create_snapshot?: boolean } = {}) =>
    api.post('autopilot/run', { json: data }).json<any>(),
  digestPreview: (siteId: string) =>
    api.get(`sites/${siteId}/digest/preview`).json<any>(),
  digestSend: (siteId: string) =>
    api.post(`sites/${siteId}/digest/send`).json<any>(),
}

export const aiVisibilityApi = {
  list: (siteId: string) => api.get(`sites/${siteId}/ai-visibility`).json<any>(),
  run: (siteId: string, data: { prompt: string; target_entity?: string; competitor_domains?: string[] }) =>
    api.post(`sites/${siteId}/ai-visibility/run`, { json: data }).json<any>(),
}

export const contentBriefsApi = {
  list: (siteId: string) => api.get('content-briefs', { searchParams: { site_id: siteId } }).json<any>(),
  create: (data: { site_id: string; page_url: string; target_keyword?: string; title?: string }) =>
    api.post('content-briefs', { json: data }).json<any>(),
  createGithubPr: (id: string) =>
    api.post(`content-briefs/${id}/github-pr`).json<any>(),
}

export const crawlBudgetApi = {
  importLogs: (siteId: string, data: { filename?: string; raw_log: string }) =>
    api.post(`sites/${siteId}/logs/import`, { json: data }).json<any>(),
  summary: (siteId: string) =>
    api.get(`sites/${siteId}/crawl-budget`).json<any>(),
}

export const agencyApi = {
  clients: () => api.get('agency/clients').json<any>(),
  createClient: (data: { name: string; contact_email?: string; brand_name?: string; logo_url?: string }) =>
    api.post('agency/clients', { json: data }).json<any>(),
  getClient: (id: string) => api.get(`agency/clients/${id}`).json<any>(),
  assignSite: (id: string, siteId: string) =>
    api.post(`agency/clients/${id}/sites`, { json: { site_id: siteId } }).json<any>(),
}

export const reportsApi = {
  list: () => api.get('reports').json<any>(),
  create: (data: any) => api.post('reports', { json: data }).json<any>(),
  generate: (data: any) => api.post('reports/generate', { json: data }).json<any>(),
  digestPreview: (siteId?: string) =>
    api.get('reports/digest/preview', { searchParams: siteId ? { site_id: siteId } : {} }).json<any>(),
  shareLink: (data: any) => api.post('reports/share-link', { json: data }).json<any>(),
}

export const keywordProviderApi = {
  sync: (data: { site_id: string; provider?: string }) =>
    api.post('keywords/sync-provider', { json: data }).json<any>(),
  opportunities: (siteId: string) =>
    api.get('keywords/opportunities', { searchParams: { site_id: siteId } }).json<any>(),
}

export const notificationsApi = {
  list: () => api.get('notifications').json<any>(),
  markRead: (id: string) => api.post(`notifications/${id}/read`).json<any>(),
  markAllRead: () => api.post('notifications/read-all').json<any>(),
  preferences: () => api.get('notifications/preferences').json<any>(),
  updatePreferences: (data: any) => api.put('notifications/preferences', { json: data }).json<any>(),
}

export const webhooksApi = {
  list: () => api.get('webhooks').json<any>(),
  create: (data: any) => api.post('webhooks', { json: data }).json<any>(),
  update: (id: string, data: { name?: string; url?: string; events?: string[]; enabled?: boolean }) =>
    api.patch(`webhooks/${id}`, { json: data }).json<any>(),
  delete: (id: string) => api.delete(`webhooks/${id}`),
  test: (id: string) => api.post(`webhooks/${id}/test`).json<any>(),
  deliveries: (id: string) => api.get(`webhooks/${id}/deliveries`).json<any>(),
}

export const competitorsApi = {
  list: (siteId: string) =>
    api.get('competitors', { searchParams: { site_id: siteId } }).json<any>(),
  add: (data: { site_id: string; domain: string; name?: string }) =>
    api.post('competitors', { json: data }).json<any>(),
  delete: (id: string) => api.delete(`competitors/${id}`),
  analyze: (id: string) => api.post(`competitors/${id}/analyze`).json<any>(),
  comparePages: (id: string, data: { site_page_url: string; competitor_page_url: string }) =>
    api.post(`competitors/${id}/compare-pages`, { json: data }).json<any>(),
}

export const keywordsApi = {
  list: (siteId: string) =>
    api.get('keywords', { searchParams: { site_id: siteId } }).json<any>(),
  create: (data: { site_id: string; keyword: string; target_url?: string; intent?: string; priority?: number }) =>
    api.post('keywords', { json: data }).json<any>(),
  delete: (id: string) => api.delete(`keywords/${id}`),
  history: (id: string) => api.get(`keywords/${id}/history`).json<any>(),
  import: (data: { site_id: string; csv_text: string }) =>
    api.post('keywords/import', { json: data }).json<any>(),
  opportunities: (siteId: string) =>
    api.get('keywords/opportunities', { searchParams: { site_id: siteId } }).json<any>(),
}

export const siteIntelligenceApi = {
  seoScoreHistory: (siteId: string, limit = 30) =>
    api.get(`sites/${siteId}/seo-score-history`, { searchParams: { limit } }).json<any>(),
  healthTrends: (siteId: string, limit = 20) =>
    api.get(`sites/${siteId}/health-trends`, { searchParams: { limit } }).json<any>(),
  orphanPages: (siteId: string, page = 1, perPage = 50) =>
    api.get(`sites/${siteId}/orphan-pages`, { searchParams: { page, per_page: perPage } }).json<any>(),
  duplicateAnalysis: (siteId: string) =>
    api.get(`sites/${siteId}/duplicate-analysis`).json<any>(),
  redirectChains: (siteId: string, page = 1) =>
    api.get(`sites/${siteId}/redirect-chains`, { searchParams: { page } }).json<any>(),
  internalLinking: (siteId: string, page = 1) =>
    api.get(`sites/${siteId}/internal-linking`, { searchParams: { page } }).json<any>(),
  pagespeedTrend: (siteId: string, strategy: 'mobile' | 'desktop' = 'mobile') =>
    api.get(`sites/${siteId}/pagespeed-trend`, { searchParams: { strategy } }).json<any>(),
  coverageGaps: (siteId: string) =>
    api.get(`sites/${siteId}/coverage-gaps`).json<any>(),
  pageDetail: (siteId: string, pageId: string) =>
    api.get(`sites/${siteId}/pages/${pageId}`).json<any>(),
}

export const issuesBulkApi = {
  bulkDismiss: (issueIds: string[], reason?: string) =>
    api.post('issues/bulk-dismiss', { json: { issue_ids: issueIds, reason } }).json<any>(),
}

export const changeLogApi = {
  list: (siteId?: string, page = 1, perPage = 30) =>
    api.get('change-log', { searchParams: { ...(siteId ? { site_id: siteId } : {}), page, per_page: perPage } }).json<any>(),
}

export const fixVersionsApi = {
  list: (issueId: string) => api.get(`fixes/versions/${issueId}`).json<any>(),
}

// Alias for pages that import apiClient directly
export const apiClient = api
