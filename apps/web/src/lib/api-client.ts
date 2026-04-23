import ky from 'ky'
import { supabase } from './supabase'

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
        const { data: { session } } = await supabase.auth.getSession()
        const token = session?.access_token
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`)
        }
      },
    ],
    afterResponse: [
      async ({ response }) => {
        if (response.status === 401) {
          await supabase.auth.signOut()
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

// Sites
export const sitesApi = {
  list: (page = 1, perPage = 20) =>
    api.get('sites', { searchParams: { page, per_page: perPage } }).json<any>(),
  get: (id: string) => api.get(`sites/${id}`).json<any>(),
  create: (data: any) => api.post('sites', { json: data }).json<any>(),
  update: (id: string, data: any) => api.patch(`sites/${id}`, { json: data }).json<any>(),
  delete: (id: string) => api.delete(`sites/${id}`),
}

// Crawls
export const crawlsApi = {
  list: (siteId?: string, page = 1) =>
    api.get('crawls', { searchParams: { ...(siteId ? { site_id: siteId } : {}), page } }).json<any>(),
  get: (id: string) => api.get(`crawls/${id}`).json<any>(),
  trigger: (siteId: string) =>
    api.post('crawls', { json: { site_id: siteId, trigger: 'manual' } }).json<any>(),
}

// Issues
export const issuesApi = {
  list: (params: Record<string, any> = {}) =>
    api.get('issues', { searchParams: params }).json<any>(),
  get: (id: string) => api.get(`issues/${id}`).json<any>(),
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
}

export const connectionsApi = {
  status: (siteId: string) =>
    api.get(`sites/${siteId}/connection`).json<any>(),
  test: (siteId: string, payload: ConnectionPayload) =>
    api.post(`sites/${siteId}/connection/test`, { json: payload }).json<any>(),
  save: (siteId: string, payload: ConnectionPayload) =>
    api.put(`sites/${siteId}/connection`, { json: payload }).json<any>(),
  remove: (siteId: string) =>
    api.delete(`sites/${siteId}/connection`),
}

export const snippetApi = {
  installCode: (siteId: string) =>
    api.get('snippet/install-code', { searchParams: { site_id: siteId } }).json<any>(),
}

export const reportsApi = {
  list: () => api.get('reports').json<any>(),
  create: (data: any) => api.post('reports', { json: data }).json<any>(),
  generate: (data: any) => api.post('reports/generate', { json: data }).json<any>(),
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
  test: (id: string) => api.post(`webhooks/${id}/test`).json<any>(),
  deliveries: (id: string) => api.get(`webhooks/${id}/deliveries`).json<any>(),
}

// Alias for pages that import apiClient directly
export const apiClient = api
