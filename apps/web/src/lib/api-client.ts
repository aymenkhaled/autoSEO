import ky from 'ky'
import { supabase } from './supabase'

const API_BASE = '/api'

export const api = ky.extend({
  prefix: API_BASE,
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

// Fixes
export const fixesApi = {
  apply: (issueId: string) =>
    api.post('fixes/apply', { json: { issue_id: issueId, approved: true } }).json<any>(),
  rollback: (issueId: string) =>
    api.post('fixes/rollback', { json: { issue_id: issueId } }).json<any>(),
}

// Alias for pages that import apiClient directly
export const apiClient = api
