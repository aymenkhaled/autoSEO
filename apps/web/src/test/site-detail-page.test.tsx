import { fireEvent, screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Route, Routes, MemoryRouter } from 'react-router'
import { vi } from 'vitest'

import SiteDetailPage from '@/pages/SiteDetailPage'

const getSiteMock = vi.fn()
const summaryMock = vi.fn()
const aggregatedMock = vi.fn()
const listIssuesMock = vi.fn()
const connectionStatusMock = vi.fn()
const installCodeMock = vi.fn()
const snippetInsightsMock = vi.fn()
const searchConsoleStatusMock = vi.fn()
const searchConsolePerformanceMock = vi.fn()
const analyticsStatusMock = vi.fn()
const analyticsPerformanceMock = vi.fn()
const pageSpeedListMock = vi.fn()
const indexNowStatusMock = vi.fn()
const opportunitiesSiteMock = vi.fn()
const apiGetMock = vi.fn()

vi.mock('@/lib/api-client', () => ({
  api: {
    get: (...args: any[]) => apiGetMock(...args),
    post: vi.fn(() => ({ json: vi.fn() })),
  },
  sitesApi: {
    get: (...args: any[]) => getSiteMock(...args),
    summary: (...args: any[]) => summaryMock(...args),
  },
  issuesApi: {
    aggregated: (...args: any[]) => aggregatedMock(...args),
    list: (...args: any[]) => listIssuesMock(...args),
  },
  connectionsApi: {
    status: (...args: any[]) => connectionStatusMock(...args),
  },
  snippetApi: {
    installCode: (...args: any[]) => installCodeMock(...args),
    insights: (...args: any[]) => snippetInsightsMock(...args),
  },
  searchConsoleApi: {
    status: (...args: any[]) => searchConsoleStatusMock(...args),
    performance: (...args: any[]) => searchConsolePerformanceMock(...args),
    connectUrl: vi.fn(),
    sync: vi.fn(),
  },
  analyticsApi: {
    status: (...args: any[]) => analyticsStatusMock(...args),
    performance: (...args: any[]) => analyticsPerformanceMock(...args),
    connectUrl: vi.fn(),
    sync: vi.fn(),
  },
  pageSpeedApi: {
    list: (...args: any[]) => pageSpeedListMock(...args),
    run: vi.fn(),
  },
  indexNowApi: {
    status: (...args: any[]) => indexNowStatusMock(...args),
    setup: vi.fn(),
    submit: vi.fn(),
  },
  opportunitiesApi: {
    site: (...args: any[]) => opportunitiesSiteMock(...args),
    prioritizedIssues: vi.fn(),
  },
}))

vi.mock('@/components/sites/DeleteSiteDialog', () => ({
  DeleteSiteDialog: () => null,
}))

vi.mock('@/lib/utils', () => ({
  formatRelativeTime: () => 'just now',
}))

vi.mock('@/lib/supabase', () => ({
  supabase: null,
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <MemoryRouter initialEntries={['/dashboard/sites/site-123']}>
      <QueryClientProvider client={queryClient}>
        <Routes>
          <Route path="/dashboard/sites/:id" element={<SiteDetailPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('SiteDetailPage workspace tabs', () => {
  it('renders setup and audit tabs with grouped issues', async () => {
    getSiteMock.mockResolvedValue({
      id: 'site-123',
      name: 'Strategy',
      domain: 'https://strategy.test',
      ownership_verified: false,
      last_crawled_at: null,
    })
    summaryMock.mockResolvedValue({
      site: { id: 'site-123', name: 'Strategy', domain: 'https://strategy.test' },
      latest_crawl: { seo_score: 47 },
      metrics: { pages_count: 10, open_issues: 30, deployed_fixes: 0 },
      setup: {
        state: 'setup_required',
        label: 'Verification required',
        description: 'Verify ownership before trust-sensitive actions.',
        steps: [],
      },
      connection: {
        monitoring_mode: 'crawler',
        monitoring_mode_label: 'Crawler',
        write_integration_label: 'Not configured',
        readiness: 'monitoring_only',
        readiness_label: 'Monitoring only',
        explanation: 'AutoSEO can monitor but not deploy changes.',
      },
      audit_note: 'Use grouped root causes to judge real change.',
    })
    aggregatedMock.mockResolvedValue({
      groups: [
        {
          type: 'spa_no_prerender',
          category: 'rendering',
          title: 'Pages are rendering as empty SPA shells',
          summary: 'Grouped issue summary',
          why_it_matters: 'Search engines may see empty pages.',
          recommended_fix: 'Add prerendering or SSR.',
          count: 10,
          examples: [{ url: 'https://strategy.test/pricing' }],
        },
      ],
    })
    listIssuesMock.mockResolvedValue({ issues: [] })
    connectionStatusMock.mockResolvedValue({
      monitoring_mode: 'crawler',
      monitoring_mode_label: 'Crawler',
      write_integration_label: 'Not configured',
      readiness: 'monitoring_only',
      readiness_label: 'Monitoring only',
      explanation: 'AutoSEO can monitor but not deploy changes.',
    })
    installCodeMock.mockResolvedValue({})
    snippetInsightsMock.mockResolvedValue({ status: 'no_data', insights: [] })
    searchConsoleStatusMock.mockResolvedValue({ connected: false, configured: false, totals: { impressions: 0, clicks: 0, ctr: 0 } })
    searchConsolePerformanceMock.mockResolvedValue({ totals: { impressions: 0, clicks: 0, ctr: 0 } })
    analyticsStatusMock.mockResolvedValue({ connected: false, configured: false, totals: { sessions: 0, key_events: 0, total_revenue: 0 } })
    analyticsPerformanceMock.mockResolvedValue({ totals: { sessions: 0, key_events: 0, total_revenue: 0 } })
    pageSpeedListMock.mockResolvedValue({ summary: {}, runs: [] })
    indexNowStatusMock.mockResolvedValue({ configured: false, verified: false })
    opportunitiesSiteMock.mockResolvedValue({ opportunities: [] })
    apiGetMock.mockImplementation((path: string) => {
      if (path === 'sites/site-123/pages') return { json: async () => ({ pages: [], crawl_context: { monitoring_mode: 'crawler' } }) }
      if (path === 'crawls') return { json: async () => ({ crawls: [] }) }
      return { json: async () => ({}) }
    })

    renderPage()

    expect(await screen.findByText(/Workspace status/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Audit' }))

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Root causes/i })).toBeInTheDocument()
      expect(screen.getByText(/Pages are rendering as empty SPA shells/i)).toBeInTheDocument()
    })
  })
})
