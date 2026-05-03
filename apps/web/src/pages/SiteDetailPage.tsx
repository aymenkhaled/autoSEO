import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { motion } from 'framer-motion'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Brain,
  CheckCircle2,
  ExternalLink,
  Globe,
  Layers3,
  Link2,
  Loader2,
  RefreshCw,
  Settings2,
  Shield,
  Sparkles,
  TrendingUp,
  Trash2,
} from 'lucide-react'

import { DeleteSiteDialog } from '@/components/sites/DeleteSiteDialog'
import { analyticsApi, api, changeLogApi, connectionsApi, indexNowApi, issuesApi, opportunitiesApi, pageSpeedApi, searchConsoleApi, sitesApi, snippetApi } from '@/lib/api-client'
import { SUPABASE_AUTH_ENABLED } from '@/lib/auth-mode'
import { getLocalAccessToken } from '@/lib/auth-storage'
import { readinessMeta } from '@/lib/readiness'
import { supabase } from '@/lib/supabase'
import { formatRelativeTime } from '@/lib/utils'

const TABS = [
  { id: 'setup', label: 'Setup' },
  { id: 'audit', label: 'Audit' },
  { id: 'pages', label: 'Pages' },
  { id: 'fixes', label: 'Fixes' },
  { id: 'log', label: 'Change Log' },
] as const

const ISSUE_TYPE_LABELS: Record<string, string> = {
  spa_no_prerender: 'SPA Not Prerendered',
  duplicate_title: 'Duplicate Page Title',
  keyword_cannibalization: 'Keyword Cannibalization',
  stale_schema_date: 'Expired Schema Date',
  unverified_review_schema: 'Review Schema Needs Proof',
  missing_sitemap: 'Missing Sitemap',
  missing_robots: 'Missing Robots',
  missing_offer_schema: 'Missing Offer Schema',
  broken_og_image: 'Broken OG Image',
  missing_title: 'Missing Page Title',
  title_too_short: 'Title Too Short',
  title_too_long: 'Title Too Long',
  missing_meta_description: 'Missing Meta Description',
  meta_description_too_long: 'Meta Description Too Long',
  missing_h1: 'Missing H1 Tag',
  multiple_h1: 'Multiple H1 Tags',
  images_missing_alt_text: 'Images Missing Alt Text',
  missing_schema: 'Missing Structured Data',
  missing_canonical: 'Missing Canonical URL',
  missing_charset: 'Missing Charset Declaration',
  thin_content: 'Thin Content',
  short_title: 'Title Too Short',
  long_title: 'Title Too Long',
  short_meta_description: 'Meta Description Too Short',
  long_meta_description: 'Meta Description Too Long',
  duplicate_meta_description: 'Duplicate Meta Description',
  canonical_mismatch: 'Canonical URL Mismatch',
  broken_link: 'Broken Link',
  redirect_chain: 'Redirect Chain',
  slow_page: 'Slow Page Speed',
  large_image: 'Unoptimised Image',
  missing_alt_text: 'Missing Alt Text',
  duplicate_content: 'Duplicate Content',
  noindex_page: 'Noindex Directive',
}

type TabId = typeof TABS[number]['id']

function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-sm text-muted-foreground">-</span>
  const color = score >= 80
    ? 'text-green-500 bg-green-500/10 border-green-500/20'
    : score >= 60
      ? 'text-amber-500 bg-amber-500/10 border-amber-500/20'
      : 'text-red-500 bg-red-500/10 border-red-500/20'
  return <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-sm font-bold border ${color}`}>{score}</span>
}

function TinyPill({ label, className }: { label: string; className?: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-semibold ${className ?? 'bg-muted text-muted-foreground border-border'}`}>
      {label}
    </span>
  )
}

function useCrawlProgress(crawlId: string | null) {
  const [progress, setProgress] = useState<any | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)

  useEffect(() => {
    if (!crawlId) {
      setProgress(null)
      setStreamError(null)
      return
    }

    let cancelled = false
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null

    const run = async () => {
      const token = SUPABASE_AUTH_ENABLED && supabase
        ? (await supabase.auth.getSession()).data.session?.access_token
        : getLocalAccessToken()
      const response = await fetch(`${window.location.origin}/api/v1/crawls/${crawlId}/progress`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok || !response.body) {
        throw new Error('Progress stream could not be opened.')
      }

      reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (!cancelled) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''

        for (const chunk of chunks) {
          const dataLine = chunk.split('\n').find((line) => line.startsWith('data: '))
          if (!dataLine) continue
          const payload = JSON.parse(dataLine.slice(6))
          if (!cancelled) setProgress(payload)
        }
      }
    }

    run().catch((error: any) => {
      if (!cancelled) setStreamError(error?.message || 'Progress stream failed.')
    })

    return () => {
      cancelled = true
      reader?.cancel().catch(() => undefined)
    }
  }, [crawlId])

  return { progress, streamError }
}

export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = (searchParams.get('tab') as TabId) || 'setup'
  const [tab, setTab] = useState<TabId>(TABS.some((item) => item.id === initialTab) ? initialTab : 'setup')
  const [activeCrawlId, setActiveCrawlId] = useState<string | null>(null)
  const [showDelete, setShowDelete] = useState(false)
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null)
  const [crawlLimit, setCrawlLimit] = useState('500')
  const [crawlFrequency, setCrawlFrequency] = useState('weekly')
  const [respectRobots, setRespectRobots] = useState(true)
  const [crawlDelayMs, setCrawlDelayMs] = useState('1000')
  const [workflowPanel, setWorkflowPanel] = useState<any | null>(null)
  const [gaPropertyId, setGaPropertyId] = useState('')
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null)

  const siteQuery = useQuery({
    queryKey: ['site', id],
    queryFn: () => sitesApi.get(id!),
    enabled: !!id,
  })

  const summaryQuery = useQuery({
    queryKey: ['site-summary', id],
    queryFn: () => sitesApi.summary(id!),
    enabled: !!id,
  })

  const groupedIssuesQuery = useQuery({
    queryKey: ['site-issues-grouped', id],
    queryFn: () => issuesApi.aggregated({ site_id: id!, fix_status: 'pending' }),
    enabled: !!id,
  })

  const rawIssuesQuery = useQuery({
    queryKey: ['site-issues-raw', id],
    queryFn: () => issuesApi.list({ site_id: id!, per_page: 20 }),
    enabled: !!id,
  })

  const pagesQuery = useQuery({
    queryKey: ['site-pages', id],
    queryFn: () => api.get(`sites/${id}/pages`).json<any>(),
    enabled: !!id,
  })

  const pageDetailQuery = useQuery({
    queryKey: ['page-detail', id, selectedPageId],
    queryFn: () => sitesApi.pageDetail(id!, selectedPageId!),
    enabled: !!id && !!selectedPageId,
  })

  const connectionQuery = useQuery({
    queryKey: ['site-connection', id],
    queryFn: () => connectionsApi.status(id!),
    enabled: !!id,
  })

  const activeCrawlQuery = useQuery({
    queryKey: ['site-active-crawl', id],
    queryFn: () => api.get('crawls', { searchParams: { site_id: id!, page: 1, per_page: 5 } }).json<any>(),
    enabled: !!id,
  })

  const snippetInstallQuery = useQuery({
    queryKey: ['snippet-install', id],
    queryFn: () => snippetApi.installCode(id!),
    enabled: !!id && connectionQuery.data?.monitoring_mode === 'snippet',
  })

  const searchConsoleStatusQuery = useQuery({
    queryKey: ['search-console-status', id],
    queryFn: () => searchConsoleApi.status(id!),
    enabled: !!id,
  })

  const searchConsolePerformanceQuery = useQuery({
    queryKey: ['search-console-performance', id],
    queryFn: () => searchConsoleApi.performance(id!),
    enabled: !!id && !!searchConsoleStatusQuery.data?.connected,
  })

  const analyticsStatusQuery = useQuery({
    queryKey: ['analytics-status', id],
    queryFn: () => analyticsApi.status(id!),
    enabled: !!id,
  })

  const analyticsPerformanceQuery = useQuery({
    queryKey: ['analytics-performance', id],
    queryFn: () => analyticsApi.performance(id!),
    enabled: !!id && !!analyticsStatusQuery.data?.connected,
  })

  const pageSpeedQuery = useQuery({
    queryKey: ['pagespeed', id],
    queryFn: () => pageSpeedApi.list(id!),
    enabled: !!id,
  })

  const indexNowQuery = useQuery({
    queryKey: ['indexnow', id],
    queryFn: () => indexNowApi.status(id!),
    enabled: !!id,
  })

  const opportunitiesQuery = useQuery({
    queryKey: ['site-opportunities', id],
    queryFn: () => opportunitiesApi.site(id!),
    enabled: !!id,
  })

  const snippetInsightsQuery = useQuery({
    queryKey: ['snippet-insights', id],
    queryFn: () => snippetApi.insights(id!),
    enabled: !!id,
  })

  const changeLogQuery = useQuery({
    queryKey: ['site-change-log', id],
    queryFn: () => changeLogApi.list(id!),
    enabled: !!id && tab === 'log',
  })

  const connectionCapabilitiesQuery = useQuery({
    queryKey: ['connection-capabilities', id],
    queryFn: () => connectionsApi.capabilities(id!),
    enabled: !!id,
  })

  const latestCrawlId = summaryQuery.data?.latest_crawl?.id
  const crawlDiffQuery = useQuery({
    queryKey: ['crawl-diff', latestCrawlId],
    queryFn: () => crawlsApi.diff(latestCrawlId!),
    enabled: !!latestCrawlId && tab === 'audit',
  })

  const { progress, streamError } = useCrawlProgress(activeCrawlId)

  useEffect(() => {
    if (!searchParams.get('tab') || searchParams.get('tab') === tab) return
    const nextTab = searchParams.get('tab') as TabId
    if (TABS.some((item) => item.id === nextTab)) setTab(nextTab)
  }, [searchParams, tab])

  useEffect(() => {
    const crawls = activeCrawlQuery.data?.crawls ?? []
    const active = crawls.find((crawl: any) => ['queued', 'running', 'cancelling'].includes(crawl.status))
    if (active?.id) setActiveCrawlId((current) => current ?? active.id)
  }, [activeCrawlQuery.data])

  useEffect(() => {
    if (!progress?.status || !['completed', 'failed'].includes(progress.status)) return
    queryClient.invalidateQueries({ queryKey: ['site-summary', id] })
    queryClient.invalidateQueries({ queryKey: ['site-pages', id] })
    queryClient.invalidateQueries({ queryKey: ['site-issues-grouped', id] })
    queryClient.invalidateQueries({ queryKey: ['site-issues-raw', id] })
    queryClient.invalidateQueries({ queryKey: ['site-active-crawl', id] })
  }, [id, progress?.status, queryClient])

  useEffect(() => {
    if (siteQuery.data) {
      if (siteQuery.data.crawl_max_pages) setCrawlLimit(String(siteQuery.data.crawl_max_pages))
      if (siteQuery.data.crawl_frequency) setCrawlFrequency(siteQuery.data.crawl_frequency)
      if (siteQuery.data.respect_robots_txt != null) setRespectRobots(siteQuery.data.respect_robots_txt)
      if (siteQuery.data.crawl_delay_ms) setCrawlDelayMs(String(siteQuery.data.crawl_delay_ms))
    }
  }, [siteQuery.data?.crawl_max_pages, siteQuery.data?.crawl_frequency, siteQuery.data?.respect_robots_txt, siteQuery.data?.crawl_delay_ms])

  useEffect(() => {
    if (analyticsStatusQuery.data?.property_id && !gaPropertyId) {
      setGaPropertyId(String(analyticsStatusQuery.data.property_id))
    }
  }, [analyticsStatusQuery.data?.property_id, gaPropertyId])

  const triggerCrawl = useMutation({
    mutationFn: () => api.post('crawls', { json: { site_id: id, trigger: 'manual' } }).json<any>(),
    onSuccess: (crawl) => {
      setActiveCrawlId(crawl.id)
      queryClient.invalidateQueries({ queryKey: ['site-active-crawl', id] })
      queryClient.invalidateQueries({ queryKey: ['site-summary', id] })
    },
  })

  const startVerification = useMutation({
    mutationFn: () => api.post(`sites/${id}/verify`, { json: { method: 'meta_tag' } }).json<any>(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['site', id] }),
  })

  const checkVerification = useMutation({
    mutationFn: () => api.post(`sites/${id}/verify/check`).json<any>(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['site', id] })
      queryClient.invalidateQueries({ queryKey: ['site-summary', id] })
    },
  })

  const updateCrawlSettings = useMutation({
    mutationFn: () => sitesApi.update(id!, {
      crawl_max_pages: Number(crawlLimit),
      crawl_frequency: crawlFrequency,
      respect_robots_txt: respectRobots,
      crawl_delay_ms: Number(crawlDelayMs),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['site', id] })
      queryClient.invalidateQueries({ queryKey: ['site-summary', id] })
      toast.success('Crawl settings updated')
    },
    onError: () => toast.error('Crawl settings could not be updated'),
  })

  const connectSearchConsole = useMutation({
    mutationFn: () => searchConsoleApi.connectUrl(id!),
    onSuccess: (result) => {
      if (result.connect_url) {
        window.open(result.connect_url, '_blank', 'noopener,noreferrer')
        toast.success('Google authorization opened in a new tab')
      } else {
        toast.error(result.message || 'Google Search Console is not configured')
      }
    },
    onError: () => toast.error('Could not prepare Google Search Console connection'),
  })

  const syncSearchConsole = useMutation({
    mutationFn: () => searchConsoleApi.sync(id!, { days: 90, inspect_limit: 10 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['search-console-status', id] })
      queryClient.invalidateQueries({ queryKey: ['search-console-performance', id] })
      queryClient.invalidateQueries({ queryKey: ['site-opportunities', id] })
      toast.success('Search Console sync finished')
    },
    onError: async (error: any) => {
      const detail = error?.response ? await error.response.json().catch(() => null) : null
      toast.error(detail?.detail || error?.message || 'Search Console sync failed')
    },
  })

  const connectAnalytics = useMutation({
    mutationFn: () => analyticsApi.connectUrl(id!, gaPropertyId.trim()),
    onSuccess: (result) => {
      if (result.connect_url) {
        window.open(result.connect_url, '_blank', 'noopener,noreferrer')
        toast.success('Google Analytics authorization opened')
      } else {
        toast.error(result.message || 'Google Analytics is not configured')
      }
    },
    onError: () => toast.error('Could not prepare GA4 connection'),
  })

  const syncAnalytics = useMutation({
    mutationFn: () => analyticsApi.sync(id!, { days: 90 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics-status', id] })
      queryClient.invalidateQueries({ queryKey: ['analytics-performance', id] })
      queryClient.invalidateQueries({ queryKey: ['site-opportunities', id] })
      toast.success('GA4 sync finished')
    },
    onError: async (error: any) => {
      const detail = error?.response ? await error.response.json().catch(() => null) : null
      toast.error(detail?.detail || error?.message || 'GA4 sync failed')
    },
  })

  const runPageSpeed = useMutation({
    mutationFn: () => pageSpeedApi.run(id!, { strategies: ['mobile', 'desktop'] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pagespeed', id] })
      queryClient.invalidateQueries({ queryKey: ['site-opportunities', id] })
      toast.success('PageSpeed checks completed')
    },
    onError: () => toast.error('PageSpeed checks failed'),
  })

  const setupIndexNow = useMutation({
    mutationFn: () => indexNowApi.setup(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['indexnow', id] })
      queryClient.invalidateQueries({ queryKey: ['site-opportunities', id] })
      toast.success('IndexNow setup checked')
    },
    onError: () => toast.error('IndexNow setup failed'),
  })

  const planRootCauseFix = useMutation({
    mutationFn: (group: any) => issuesApi.rootCauseFix({ site_id: id!, issue_type: group.type, mode: 'plan' }),
    onSuccess: (result) => setWorkflowPanel(result),
    onError: (error: any) => toast.error(error?.message || 'Fix workflow could not be loaded'),
  })

  const previewAiFix = useMutation({
    mutationFn: (group: any) => issuesApi.rootCauseFix({ site_id: id!, issue_type: group.type, mode: 'ai_preview' }),
    onSuccess: (result) => setWorkflowPanel(result),
    onError: async (error: any) => {
      const detail = error?.response ? await error.response.json().catch(() => null) : null
      toast.error(detail?.detail?.message || detail?.detail || error?.message || 'AI preview could not be created')
    },
  })

  const createGithubPr = useMutation({
    mutationFn: (group: any) => issuesApi.rootCauseFix({ site_id: id!, issue_type: group.type, mode: 'github_pr' }),
    onSuccess: (result) => {
      setWorkflowPanel(result)
      queryClient.invalidateQueries({ queryKey: ['site-issues-grouped', id] })
      queryClient.invalidateQueries({ queryKey: ['site-issues-raw', id] })
      toast.success('GitHub PR created')
    },
    onError: async (error: any) => {
      const detail = error?.response ? await error.response.json().catch(() => null) : null
      toast.error(detail?.detail?.message || detail?.detail || error?.message || 'GitHub PR could not be created')
    },
  })

  const site = siteQuery.data
  const summary = summaryQuery.data
  const crawlDiff = crawlDiffQuery.data
  const setup = summary?.setup
  const groups: any[] = groupedIssuesQuery.data?.groups ?? []
  const rawIssues: any[] = rawIssuesQuery.data?.issues ?? []
  const pages = pagesQuery.data?.pages ?? []
  const connection = connectionQuery.data ?? summary?.connection
  const searchConsole = searchConsoleStatusQuery.data ?? summary?.search_console
  const analytics = analyticsStatusQuery.data ?? summary?.analytics
  const gscPerformance = searchConsolePerformanceQuery.data
  const analyticsPerformance = analyticsPerformanceQuery.data
  const pageSpeed = pageSpeedQuery.data ?? summary?.pagespeed
  const indexNow = indexNowQuery.data ?? summary?.indexnow
  const opportunities: any[] = opportunitiesQuery.data?.opportunities ?? []
  const snippetInsights: any[] = snippetInsightsQuery.data?.insights ?? []

  const loading = siteQuery.isLoading || summaryQuery.isLoading
  const totalGroupedAffected = groups.reduce((sum, group) => sum + (group.count ?? 0), 0)
  const setupReadiness = readinessMeta(setup?.state)
  const connectionReadiness = readinessMeta(connection?.readiness)

  const changeTab = (nextTab: TabId) => {
    setTab(nextTab)
    setSearchParams({ tab: nextTab })
  }

  const fixSummary = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const issue of rawIssues) {
      counts[issue.fix_status] = (counts[issue.fix_status] || 0) + 1
    }
    return counts
  }, [rawIssues])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 text-primary animate-spin" />
      </div>
    )
  }

  if (!site) {
    return (
      <div className="space-y-4">
        <button onClick={() => navigate('/dashboard/sites')} className="text-sm text-muted-foreground hover:text-foreground">
          Back to sites
        </button>
        <p className="text-sm text-muted-foreground">This site could not be loaded.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          <button
            onClick={() => navigate('/dashboard/sites')}
            className="mt-1 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-3 mb-1 flex-wrap">
              <h1 className="text-2xl font-bold text-foreground">{site.name}</h1>
              <ScoreBadge score={summary?.latest_crawl?.seo_score} />
              <TinyPill label={setup?.label || 'Setup required'} className={setupReadiness.className} />
              <TinyPill
                label={site.ownership_verified ? 'Verified' : 'Unverified'}
                className={site.ownership_verified ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}
              />
              {site.status && (
                <TinyPill
                  label={site.status.replace(/_/g, ' ')}
                  className={
                    site.status === 'active' ? 'bg-green-500/10 text-green-500 border-green-500/20'
                    : site.status === 'paused' ? 'bg-muted text-muted-foreground border-border'
                    : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                  }
                />
              )}
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
              <a
                href={site.domain}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-primary transition-colors"
              >
                <Globe className="h-3.5 w-3.5" />
                {site.domain}
                <ExternalLink className="h-3 w-3" />
              </a>
              <span>Last crawl {site.last_crawled_at ? formatRelativeTime(site.last_crawled_at) : 'never'}</span>
              {site.created_at && <span>Added {formatRelativeTime(site.created_at)}</span>}
              {connection && <span>{connection.monitoring_mode_label} monitoring</span>}
              {connection?.write_integration_label && <span>Write integration: {connection.write_integration_label}</span>}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Link
            to={`/dashboard/sites/${id}/intelligence`}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
          >
            <Brain className="h-4 w-4" />
            Intelligence
          </Link>
          <button
            onClick={() => triggerCrawl.mutate()}
            disabled={triggerCrawl.isPending || (!!progress && ['queued', 'running'].includes(progress.status))}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-semibold hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${triggerCrawl.isPending || progress?.status === 'running' ? 'animate-spin' : ''}`} />
            {progress && ['queued', 'running'].includes(progress.status) ? 'Crawling...' : 'Run Crawl'}
          </button>
        </div>
      </div>

      {progress && (
        <div className="bg-card border border-border rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-foreground">Crawl status: {progress.status}</span>
            <span className="text-muted-foreground">{progress.pages_crawled}/{progress.pages_total ?? '-'} pages</span>
          </div>
          {progress.coverage_reason && (
            <p className="text-xs text-muted-foreground">
              {progress.coverage_reason}
            </p>
          )}
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-600"
              style={{ width: `${progress.percentage ? Math.min(progress.percentage, 100) : 10}%` }}
            />
          </div>
          {streamError && <p className="text-xs text-amber-400">{streamError}</p>}
        </div>
      )}

      <div className="border-b border-border">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {TABS.map((item) => (
            <button
              key={item.id}
              onClick={() => changeTab(item.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
                tab === item.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}>
        {tab === 'setup' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="rounded-xl border border-border bg-card p-5">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Workspace status</p>
                <p className="text-lg font-semibold text-foreground mt-3">{setup?.label || 'Setup required'}</p>
                <p className="text-sm text-muted-foreground mt-2">{setup?.description}</p>
              </div>
              <div className="rounded-xl border border-border bg-card p-5">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Monitoring mode</p>
                <p className="text-lg font-semibold text-foreground mt-3">{connection?.monitoring_mode_label || 'Crawler'}</p>
                <p className="text-sm text-muted-foreground mt-2">
                  {connection?.monitoring_mode === 'snippet'
                    ? 'Snippet mode can collect runtime data after install, but deployment remains read-only.'
                    : 'Crawler mode audits public pages and can power grouped issue detection and comparisons.'}
                </p>
              </div>
              <div className="rounded-xl border border-border bg-card p-5">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Write integration</p>
                <div className="mt-3 flex items-center gap-2 flex-wrap">
                  <p className="text-lg font-semibold text-foreground">{connection?.write_integration_label || 'Not configured'}</p>
                  <TinyPill label={connection?.readiness_label || 'Monitoring only'} className={connectionReadiness.className} />
                  {connection?.auto_deploy_capable && (
                    <TinyPill label="Auto-deploy capable" className="bg-green-500/10 text-green-400 border-green-500/20" />
                  )}
                  {setup?.write_integration_configured != null && (
                    <TinyPill
                      label={setup.write_integration_configured ? 'Configured' : 'Not configured'}
                      className={setup.write_integration_configured ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}
                    />
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-2">{connection?.explanation}</p>
                {connection?.last_tested_at && (
                  <p className="text-[10px] text-muted-foreground/50 mt-2">Last tested: {new Date(connection.last_tested_at).toLocaleString()}</p>
                )}
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-card p-6">
                <div className="flex items-center gap-2">
                  <Settings2 className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Setup checklist</h3>
                </div>
                <div className="mt-4 space-y-3">
                  {(setup?.steps ?? []).map((step: any) => (
                    <div key={step.key} className="flex items-start gap-3">
                      <div className={`mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg ${step.done ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'}`}>
                        <CheckCircle2 className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">{step.label}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Ownership verification</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  {site.ownership_verified
                    ? `Verified ${site.verified_at ? formatRelativeTime(site.verified_at) : ''}. Verification protects higher-trust actions, but it is not required for basic crawling.`
                    : 'Verify ownership before treating this property as fully trusted. Crawling still works before verification.'}
                  {!site.ownership_verified && site.verification_requested_at && (
                    <span className="block text-[11px] text-muted-foreground/60 mt-1">Verification requested {formatRelativeTime(site.verification_requested_at)}</span>
                  )}
                  {site.verification_method && (
                    <span className="block text-[11px] text-muted-foreground/70 mt-1">
                      Method: <span className="font-semibold text-foreground">{site.verification_method === 'meta_tag' ? 'Meta tag' : site.verification_method === 'dns_txt' ? 'DNS TXT record' : site.verification_method.replace(/_/g, ' ')}</span>
                    </span>
                  )}
                </p>
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() => startVerification.mutate()}
                    disabled={startVerification.isPending}
                    className="h-9 px-4 rounded-lg border border-border text-sm text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                  >
                    {startVerification.isPending ? 'Preparing...' : 'Generate Meta Tag'}
                  </button>
                  <button
                    onClick={() => checkVerification.mutate()}
                    disabled={checkVerification.isPending}
                    className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    {checkVerification.isPending ? 'Checking...' : 'Check Verification'}
                  </button>
                </div>
                {startVerification.data?.instructions && (
                  <code className="block p-3 rounded-lg bg-muted text-xs text-foreground break-all">
                    {typeof startVerification.data.instructions === 'string'
                      ? startVerification.data.instructions
                      : JSON.stringify(startVerification.data.instructions, null, 2)}
                  </code>
                )}
              </div>
            </div>

            <div className="grid lg:grid-cols-4 gap-4">
              <div className="rounded-xl border border-border bg-card p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Connection setup</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Monitoring mode and write integration are different. Crawler and snippet can observe the site; WordPress, Shopify, Webflow, and GitHub can deploy supported fixes when configured.
                </p>
                <div className="flex flex-wrap gap-2">
                  <TinyPill label={`Monitoring: ${connection?.monitoring_mode_label || 'Crawler'}`} />
                  <TinyPill label={`Write: ${connection?.write_integration_label || 'Not configured'}`} />
                  {site.connection_type && <TinyPill label={`Type: ${site.connection_type.replace(/_/g, ' ')}`} />}
                  {connection?.auto_deploy_capable && <TinyPill label="Auto-deploy capable" className="bg-green-500/10 text-green-500 border-green-500/20" />}
                  {connection?.readiness_label && <TinyPill label={connection.readiness_label} />}
                </div>
                {(site.cms_endpoint || site.github_repo) && (
                  <div className="space-y-1 text-xs text-muted-foreground">
                    {site.cms_endpoint && (
                      <p className="flex gap-2"><span className="shrink-0 font-medium text-foreground">CMS endpoint</span><span className="font-mono text-[11px] truncate">{site.cms_endpoint}</span></p>
                    )}
                    {site.github_repo && (
                      <p className="flex gap-2"><span className="shrink-0 font-medium text-foreground">GitHub repo</span><span className="font-mono text-[11px] truncate">{site.github_repo}</span></p>
                    )}
                    {site.github_repo && site.github_branch && (
                      <p className="flex gap-2"><span className="shrink-0 font-medium text-foreground">Branch</span><span className="font-mono text-[11px]">{site.github_branch}</span></p>
                    )}
                  </div>
                )}
                {connection?.explanation && (
                  <p className="text-[11px] text-muted-foreground/80 italic border border-border/40 rounded-lg px-3 py-2 bg-muted/20">
                    {connection.explanation}
                  </p>
                )}
                <button
                  onClick={() => navigate(`/dashboard/integrations?site_id=${site.id}`)}
                  className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-border text-sm text-foreground hover:bg-muted transition-colors"
                >
                  <Link2 className="h-4 w-4" />
                  Open connection setup
                </button>
                {snippetInstallQuery.data?.snippet_token && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Snippet token</p>
                    <code className="block p-2 rounded-lg bg-muted text-[11px] text-foreground break-all">{snippetInstallQuery.data.snippet_token}</code>
                  </div>
                )}
                {snippetInstallQuery.data?.script_tag && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Install tag</p>
                    <code className="block p-2 rounded-lg bg-muted text-[11px] text-foreground break-all">
                      {snippetInstallQuery.data.script_tag}
                    </code>
                  </div>
                )}
                {snippetInstallQuery.data?.collect_url && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Collect URL</p>
                    <code className="block p-2 rounded-lg bg-muted text-[11px] text-foreground break-all">{snippetInstallQuery.data.collect_url}</code>
                  </div>
                )}
                {snippetInstallQuery.data?.snippet_url && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Snippet JS URL</p>
                    <code className="block p-2 rounded-lg bg-muted text-[11px] text-foreground break-all">{snippetInstallQuery.data.snippet_url}</code>
                  </div>
                )}
                {(connectionCapabilitiesQuery.data?.capabilities ?? []).length > 0 && (
                  <div className="space-y-2">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Available connection types</p>
                    <div className="space-y-2">
                      {(connectionCapabilitiesQuery.data.capabilities as any[]).map((cap: any) => (
                        <div key={cap.connection_type} className={`rounded-lg border p-3 ${cap.connection_type === connectionCapabilitiesQuery.data.current_connection_type ? 'border-primary/40 bg-primary/5' : 'border-border bg-muted/20'}`}>
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <p className="text-xs font-semibold text-foreground">{cap.label}</p>
                            <div className="flex items-center gap-1.5">
                              {cap.connection_type === connectionCapabilitiesQuery.data.current_connection_type && (
                                <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">Active</span>
                              )}
                              <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                                cap.certification?.status === 'sandbox_only' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                                : cap.certification?.status === 'certified' ? 'bg-green-500/10 text-green-500 border-green-500/20'
                                : 'bg-muted text-muted-foreground border-border'
                              }`}>{cap.certification?.status?.replace(/_/g, ' ') ?? 'not tested'}</span>
                            </div>
                          </div>
                          <p className="text-[10px] text-muted-foreground">{cap.description}</p>
                          {cap.certification?.message && <p className="text-[10px] text-muted-foreground/60 mt-0.5 italic">{cap.certification.message}</p>}
                          <div className="flex flex-wrap gap-1.5 mt-1">
                            {cap.mode && <span className="text-[9px] px-1.5 py-0.5 rounded border bg-muted/50 text-muted-foreground border-border capitalize">{cap.mode.replace(/_/g, ' ')}</span>}
                            {cap.required_credentials?.length > 0 && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded border bg-muted/50 text-muted-foreground border-border">Needs: {(cap.required_credentials as string[]).join(', ')}</span>
                            )}
                          </div>
                          {cap.unsupported_message && <p className="text-[9px] text-amber-400/70 mt-1 italic">{cap.unsupported_message}</p>}
                          {cap.supported_fix_fields?.length > 0 && (
                            <p className="text-[10px] text-muted-foreground mt-1">Supports: {cap.supported_fix_fields.join(', ')}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-border bg-card p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Search Console</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Read-only GSC data tells AutoSEO which issues affect real Google impressions, CTR, positions, indexing, and sitemaps.
                </p>
                <div className="flex flex-wrap gap-2">
                  <TinyPill
                    label={searchConsole?.connected ? 'Connected' : (searchConsole?.readiness_label ?? 'Not connected')}
                    className={searchConsole?.connected ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}
                  />
                  {searchConsole?.property_url && <TinyPill label={searchConsole.property_url} />}
                  {searchConsole?.scope && (
                    <TinyPill label={searchConsole.scope.split('/').pop()?.replace('webmasters.', '') ?? searchConsole.scope} />
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => connectSearchConsole.mutate()}
                    disabled={connectSearchConsole.isPending}
                    className="h-9 px-3 rounded-lg border border-border text-xs text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                  >
                    {connectSearchConsole.isPending ? 'Preparing...' : searchConsole?.connected ? 'Reconnect' : 'Connect Google'}
                  </button>
                  <button
                    onClick={() => syncSearchConsole.mutate()}
                    disabled={syncSearchConsole.isPending || !searchConsole?.connected}
                    className="h-9 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    {syncSearchConsole.isPending ? 'Syncing...' : 'Sync 90 days'}
                  </button>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {searchConsole?.last_sync_at ? `Last synced ${formatRelativeTime(searchConsole.last_sync_at)}` : searchConsole?.description || 'Connect Google Search Console to unlock real traffic priority.'}
                  {searchConsole?.latest_sync_status && searchConsole.latest_sync_status !== 'success' && (
                    <span className="ml-1.5 text-amber-400">· Sync {searchConsole.latest_sync_status.replace(/_/g, ' ')}</span>
                  )}
                </p>
              </div>

              <div className="rounded-xl border border-border bg-card p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">GA4 revenue impact</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  GA4 tells AutoSEO which SEO fixes affect sessions, key events, transactions, and revenue.
                </p>
                <div className="flex flex-wrap gap-2">
                  <TinyPill
                    label={analytics?.connected ? 'Connected' : (analytics?.readiness_label ?? 'Not connected')}
                    className={analytics?.connected ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}
                  />
                  {analytics?.property_name && <TinyPill label={analytics.property_name} />}
                  {analytics?.property_id && !analytics?.property_name && <TinyPill label={`Property ${analytics.property_id}`} />}
                  {analytics?.scope && (
                    <TinyPill label={analytics.scope.split('/').pop()?.replace('analytics.', '') ?? analytics.scope} />
                  )}
                </div>
                {analytics?.description && !analytics?.connected && (
                  <p className="text-[10px] text-muted-foreground/70 leading-relaxed">{analytics.description}</p>
                )}
                {analytics?.last_sync_at && (
                  <p className="text-[10px] text-muted-foreground/60">Last synced {formatRelativeTime(analytics.last_sync_at)}</p>
                )}
                {analyticsPerformance?.synced_at && (
                  <p className="text-[10px] text-muted-foreground/50">Performance synced {new Date(analyticsPerformance.synced_at).toLocaleDateString()}</p>
                )}
                {analyticsPerformance?.generated_at && (
                  <p className="text-[10px] text-muted-foreground/40">Data as of {new Date(analyticsPerformance.generated_at).toLocaleDateString()}</p>
                )}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-muted/30 p-2">
                    <p className="font-bold text-foreground">${Number(analyticsPerformance?.totals?.total_revenue ?? analytics?.totals?.total_revenue ?? 0).toFixed(2)}</p>
                    <p className="text-muted-foreground">Revenue</p>
                  </div>
                  <div className="rounded-lg bg-muted/30 p-2">
                    <p className="font-bold text-foreground">{Math.round(analyticsPerformance?.totals?.sessions ?? analytics?.totals?.sessions ?? 0).toLocaleString()}</p>
                    <p className="text-muted-foreground">Sessions</p>
                  </div>
                  <div className="rounded-lg bg-muted/30 p-2">
                    <p className="font-bold text-foreground">{Math.round(analyticsPerformance?.totals?.active_users ?? 0).toLocaleString()}</p>
                    <p className="text-muted-foreground">Active users</p>
                  </div>
                  <div className="rounded-lg bg-muted/30 p-2">
                    <p className="font-bold text-foreground">{Math.round(analyticsPerformance?.totals?.key_events ?? 0).toLocaleString()}</p>
                    <p className="text-muted-foreground">Key events</p>
                  </div>
                  {(analyticsPerformance?.totals?.transactions ?? 0) > 0 && (
                    <div className="rounded-lg bg-muted/30 p-2">
                      <p className="font-bold text-foreground">{Math.round(analyticsPerformance.totals.transactions).toLocaleString()}</p>
                      <p className="text-muted-foreground">Transactions</p>
                    </div>
                  )}
                  {(analyticsPerformance?.totals?.engagement_rate ?? 0) > 0 && (
                    <div className="rounded-lg bg-muted/30 p-2">
                      <p className="font-bold text-foreground">{((analyticsPerformance.totals.engagement_rate as number) * 100).toFixed(1)}%</p>
                      <p className="text-muted-foreground">Engagement rate</p>
                    </div>
                  )}
                </div>
                {(analyticsPerformance?.top_pages ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Top GA4 pages</p>
                    <div className="space-y-1">
                      {(analyticsPerformance!.top_pages as any[]).slice(0, 5).map((pg: any, i: number) => (
                        <div key={i} className="flex items-center justify-between gap-2 text-[10px]">
                          <span className="text-foreground font-mono truncate">{pg.page_path ?? pg.page ?? pg}</span>
                          <span className="text-muted-foreground flex-shrink-0">{pg.sessions ?? pg.active_users ?? 0} sessions</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <input
                  value={gaPropertyId}
                  onChange={(event) => setGaPropertyId(event.target.value)}
                  placeholder="GA4 property ID, e.g. 123456789"
                  className="w-full h-9 rounded-lg border border-border bg-background px-3 text-xs text-foreground"
                />
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => connectAnalytics.mutate()}
                    disabled={connectAnalytics.isPending || !gaPropertyId.trim()}
                    className="h-9 px-3 rounded-lg border border-border text-xs text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                  >
                    {connectAnalytics.isPending ? 'Preparing...' : analytics?.connected ? 'Reconnect GA4' : 'Connect GA4'}
                  </button>
                  <button
                    onClick={() => syncAnalytics.mutate()}
                    disabled={syncAnalytics.isPending || !analytics?.connected}
                    className="h-9 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    {syncAnalytics.isPending ? 'Syncing...' : 'Sync 90 days'}
                  </button>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-6 space-y-3">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">PageSpeed + CrUX</h3>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {pageSpeed?.readiness_label && (
                      <TinyPill label={pageSpeed.readiness_label} className={pageSpeed?.configured ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-muted text-muted-foreground border-border'} />
                    )}
                    {pageSpeed?.generated_at && (
                      <span className="text-[10px] text-muted-foreground/60">Updated {new Date(pageSpeed.generated_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  {pageSpeed?.description || 'Run Google PageSpeed checks for the top pages and merge Core Web Vitals into the priority engine.'}
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-muted/30 p-2">
                    <p className="font-bold text-foreground">{pageSpeed?.summary?.avg_performance_score ?? pageSpeed?.avg_performance_score ?? '-'}</p>
                    <p className="text-muted-foreground">Avg score</p>
                  </div>
                  <div className="rounded-lg bg-muted/30 p-2">
                    <p className="font-bold text-foreground">{pageSpeed?.summary?.avg_lcp_ms ?? pageSpeed?.avg_lcp_ms ?? '-'}ms</p>
                    <p className="text-muted-foreground">Avg LCP</p>
                  </div>
                  {pageSpeed?.summary?.avg_inp_ms != null && (
                    <div className="rounded-lg bg-muted/30 p-2">
                      <p className="font-bold text-foreground">{pageSpeed.summary.avg_inp_ms}ms</p>
                      <p className="text-muted-foreground">Avg INP</p>
                    </div>
                  )}
                  {pageSpeed?.summary?.avg_cls_score != null && (
                    <div className="rounded-lg bg-muted/30 p-2">
                      <p className="font-bold text-foreground">{pageSpeed.summary.avg_cls_score}</p>
                      <p className="text-muted-foreground">Avg CLS</p>
                    </div>
                  )}
                </div>
                {(pageSpeed?.runs ?? []).length > 0 && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-[11px]">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left pb-1.5 pr-3 text-muted-foreground font-medium">Page</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium">Perf</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium">A11y</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium">BP</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium">SEO</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium">LCP</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium hidden md:table-cell">FCP</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium hidden md:table-cell">INP</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium hidden lg:table-cell">TTFB</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium hidden xl:table-cell">CLS</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium hidden xl:table-cell">TBT</th>
                          <th className="text-center pb-1.5 pr-2 text-muted-foreground font-medium hidden 2xl:table-cell">SI</th>
                          <th className="text-center pb-1.5 text-muted-foreground font-medium">Strategy</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {(pageSpeed.runs as any[]).slice(0, 6).map((run: any) => {
                          const isExpanded = expandedRunId === run.id
                          const hasDetails = (run.opportunities?.length > 0) || (run.diagnostics?.length > 0) || (run.crux_metrics && Object.keys(run.crux_metrics).length > 0)
                          return (
                            <>
                              <tr
                                key={run.id}
                                onClick={() => hasDetails ? setExpandedRunId(isExpanded ? null : run.id) : undefined}
                                className={`transition-colors ${hasDetails ? 'cursor-pointer hover:bg-muted/30' : 'hover:bg-muted/20'} ${isExpanded ? 'bg-muted/20' : ''}`}
                              >
                                <td className="py-1.5 pr-3 text-muted-foreground truncate max-w-[100px]" title={run.page_url}>
                                  <div className="flex items-center gap-1">
                                    {hasDetails && (
                                      <span className={`text-[9px] text-primary transition-transform inline-block ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
                                    )}
                                    {run.page_url?.replace(/^https?:\/\/[^/]+/, '') || '/'}
                                  </div>
                                </td>
                                <td className="py-1.5 pr-2 text-center">
                                  {run.performance_score != null ? (
                                    <span className={`font-bold ${run.performance_score >= 90 ? 'text-green-400' : run.performance_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                                      {Math.round(run.performance_score)}
                                    </span>
                                  ) : <span className="text-muted-foreground/50">{run.error_message ? '!' : '—'}</span>}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-foreground">
                                  {run.accessibility_score != null ? Math.round(run.accessibility_score) : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-foreground">
                                  {run.best_practices_score != null ? Math.round(run.best_practices_score) : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-foreground">
                                  {run.seo_score != null ? Math.round(run.seo_score) : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-muted-foreground">
                                  {run.lcp_ms != null ? `${run.lcp_ms}ms` : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-muted-foreground hidden md:table-cell">
                                  {run.fcp_ms != null ? `${run.fcp_ms}ms` : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-muted-foreground hidden md:table-cell">
                                  {run.inp_ms != null ? `${run.inp_ms}ms` : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-muted-foreground hidden lg:table-cell">
                                  {run.ttfb_ms != null ? `${run.ttfb_ms}ms` : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-muted-foreground hidden xl:table-cell">
                                  {run.cls_score != null ? <span className={run.cls_score <= 0.1 ? 'text-green-400' : run.cls_score <= 0.25 ? 'text-amber-400' : 'text-red-400'}>{run.cls_score.toFixed(3)}</span> : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-muted-foreground hidden xl:table-cell">
                                  {run.total_blocking_time_ms != null ? `${run.total_blocking_time_ms}ms` : '—'}
                                </td>
                                <td className="py-1.5 pr-2 text-center text-muted-foreground hidden 2xl:table-cell">
                                  {run.speed_index_ms != null ? `${run.speed_index_ms}ms` : '—'}
                                </td>
                                <td className="py-1.5 text-center text-muted-foreground capitalize">{run.strategy}</td>
                              </tr>
                              {isExpanded && (
                                <tr key={`${run.id}-detail`}>
                                  <td colSpan={13} className="px-4 pb-3 pt-0 bg-muted/10">
                                    <div className="rounded-lg border border-border bg-background p-4 space-y-4 text-xs">
                                      <div className="flex items-center gap-2 flex-wrap">
                                        {run.status && (
                                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${run.status === 'completed' ? 'bg-green-500/10 text-green-400 border-green-500/20' : run.status === 'failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-muted text-muted-foreground border-border'}`}>
                                            {run.status}
                                          </span>
                                        )}
                                        {run.checked_at && (
                                          <span className="text-[10px] text-muted-foreground/60">Checked {new Date(run.checked_at).toLocaleString()}</span>
                                        )}
                                        {run.speed_index_ms != null && (
                                          <span className="text-[10px] text-muted-foreground">Speed Index: {run.speed_index_ms}ms</span>
                                        )}
                                      </div>
                                      {run.error_message && (
                                        <p className="text-red-400 text-[11px]">Error: {run.error_message}</p>
                                      )}
                                      {run.crux_metrics && Object.keys(run.crux_metrics).length > 0 && (
                                        <div>
                                          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">CrUX Field Data</p>
                                          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                                            {Object.entries(run.crux_metrics as Record<string, any>).map(([k, v]) => (
                                              <div key={k} className="rounded bg-muted/40 px-2 py-1.5 text-center">
                                                <p className="text-sm font-bold text-foreground">{typeof v === 'number' ? (k.includes('ms') ? `${v}ms` : v.toFixed ? v.toFixed(3) : v) : String(v)}</p>
                                                <p className="text-[9px] text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</p>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                      {(run.opportunities as any[])?.length > 0 && (
                                        <div>
                                          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Opportunities</p>
                                          <div className="space-y-2">
                                            {(run.opportunities as any[]).map((opp: any, i: number) => (
                                              <div key={i} className="flex items-start justify-between gap-3 rounded-lg bg-amber-500/5 border border-amber-500/15 px-3 py-2">
                                                <div className="min-w-0">
                                                  <p className="font-medium text-foreground">{opp.title ?? opp.id}</p>
                                                  {opp.description && <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{opp.description}</p>}
                                                </div>
                                                {opp.savings_ms != null && (
                                                  <span className="flex-shrink-0 text-[10px] font-semibold text-amber-400 whitespace-nowrap">{opp.savings_ms}ms saved</span>
                                                )}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                      {(run.diagnostics as any[])?.length > 0 && (
                                        <div>
                                          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Diagnostics</p>
                                          <div className="space-y-2">
                                            {(run.diagnostics as any[]).map((diag: any, i: number) => (
                                              <div key={i} className="flex items-start gap-3 rounded-lg bg-muted/30 border border-border px-3 py-2">
                                                <div className="min-w-0">
                                                  <p className="font-medium text-foreground">{diag.title ?? diag.id}</p>
                                                  {diag.description && <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{diag.description}</p>}
                                                  {diag.display_value && <p className="text-[11px] text-primary mt-0.5 font-mono">{diag.display_value}</p>}
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                      {!hasDetails && (
                                        <p className="text-[11px] text-muted-foreground text-center py-2">No detailed diagnostics available for this run.</p>
                                      )}
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
                <button
                  onClick={() => runPageSpeed.mutate()}
                  disabled={runPageSpeed.isPending}
                  className="h-9 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {runPageSpeed.isPending ? 'Running...' : 'Run PageSpeed'}
                </button>
              </div>

              <div className="rounded-xl border border-border bg-card p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <Link2 className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">IndexNow</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  After a fix is deployed and verified by recrawl, IndexNow can notify supported search engines about changed URLs.
                </p>
                <TinyPill
                  label={indexNow?.readiness_label ?? (indexNow?.verified ? 'Verified' : indexNow?.configured ? 'Key file needed' : 'Not set up')}
                  className={indexNow?.verified ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}
                />
                {indexNow?.last_verified_at && (
                  <p className="text-[10px] text-muted-foreground/60">Last verified {new Date(indexNow.last_verified_at).toLocaleDateString()}</p>
                )}
                {indexNow?.key && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Key</p>
                    <code className="block p-2 rounded-lg bg-muted text-[11px] text-foreground break-all">{indexNow.key}</code>
                  </div>
                )}
                {indexNow?.key_location && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Key file URL</p>
                    <code className="block p-2 rounded-lg bg-muted text-[11px] text-foreground break-all">{indexNow.key_location}</code>
                  </div>
                )}
                {indexNow?.instructions && !indexNow.verified && (
                  <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                    <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-1.5">Setup instructions</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{indexNow.instructions}</p>
                  </div>
                )}
                {(indexNow?.recent_submissions ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Recent submissions</p>
                    <div className="space-y-2">
                      {(indexNow.recent_submissions as any[]).slice(0, 3).map((sub: any, i: number) => (
                        <div key={sub.id ?? i} className="rounded-lg border border-border bg-muted/30 p-2 space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            {sub.success != null && (
                              <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${sub.success ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                {sub.success ? 'Accepted' : 'Failed'}
                              </span>
                            )}
                            {sub.status_code != null && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-muted border-border text-muted-foreground">HTTP {sub.status_code}</span>
                            )}
                            {sub.submitted_at && (
                              <span className="text-[10px] text-muted-foreground/60">{formatRelativeTime(sub.submitted_at)}</span>
                            )}
                          </div>
                          {(sub.urls ?? []).slice(0, 2).map((u: string, j: number) => (
                            <p key={j} className="text-[11px] text-muted-foreground truncate font-mono">{u}</p>
                          ))}
                          {(sub.urls ?? []).length > 2 && (
                            <p className="text-[10px] text-muted-foreground/50">+{sub.urls.length - 2} more URLs</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <button
                  onClick={() => setupIndexNow.mutate()}
                  disabled={setupIndexNow.isPending}
                  className="h-9 px-3 rounded-lg border border-border text-xs text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                >
                  {setupIndexNow.isPending ? 'Checking...' : 'Prepare / verify key'}
                </button>
              </div>

              <div className="rounded-xl border border-border bg-card p-6 space-y-4">
                <div className="flex items-center gap-2">
                  <Layers3 className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Crawl settings</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Configure how AutoSEO crawls this site. Changes take effect on the next scheduled or manual crawl.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground block">Max pages per crawl</label>
                    <input
                      type="number"
                      min={1}
                      max={50000}
                      value={crawlLimit}
                      onChange={(event) => setCrawlLimit(event.target.value)}
                      className="w-full h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground"
                    />
                    <p className="text-[10px] text-muted-foreground/70">
                      Backend limit: {summary?.latest_crawl?.crawl_limit ?? site.crawl_max_pages ?? '—'}
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground block">Crawl frequency</label>
                    <select
                      value={crawlFrequency}
                      onChange={(event) => setCrawlFrequency(event.target.value)}
                      className="w-full h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground"
                    >
                      <option value="never">Never (manual only)</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="biweekly">Biweekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="after_github_pr_merge">After GitHub PR merge</option>
                    </select>
                    {site.next_scheduled_crawl && (
                      <p className="text-[10px] text-muted-foreground/70">
                        Next: {new Date(site.next_scheduled_crawl).toLocaleString()}
                      </p>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground block">Crawl delay (ms)</label>
                    <input
                      type="number"
                      min={500}
                      max={10000}
                      step={100}
                      value={crawlDelayMs}
                      onChange={(event) => setCrawlDelayMs(event.target.value)}
                      className="w-full h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground"
                    />
                    <p className="text-[10px] text-muted-foreground/70">500–10000ms between requests</p>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground block">Respect robots.txt</label>
                    <button
                      type="button"
                      onClick={() => setRespectRobots(prev => !prev)}
                      className={`flex items-center gap-2 h-9 px-3 rounded-lg border text-sm font-medium transition-colors w-full ${respectRobots ? 'border-green-500/40 bg-green-500/10 text-green-400' : 'border-border bg-muted/30 text-muted-foreground'}`}
                    >
                      <span className={`w-4 h-4 rounded-full border-2 flex-shrink-0 ${respectRobots ? 'bg-green-400 border-green-400' : 'border-muted-foreground'}`} />
                      {respectRobots ? 'Enabled — obeying robots.txt' : 'Disabled — ignoring robots.txt'}
                    </button>
                  </div>
                </div>

                <button
                  onClick={() => updateCrawlSettings.mutate()}
                  disabled={updateCrawlSettings.isPending || Number(crawlLimit) < 1 || Number(crawlDelayMs) < 500}
                  className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {updateCrawlSettings.isPending ? 'Saving…' : 'Save crawl settings'}
                </button>
              </div>

              {(activeCrawlQuery.data?.crawls ?? []).length > 0 && (
                <div className="rounded-xl border border-border bg-card overflow-hidden">
                  <div className="px-5 py-3 border-b border-border">
                    <h3 className="text-sm font-semibold text-foreground">Recent Crawls</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left px-4 py-2.5 text-muted-foreground font-medium">Date</th>
                          <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">Status</th>
                          <th className="text-center px-4 py-2.5 text-muted-foreground font-medium hidden sm:table-cell">Trigger</th>
                          <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">Pages</th>
                          <th className="text-center px-4 py-2.5 text-muted-foreground font-medium hidden sm:table-cell">Issues</th>
                          <th className="text-center px-4 py-2.5 text-muted-foreground font-medium hidden md:table-cell">Score</th>
                          <th className="text-center px-4 py-2.5 text-muted-foreground font-medium hidden lg:table-cell">Duration</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/50">
                        {(activeCrawlQuery.data.crawls as any[]).slice(0, 5).map((cr: any) => (
                          <tr key={cr.id} className="hover:bg-muted/20 transition-colors">
                            <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">
                              {(cr.completed_at || cr.created_at)
                                ? formatRelativeTime(cr.completed_at || cr.created_at)
                                : '—'}
                            </td>
                            <td className="px-4 py-2.5 text-center">
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full border text-[10px] font-semibold capitalize ${
                                cr.status === 'completed' ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                : cr.status === 'running' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
                                : cr.status === 'failed' ? 'bg-red-500/10 text-red-400 border-red-500/20'
                                : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                              }`}>
                                {cr.status}
                              </span>
                              {cr.error_message && (
                                <p className="text-[9px] text-red-400/70 mt-0.5 max-w-[120px] truncate" title={cr.error_message}>{cr.error_message}</p>
                              )}
                            </td>
                            <td className="px-4 py-2.5 text-center text-muted-foreground hidden sm:table-cell capitalize">{cr.trigger ?? '—'}</td>
                            <td className="px-4 py-2.5 text-center text-foreground">{cr.pages_crawled ?? '—'}</td>
                            <td className="px-4 py-2.5 text-center text-muted-foreground hidden sm:table-cell">{cr.issues_found ?? '—'}</td>
                            <td className="px-4 py-2.5 text-center hidden md:table-cell">
                              {cr.seo_score != null ? (
                                <span className={`font-bold ${cr.seo_score >= 70 ? 'text-green-400' : cr.seo_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                                  {Math.round(cr.seo_score)}
                                </span>
                              ) : '—'}
                            </td>
                            <td className="px-4 py-2.5 text-center text-muted-foreground hidden lg:table-cell">
                              {cr.duration_ms != null ? `${(cr.duration_ms / 1000).toFixed(1)}s` : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <Trash2 className="h-4 w-4 text-red-400" />
                  <h3 className="text-sm font-semibold text-foreground">Delete site</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  Deleting a site is permanent. AutoSEO will remove crawls, pages, issues, reports, keywords, competitors, snippet events, and related history for this property.
                </p>
                <button
                  onClick={() => setShowDelete(true)}
                  className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-red-500 text-white text-sm font-semibold hover:bg-red-600 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete site
                </button>
              </div>
            </div>
          </div>
        )}

        {tab === 'audit' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Pages', value: summary?.metrics?.pages_count ?? 0 },
                { label: 'Raw Issues', value: summary?.metrics?.open_issues ?? 0 },
                { label: 'Grouped Root Causes', value: groups.length },
                { label: 'Deployed Fixes', value: summary?.metrics?.deployed_fixes ?? 0 },
              ].map((card) => (
                <div key={card.label} className="rounded-xl border border-border bg-card p-5">
                  <p className="text-2xl font-bold text-foreground">{card.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{card.label}</p>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-border bg-card p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Crawl coverage</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    Shows why issue totals can change when page coverage changes.
                  </p>
                </div>
                <TinyPill label={`Limit: ${summary?.latest_crawl?.crawl_limit ?? site.crawl_max_pages ?? '-'}`} />
              </div>
              <div className="grid sm:grid-cols-4 gap-3 mt-4">
                {[
                  { label: 'Discovered URLs', value: summary?.latest_crawl?.urls_discovered ?? 0 },
                  { label: 'Scanned URLs', value: summary?.latest_crawl?.pages_crawled ?? 0 },
                  { label: 'Skipped URLs', value: summary?.latest_crawl?.urls_skipped ?? 0 },
                  { label: 'Crawl limit', value: summary?.latest_crawl?.crawl_limit ?? site.crawl_max_pages ?? 0 },
                ].map((item) => (
                  <div key={item.label} className="rounded-lg bg-muted/30 p-3">
                    <p className="text-lg font-bold text-foreground">{item.value}</p>
                    <p className="text-[11px] text-muted-foreground">{item.label}</p>
                  </div>
                ))}
              </div>
              {summary?.latest_crawl?.coverage_reason && (
                <p className="text-xs text-muted-foreground mt-3">{summary.latest_crawl.coverage_reason}</p>
              )}
              {summary?.latest_crawl?.coverage_details?.reason && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">
                    Reason: {(summary.latest_crawl.coverage_details.reason as string).replace(/_/g, ' ')}
                  </span>
                  {summary.latest_crawl.coverage_details.source && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">
                      Source: {(summary.latest_crawl.coverage_details.source as string).replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
              )}
            </div>

            {summary?.issues_by_severity && Object.keys(summary.issues_by_severity).some(k => (summary.issues_by_severity as Record<string,number>)[k] > 0) && (
              <div className="rounded-xl border border-border bg-card p-5">
                <h3 className="text-sm font-semibold text-foreground mb-3">Issues by severity</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {(['critical','high','medium','low'] as const).map((sev) => {
                    const count = (summary.issues_by_severity as Record<string,number>)[sev] ?? 0
                    const colors: Record<string,string> = {
                      critical: 'text-red-500 border-red-500/20 bg-red-500/10',
                      high: 'text-orange-500 border-orange-500/20 bg-orange-500/10',
                      medium: 'text-amber-500 border-amber-500/20 bg-amber-500/10',
                      low: 'text-blue-500 border-blue-500/20 bg-blue-500/10',
                    }
                    return (
                      <div key={sev} className={`rounded-lg border p-3 text-center ${colors[sev]}`}>
                        <p className="text-2xl font-bold">{count}</p>
                        <p className="text-[11px] capitalize mt-0.5 opacity-80">{sev}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {crawlDiff && (
              <div className="rounded-xl border border-border bg-card p-5 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-foreground">Crawl diff</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {crawlDiff.summary?.site_score_delta != null && crawlDiff.summary.site_score_delta !== 0 && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${crawlDiff.summary.site_score_delta > 0 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                        Score {crawlDiff.summary.site_score_delta > 0 ? '+' : ''}{crawlDiff.summary.site_score_delta}
                      </span>
                    )}
                    {crawlDiff.summary?.new_pages_count > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20 font-semibold">+{crawlDiff.summary.new_pages_count} new</span>}
                    {crawlDiff.summary?.removed_pages_count > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 font-semibold">−{crawlDiff.summary.removed_pages_count} removed</span>}
                    {crawlDiff.summary?.score_improved_count > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-semibold">{crawlDiff.summary.score_improved_count} improved</span>}
                    {crawlDiff.summary?.score_declined_count > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">{crawlDiff.summary.score_declined_count} declined</span>}
                    {crawlDiff.summary?.title_changed_count > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground border border-border font-semibold">{crawlDiff.summary.title_changed_count} title changes</span>}
                  </div>
                </div>
                {crawlDiff.previous_crawl_id && (
                  <p className="text-[10px] text-muted-foreground/60">
                    Comparing {new Date(crawlDiff.current_started_at).toLocaleDateString()} vs {new Date(crawlDiff.previous_started_at).toLocaleDateString()}
                  </p>
                )}
                {(crawlDiff.new_pages ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-green-400 uppercase tracking-wider mb-1">New pages</p>
                    {(crawlDiff.new_pages as any[]).slice(0, 5).map((p: any) => (
                      <p key={p.url ?? p} className="text-[11px] text-muted-foreground truncate">+ {p.url ?? p}</p>
                    ))}
                  </div>
                )}
                {(crawlDiff.removed_pages ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-red-400 uppercase tracking-wider mb-1">Removed pages</p>
                    {(crawlDiff.removed_pages as any[]).slice(0, 5).map((p: any) => (
                      <p key={p.url ?? p} className="text-[11px] text-muted-foreground truncate">− {p.url ?? p}</p>
                    ))}
                  </div>
                )}
                {(crawlDiff.score_improved ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider mb-1">Score improved</p>
                    {(crawlDiff.score_improved as any[]).slice(0, 3).map((p: any) => (
                      <p key={p.url ?? p} className="text-[11px] text-muted-foreground truncate flex items-center gap-2">
                        <span className="text-green-400 font-semibold">{p.previous_score ?? '?'} → {p.current_score ?? '?'}</span>
                        <span className="truncate">{p.url ?? p}</span>
                      </p>
                    ))}
                  </div>
                )}
                {(crawlDiff.score_declined ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-1">Score declined</p>
                    {(crawlDiff.score_declined as any[]).slice(0, 3).map((p: any) => (
                      <p key={p.url ?? p} className="text-[11px] text-muted-foreground truncate flex items-center gap-2">
                        <span className="text-red-400 font-semibold">{p.previous_score ?? '?'} → {p.current_score ?? '?'}</span>
                        <span className="truncate">{p.url ?? p}</span>
                      </p>
                    ))}
                  </div>
                )}
                {(crawlDiff.title_changed ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Title changes</p>
                    {(crawlDiff.title_changed as any[]).slice(0, 3).map((p: any) => (
                      <div key={p.url ?? p} className="text-[11px] space-y-0.5">
                        <p className="text-muted-foreground/60 truncate">{p.url ?? p}</p>
                        <p className="truncate"><span className="line-through text-red-400/70">{p.old_title}</span></p>
                        <p className="truncate text-green-400/70">{p.new_title}</p>
                      </div>
                    ))}
                  </div>
                )}
                {!crawlDiff.previous_crawl_id && (
                  <p className="text-xs text-muted-foreground">No previous crawl to compare against yet.</p>
                )}
              </div>
            )}

            {(summary?.audit_note || groupedIssuesQuery.data?.note) && (
              <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-3 text-xs text-blue-100">
                {summary?.audit_note || groupedIssuesQuery.data?.note}
              </div>
            )}

            <div className="grid lg:grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-card p-5 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-primary" />
                      Next best opportunities
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Ranked by technical severity, Google demand, runtime signals, and fix readiness.
                    </p>
                  </div>
                  <TinyPill label={`${opportunities.length} found`} />
                </div>
                {opportunitiesQuery.data?.by_source && Object.keys(opportunitiesQuery.data.by_source).length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(opportunitiesQuery.data.by_source as Record<string, number>).map(([src, count]) => (
                      <span key={src} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border text-[10px] font-semibold">
                        {src}<span className="text-foreground">{count}</span>
                      </span>
                    ))}
                  </div>
                )}
                <div className="space-y-3">
                  {opportunitiesQuery.data?.snippet_status && (
                    <p className="text-[11px] text-muted-foreground/70 italic">{opportunitiesQuery.data.snippet_status}</p>
                  )}
                  {opportunitiesQuery.data?.message && opportunities.length === 0 && (
                    <p className="text-sm text-muted-foreground">{opportunitiesQuery.data.message}</p>
                  )}
                  {opportunities.length === 0 && !opportunitiesQuery.data?.message ? (
                    <p className="text-sm text-muted-foreground">Connect Search Console, install snippet, or run a crawl to generate prioritized opportunities.</p>
                  ) : opportunities.slice(0, 5).map((item) => (
                    <div key={`${item.source}-${item.type}-${item.affected_url || item.issue_type}`} className="rounded-lg border border-border bg-background p-3 space-y-2">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-foreground">{item.title}</p>
                          <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">{item.description}</p>
                          {item.affected_url && (
                            <p className="text-[10px] text-muted-foreground/60 mt-1 truncate font-mono">{item.affected_url}</p>
                          )}
                        </div>
                        <TinyPill label={`${item.priority_score}`} className="bg-cyan-500/10 text-cyan-300 border-cyan-500/20" />
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <TinyPill label={item.source} />
                        {item.type && <TinyPill label={item.type.replace(/_/g, ' ')} className="bg-indigo-500/10 text-indigo-300 border-indigo-500/20" />}
                        {item.issue_type && <TinyPill label={item.issue_type.replace(/_/g, ' ')} className="bg-violet-500/10 text-violet-300 border-violet-500/20" />}
                        {item.impact_label && <TinyPill label={item.impact_label} />}
                        {item.data?.category && <TinyPill label={item.data.category} className="bg-blue-500/10 text-blue-300 border-blue-500/20" />}
                        {item.data?.severity && <TinyPill label={item.data.severity} className={item.data.severity === 'high' ? 'bg-red-500/10 text-red-400 border-red-500/20' : item.data.severity === 'medium' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : ''} />}
                        {item.data?.affected_count > 0 && <TinyPill label={`${item.data.affected_count} affected`} />}
                        {item.data?.total_impact > 0 && <TinyPill label={`impact ${Math.round(item.data.total_impact)}`} className="bg-violet-500/10 text-violet-300 border-violet-500/20" />}
                      </div>
                      {item.data?.breakdown && (
                        <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
                          {item.data.breakdown.technical > 0 && <div className="rounded bg-muted/30 px-2 py-1 text-center"><p className="text-[10px] font-bold text-foreground">{Math.round(item.data.breakdown.technical)}</p><p className="text-[8px] text-muted-foreground">Technical</p></div>}
                          {item.data.breakdown.crawler_impact > 0 && <div className="rounded bg-muted/30 px-2 py-1 text-center"><p className="text-[10px] font-bold text-foreground">{Math.round(item.data.breakdown.crawler_impact)}</p><p className="text-[8px] text-muted-foreground">Crawl impact</p></div>}
                          {item.data.breakdown.fixability > 0 && <div className="rounded bg-muted/30 px-2 py-1 text-center"><p className="text-[10px] font-bold text-foreground">{Math.round(item.data.breakdown.fixability)}</p><p className="text-[8px] text-muted-foreground">Fixability</p></div>}
                          {item.data.breakdown.affected_volume > 0 && <div className="rounded bg-muted/30 px-2 py-1 text-center"><p className="text-[10px] font-bold text-foreground">{Math.round(item.data.breakdown.affected_volume)}</p><p className="text-[8px] text-muted-foreground">Affected vol</p></div>}
                          {item.data.breakdown.search_demand > 0 && <div className="rounded bg-muted/30 px-2 py-1 text-center"><p className="text-[10px] font-bold text-foreground">{Math.round(item.data.breakdown.search_demand)}</p><p className="text-[8px] text-muted-foreground">GSC demand</p></div>}
                          {item.data.breakdown.business_value > 0 && <div className="rounded bg-muted/30 px-2 py-1 text-center"><p className="text-[10px] font-bold text-foreground">{Math.round(item.data.breakdown.business_value)}</p><p className="text-[8px] text-muted-foreground">Business val</p></div>}
                          {item.data.breakdown.lost_clicks > 0 && <div className="rounded bg-red-500/10 px-2 py-1 text-center"><p className="text-[10px] font-bold text-red-400">{Math.round(item.data.breakdown.lost_clicks)}</p><p className="text-[8px] text-muted-foreground">Lost clicks</p></div>}
                        </div>
                      )}
                      {(item.data?.gsc_impact?.impressions > 0 || item.data?.gsc_impact?.clicks > 0) && (
                        <div className="flex gap-3 text-[10px] text-muted-foreground border-t border-border/50 pt-1.5">
                          {item.data.gsc_impact.impressions > 0 && <span><span className="font-semibold text-foreground">{Math.round(item.data.gsc_impact.impressions).toLocaleString()}</span> impressions</span>}
                          {item.data.gsc_impact.clicks > 0 && <span><span className="font-semibold text-foreground">{Math.round(item.data.gsc_impact.clicks)}</span> clicks</span>}
                          {item.data.gsc_impact.ctr > 0 && <span><span className="font-semibold text-foreground">{(item.data.gsc_impact.ctr * 100).toFixed(1)}%</span> CTR</span>}
                          {item.data.gsc_impact.position > 0 && <span>pos <span className="font-semibold text-foreground">{item.data.gsc_impact.position.toFixed(1)}</span></span>}
                          {item.data.gsc_impact.estimated_click_loss > 0 && <span className="text-red-400"><span className="font-semibold">{Math.round(item.data.gsc_impact.estimated_click_loss)}</span> est. lost clicks</span>}
                        </div>
                      )}
                      {item.data?.sample_urls?.length > 0 && (
                        <div className="border-t border-border/50 pt-1.5">
                          {(item.data.sample_urls as string[]).slice(0, 2).map((url: string, i: number) => (
                            <p key={i} className="text-[9px] text-muted-foreground/60 font-mono truncate">{url}</p>
                          ))}
                        </div>
                      )}
                      {(item.data?.revenue_impact?.sessions > 0 || item.data?.revenue_impact?.revenue > 0) && (
                        <div className="flex gap-3 text-[10px] text-muted-foreground border-t border-border/50 pt-1.5">
                          {item.data.revenue_impact.sessions > 0 && <span><span className="font-semibold text-foreground">{Math.round(item.data.revenue_impact.sessions).toLocaleString()}</span> sessions</span>}
                          {item.data.revenue_impact.key_events > 0 && <span><span className="font-semibold text-foreground">{Math.round(item.data.revenue_impact.key_events)}</span> key events</span>}
                          {item.data.revenue_impact.transactions > 0 && <span><span className="font-semibold text-foreground">{Math.round(item.data.revenue_impact.transactions)}</span> transactions</span>}
                          {item.data.revenue_impact.revenue > 0 && <span><span className="font-semibold text-foreground">${item.data.revenue_impact.revenue.toFixed(2)}</span> revenue</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-5 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-primary" />
                      Google + runtime signals
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Search Console shows Google performance. Snippet shows what real browsers see after JS renders.
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <TinyPill label={searchConsole?.connected ? 'GSC connected' : 'GSC missing'} />
                    {gscPerformance?.property_url && (
                      <span className="text-[9px] text-muted-foreground/60 font-mono truncate max-w-[160px]" title={gscPerformance.property_url}>{gscPerformance.property_url}</span>
                    )}
                    {gscPerformance?.synced_at && (
                      <span className="text-[9px] text-muted-foreground/50">Synced {new Date(gscPerformance.synced_at).toLocaleDateString()}</span>
                    )}
                    {gscPerformance?.generated_at && (
                      <span className="text-[9px] text-muted-foreground/40">Data as of {new Date(gscPerformance.generated_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-muted/30 p-3">
                    <p className="text-lg font-bold text-foreground">{Math.round(gscPerformance?.totals?.impressions ?? searchConsole?.totals?.impressions ?? 0).toLocaleString()}</p>
                    <p className="text-[11px] text-muted-foreground">GSC impressions</p>
                  </div>
                  <div className="rounded-lg bg-muted/30 p-3">
                    <p className="text-lg font-bold text-foreground">{Math.round(gscPerformance?.totals?.clicks ?? searchConsole?.totals?.clicks ?? 0).toLocaleString()}</p>
                    <p className="text-[11px] text-muted-foreground">GSC clicks</p>
                  </div>
                  <div className="rounded-lg bg-muted/30 p-3">
                    <p className="text-lg font-bold text-foreground">{((gscPerformance?.totals?.ctr ?? searchConsole?.totals?.ctr ?? 0) * 100).toFixed(1)}%</p>
                    <p className="text-[11px] text-muted-foreground">Average CTR</p>
                  </div>
                  <div className="rounded-lg bg-muted/30 p-3">
                    <p className="text-lg font-bold text-foreground">{(gscPerformance?.totals?.position ?? searchConsole?.totals?.position ?? 0).toFixed(1)}</p>
                    <p className="text-[11px] text-muted-foreground">Avg position</p>
                  </div>
                  <div className="rounded-lg bg-muted/30 p-3 col-span-2">
                    <p className="text-lg font-bold text-foreground">{snippetInsights.length}</p>
                    <p className="text-[11px] text-muted-foreground">Runtime insights</p>
                    {/* Inline GSC top queries/pages when available */}
                    {snippetInsightsQuery.data?.events_analyzed != null && (
                      <p className="text-[10px] text-muted-foreground/60 mt-0.5">{snippetInsightsQuery.data.events_analyzed.toLocaleString()} events analyzed</p>
                    )}
                  </div>
                </div>
                {snippetInsightsQuery.data?.message && snippetInsights.length === 0 && (
                  <p className="text-xs text-muted-foreground italic">{snippetInsightsQuery.data.message}</p>
                )}
                {/* GSC top queries */}
                {(gscPerformance?.top_queries ?? []).length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Top GSC queries</p>
                    <div className="space-y-1">
                      {(gscPerformance.top_queries as any[]).slice(0, 5).map((q: any, i: number) => (
                        <div key={i} className="flex items-center justify-between gap-2 text-[10px]">
                          <span className="text-foreground truncate">{q.query || q.keys?.[0] || q}</span>
                          <span className="text-muted-foreground flex-shrink-0">{q.clicks ?? 0} clk · pos {q.position ? q.position.toFixed(1) : '—'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* GSC top pages */}
                {(gscPerformance?.top_pages ?? []).length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Top GSC pages</p>
                    <div className="space-y-1">
                      {(gscPerformance.top_pages as any[]).slice(0, 5).map((p: any, i: number) => (
                        <div key={i} className="flex items-center justify-between gap-2 text-[10px]">
                          <span className="text-foreground font-mono truncate">{p.page || p.keys?.[0] || p}</span>
                          <span className="text-muted-foreground flex-shrink-0">{p.clicks ?? 0} clk</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* GSC sitemaps */}
                {(gscPerformance?.sitemaps ?? []).length > 0 && (
                  <div className="mt-3">
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Sitemaps ({gscPerformance.sitemaps.length})</p>
                    <div className="space-y-0.5">
                      {(gscPerformance.sitemaps as any[]).slice(0, 3).map((sm: any, i: number) => (
                        <p key={i} className="text-[10px] font-mono text-muted-foreground truncate">{sm.path || sm}</p>
                      ))}
                    </div>
                  </div>
                )}
                {snippetInsights.slice(0, 3).map((item) => (
                  <div key={`${item.type}-${item.page_url}`} className="rounded-lg border border-border bg-background p-3">
                    <p className="text-xs font-semibold text-foreground">{item.title}</p>
                    <p className="text-[11px] text-muted-foreground mt-1">{item.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-6">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Root causes</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    {totalGroupedAffected > 0
                      ? `${totalGroupedAffected} affected pages/items grouped into clearer root causes.`
                      : 'Run a crawl to populate grouped issues.'}
                  </p>
                </div>
                <Link to="/dashboard/issues" className="text-xs text-primary hover:underline">Open full issues workspace</Link>
              </div>
              <div className="mt-4 grid xl:grid-cols-2 gap-4">
                {groups.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-border bg-background p-6 text-sm text-muted-foreground">
                    No grouped issues yet.
                  </div>
                ) : (
                  groups.slice(0, 6).map((group: any) => (
                    <article key={`${group.type}-${group.category}`} className="rounded-xl border border-border bg-background p-4 space-y-3">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-foreground">{group.title}</p>
                          <p className="text-xs text-muted-foreground mt-1">{group.summary}</p>
                          {group.severity_explanation && (
                            <p className="text-[11px] text-muted-foreground/70 mt-1 italic">{group.severity_explanation}</p>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                          <TinyPill label={`${group.count} affected`} />
                          {group.severity && (
                            <TinyPill
                              label={group.severity}
                              className={
                                group.severity === 'critical' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                                group.severity === 'high' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
                                group.severity === 'medium' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                'bg-blue-500/10 text-blue-400 border-blue-500/20'
                              }
                            />
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        {group.fix_type && (
                          <TinyPill
                            label={group.fix_type === 'auto' ? 'Auto-fixable' : group.fix_type === 'semi_auto' ? 'Semi-auto' : 'Manual'}
                            className={group.fix_type === 'auto' ? 'bg-green-500/10 text-green-400 border-green-500/20' : group.fix_type === 'semi_auto' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' : 'bg-muted text-muted-foreground border-border'}
                          />
                        )}
                        {group.can_bulk_fix && (
                          <TinyPill label="Bulk fixable" className="bg-violet-500/10 text-violet-400 border-violet-500/20" />
                        )}
                        {group.total_impact != null && (
                          <TinyPill label={`Impact: ${group.total_impact}`} className="bg-muted text-muted-foreground border-border" />
                        )}
                        {group.category && (
                          <TinyPill label={group.category} className="bg-muted text-muted-foreground/70 border-border capitalize" />
                        )}
                      </div>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <div className="rounded-lg bg-muted/30 p-3">
                          <p className="text-xs font-semibold text-foreground mb-1">Why it matters</p>
                          <p className="text-xs text-muted-foreground">{group.why_it_matters}</p>
                        </div>
                        <div className="rounded-lg bg-muted/30 p-3">
                          <p className="text-xs font-semibold text-foreground mb-1">Recommended fix</p>
                          <p className="text-xs text-muted-foreground">{group.recommended_fix}</p>
                        </div>
                      </div>
                      {group.examples?.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-foreground mb-2">Examples</p>
                          <div className="space-y-2">
                            {group.examples.slice(0, 3).map((example: any, index: number) => (
                              <div key={`${group.type}-${index}`} className="rounded-lg border border-border bg-card px-3 py-2">
                                <p className="text-xs text-foreground truncate">{example.url || 'Site-wide issue'}</p>
                                {example.current_value && (
                                  <p className="text-[11px] text-muted-foreground mt-1 truncate font-mono">{example.current_value}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {group.fix_workflow && (
                        <div className="rounded-lg border border-border bg-card p-3 space-y-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="flex items-center gap-2 flex-wrap">
                                <p className="text-xs font-semibold text-foreground">Fix workflow</p>
                                {group.fix_workflow.status && (
                                  <TinyPill
                                    label={group.fix_workflow.status.replace(/_/g, ' ')}
                                    className={
                                      group.fix_workflow.status === 'ready' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                                      group.fix_workflow.status === 'cannot_auto_fix' ? 'bg-muted text-muted-foreground border-border' :
                                      'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                    }
                                  />
                                )}
                                {group.fix_workflow.affected_count != null && (
                                  <span className="text-[11px] text-muted-foreground">{group.fix_workflow.affected_count} items</span>
                                )}
                              </div>
                              <p className="text-[11px] text-muted-foreground mt-1">{group.fix_workflow.truth_note}</p>
                            </div>
                            <TinyPill label={group.fix_workflow.can_create_github_pr ? 'GitHub PR ready' : 'Needs setup'} />
                          </div>
                          <div className="grid sm:grid-cols-2 gap-2">
                            <TinyPill
                              label={group.fix_workflow.ai_configured ? 'AI ready' : 'AI key required'}
                              className={group.fix_workflow.ai_configured ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-slate-500/10 text-slate-300 border-slate-500/20'}
                            />
                            <TinyPill
                              label={`Permission: ${connection?.permission_level || 'audit_only'}`}
                              className={connection?.permission_level === 'pr_only' ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}
                            />
                          </div>
                          {group.fix_workflow.missing_requirements?.length > 0 && (
                            <ul className="space-y-1">
                              {group.fix_workflow.missing_requirements.map((item: string) => (
                                <li key={item} className="text-[11px] text-amber-300">{item}</li>
                              ))}
                            </ul>
                          )}
                          <div className="flex flex-wrap gap-2">
                            <button
                              onClick={() => planRootCauseFix.mutate(group)}
                              disabled={planRootCauseFix.isPending}
                              className="h-8 px-3 rounded-lg border border-border text-xs text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                            >
                              {group.fix_workflow.action_label || 'View exact fix steps'}
                            </button>
                            {group.fix_workflow.can_preview_ai && (
                              <button
                                onClick={() => previewAiFix.mutate(group)}
                                disabled={previewAiFix.isPending}
                                className="h-8 px-3 rounded-lg border border-cyan-500/30 text-xs text-cyan-300 hover:bg-cyan-500/10 transition-colors disabled:opacity-50"
                              >
                                {previewAiFix.isPending ? 'Planning...' : 'Preview AI fix'}
                              </button>
                            )}
                            {group.fix_workflow.can_create_github_pr && (
                              <button
                                onClick={() => createGithubPr.mutate(group)}
                                disabled={createGithubPr.isPending}
                                className="h-8 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                              >
                                Create GitHub PR
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </article>
                  ))
                )}
              </div>
            </div>

            {workflowPanel && (
              <div className="rounded-xl border border-primary/30 bg-primary/5 p-5 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">{workflowPanel.title || 'Root-cause fix workflow'}</h3>
                    <p className="text-xs text-muted-foreground mt-1">{workflowPanel.summary || workflowPanel.github?.message}</p>
                  </div>
                  <button onClick={() => setWorkflowPanel(null)} className="text-xs text-muted-foreground hover:text-foreground">Close</button>
                </div>
                {workflowPanel.fix_workflow?.manual_steps?.length > 0 && (
                  <ol className="space-y-2">
                    {workflowPanel.fix_workflow.manual_steps.map((step: string, index: number) => (
                      <li key={step} className="text-xs text-muted-foreground">
                        <span className="font-semibold text-foreground">{index + 1}. </span>{step}
                      </li>
                    ))}
                  </ol>
                )}
                {workflowPanel.github?.pr_url && (
                  <a href={workflowPanel.github.pr_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-xs text-primary hover:underline">
                    Open GitHub PR <ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {workflowPanel.ai_preview && (
                  <div className="rounded-lg border border-border bg-background p-4 space-y-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <TinyPill label={`Mode: ${workflowPanel.ai_preview.mode}`} />
                      <TinyPill label={`Risk: ${workflowPanel.ai_preview.risk_level}`} />
                      <TinyPill label={workflowPanel.ai_preview.safety?.ok ? 'Safety passed' : 'Safety blocked'} className={workflowPanel.ai_preview.safety?.ok ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'} />
                    </div>
                    <p className="text-xs text-muted-foreground">{workflowPanel.ai_preview.patch_summary || workflowPanel.ai_preview.summary}</p>
                    {workflowPanel.ai_preview.proposed_files_to_change?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-foreground mb-1">Files AutoSEO wants to change</p>
                        <ul className="space-y-1">
                          {workflowPanel.ai_preview.proposed_files_to_change.map((path: string) => (
                            <li key={path} className="text-xs text-muted-foreground font-mono">{path}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {workflowPanel.ai_preview.missing_user_data?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-foreground mb-1">Missing user data before this is safe</p>
                        <ul className="space-y-1">
                          {workflowPanel.ai_preview.missing_user_data.map((item: string) => (
                            <li key={item} className="text-xs text-amber-300">{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {workflowPanel.ai_preview.safety?.errors?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-red-300 mb-1">Safety errors</p>
                        <ul className="space-y-1">
                          {workflowPanel.ai_preview.safety.errors.map((item: string) => (
                            <li key={item} className="text-xs text-red-300">{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {tab === 'pages' && (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Pages</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Page-level crawl results with source mapping when AutoSEO knows the backing CMS resource.
                </p>
              </div>
              {pagesQuery.data?.crawl_context?.monitoring_mode && (
                <TinyPill label={`Monitoring: ${pagesQuery.data.crawl_context.monitoring_mode}`} />
              )}
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">URL</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Score</th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden sm:table-cell">Issues</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Words</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Response</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Source</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden xl:table-cell">First Seen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {pages.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-sm text-muted-foreground">No page data yet.</td>
                  </tr>
                ) : (
                  pages.map((page: any) => {
                    const statusCode = page.status_code
                    const statusColor = !statusCode ? 'text-muted-foreground'
                      : statusCode < 300 ? 'text-green-500'
                      : statusCode < 400 ? 'text-amber-500'
                      : 'text-red-500'
                    const isSelected = selectedPageId === page.id
                    return (
                      <tr key={page.id}
                        onClick={() => setSelectedPageId(isSelected ? null : page.id)}
                        className={`cursor-pointer hover:bg-muted/20 transition-colors ${isSelected ? 'bg-primary/5 border-l-2 border-l-primary' : ''}`}>
                        <td className="px-4 py-3 min-w-0 max-w-xs">
                          <div>
                            <p className="font-medium text-foreground truncate">{page.title || page.url}</p>
                            <p className="text-xs text-muted-foreground truncate">{page.url}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap"><ScoreBadge score={page.seo_score} /></td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-xs font-semibold ${statusColor}`}>{statusCode ?? '—'}</span>
                        </td>
                        <td className="px-4 py-3 text-center text-muted-foreground hidden sm:table-cell">{page.issue_count}</td>
                        <td className="px-4 py-3 text-right text-xs text-muted-foreground hidden md:table-cell whitespace-nowrap">
                          {page.word_count != null ? page.word_count.toLocaleString() : '—'}
                        </td>
                        <td className="px-4 py-3 text-right text-xs text-muted-foreground hidden md:table-cell whitespace-nowrap">
                          {page.response_time_ms != null ? `${page.response_time_ms}ms` : '—'}
                        </td>
                        <td className="px-4 py-3 text-xs text-muted-foreground hidden lg:table-cell">
                          {page.source ? (
                            <div>
                              <p className="text-foreground">{page.source.connection_type}</p>
                              <p className="truncate max-w-[140px]">{page.source.source_path || page.source.source_page_id || page.source.source_url}</p>
                            </div>
                          ) : (
                            'No source'
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-muted-foreground hidden xl:table-cell whitespace-nowrap">
                          {page.created_at ? new Date(page.created_at).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>

            {selectedPageId && (
              <div className="border-t border-border bg-muted/10 px-5 py-4">
                {pageDetailQuery.isLoading ? (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Loading page detail…
                  </div>
                ) : pageDetailQuery.data ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold text-foreground">{pageDetailQuery.data.title || pageDetailQuery.data.url}</p>
                      <button onClick={() => setSelectedPageId(null)} className="text-[10px] text-muted-foreground hover:text-foreground">✕ Close</button>
                    </div>
                    {pageDetailQuery.data.meta_description && (
                      <p className="text-[11px] text-muted-foreground italic border border-border/50 rounded-lg px-3 py-2 bg-muted/20">
                        <span className="font-semibold not-italic text-foreground/70 mr-1.5">Meta:</span>{pageDetailQuery.data.meta_description}
                      </p>
                    )}
                    {pageDetailQuery.data.h1_text?.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {(Array.isArray(pageDetailQuery.data.h1_text) ? pageDetailQuery.data.h1_text : [pageDetailQuery.data.h1_text]).slice(0, 3).map((h: string, i: number) => (
                          <span key={i} className="text-[10px] font-semibold text-foreground bg-muted/40 border border-border/50 rounded px-2 py-0.5"><span className="text-muted-foreground mr-1">H1</span>{h}</span>
                        ))}
                      </div>
                    )}
                    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
                      {[
                        { label: 'SEO Score', val: pageDetailQuery.data.seo_score != null ? Math.round(pageDetailQuery.data.seo_score) : '—' },
                        { label: 'Words', val: pageDetailQuery.data.word_count ?? '—' },
                        { label: 'H1', val: pageDetailQuery.data.h1_count ?? 0 },
                        { label: 'H2', val: pageDetailQuery.data.h2_count ?? 0 },
                        { label: 'H3', val: pageDetailQuery.data.h3_count ?? 0 },
                        { label: 'In-links', val: pageDetailQuery.data.incoming_links_count ?? 0 },
                        { label: 'Int. links', val: pageDetailQuery.data.internal_links_count ?? 0 },
                        { label: 'Ext. links', val: pageDetailQuery.data.external_links_count ?? 0 },
                        { label: 'Broken links', val: pageDetailQuery.data.broken_links_count ?? 0 },
                        { label: 'Images', val: pageDetailQuery.data.images_count ?? 0 },
                        { label: 'Missing alt', val: pageDetailQuery.data.images_missing_alt ?? 0 },
                        { label: 'Title len', val: pageDetailQuery.data.title_length ?? '—' },
                        { label: 'Meta len', val: pageDetailQuery.data.meta_description_length ?? '—' },
                        { label: 'Depth', val: pageDetailQuery.data.crawl_depth ?? '—' },
                        { label: 'Status', val: pageDetailQuery.data.status_code ?? '—' },
                        { label: 'Response', val: pageDetailQuery.data.response_time_ms != null ? `${pageDetailQuery.data.response_time_ms}ms` : '—' },
                        { label: 'Crawled', val: pageDetailQuery.data.created_at ? new Date(pageDetailQuery.data.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '—' },
                      ].map(({ label, val }) => (
                        <div key={label} className="rounded-lg bg-muted/40 px-2.5 py-2 text-center">
                          <p className="text-sm font-bold text-foreground">{val}</p>
                          <p className="text-[9px] text-muted-foreground">{label}</p>
                        </div>
                      ))}
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {(pageDetailQuery.data.lcp_ms != null || pageDetailQuery.data.cls_score != null || pageDetailQuery.data.ttfb_ms != null || pageDetailQuery.data.performance_score != null) && (
                        <div className="rounded-lg border border-border bg-background p-3">
                          <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Core Web Vitals</p>
                          <div className="space-y-1 text-xs">
                            {pageDetailQuery.data.performance_score != null && <p className="flex justify-between"><span className="text-muted-foreground">Performance</span><span className="font-bold text-foreground">{Math.round(pageDetailQuery.data.performance_score)}</span></p>}
                            {pageDetailQuery.data.lcp_ms != null && <p className="flex justify-between"><span className="text-muted-foreground">LCP</span><span className={`font-semibold ${pageDetailQuery.data.lcp_ms <= 2500 ? 'text-green-400' : pageDetailQuery.data.lcp_ms <= 4000 ? 'text-amber-400' : 'text-red-400'}`}>{pageDetailQuery.data.lcp_ms}ms</span></p>}
                            {pageDetailQuery.data.cls_score != null && <p className="flex justify-between"><span className="text-muted-foreground">CLS</span><span className={`font-semibold ${pageDetailQuery.data.cls_score <= 0.1 ? 'text-green-400' : pageDetailQuery.data.cls_score <= 0.25 ? 'text-amber-400' : 'text-red-400'}`}>{pageDetailQuery.data.cls_score.toFixed(3)}</span></p>}
                            {pageDetailQuery.data.ttfb_ms != null && <p className="flex justify-between"><span className="text-muted-foreground">TTFB</span><span className={`font-semibold ${pageDetailQuery.data.ttfb_ms <= 800 ? 'text-green-400' : pageDetailQuery.data.ttfb_ms <= 1800 ? 'text-amber-400' : 'text-red-400'}`}>{pageDetailQuery.data.ttfb_ms}ms</span></p>}
                          </div>
                        </div>
                      )}

                      <div className="rounded-lg border border-border bg-background p-3">
                        <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Meta / Social</p>
                        <div className="space-y-1 text-xs">
                          <p className="flex justify-between gap-2"><span className="text-muted-foreground shrink-0">Canonical</span><span className="font-mono text-[10px] truncate text-foreground">{pageDetailQuery.data.canonical_url ?? '—'}</span></p>
                          <p className="flex justify-between gap-2"><span className="text-muted-foreground shrink-0">Robots</span><span className="font-mono text-[10px] text-foreground">{pageDetailQuery.data.robots_directive ?? '—'}</span></p>
                          {pageDetailQuery.data.og_title && <p className="flex justify-between gap-2"><span className="text-muted-foreground shrink-0">OG title</span><span className="text-[10px] truncate text-foreground">{pageDetailQuery.data.og_title}</span></p>}
                          {pageDetailQuery.data.og_description && <p className="flex justify-between gap-2"><span className="text-muted-foreground shrink-0">OG desc</span><span className="text-[10px] truncate text-foreground">{pageDetailQuery.data.og_description}</span></p>}
                          {pageDetailQuery.data.og_image && <p className="flex justify-between gap-2"><span className="text-muted-foreground shrink-0">OG image</span><span className="text-[10px] text-cyan-300 truncate">{pageDetailQuery.data.og_image}</span></p>}
                          {pageDetailQuery.data.twitter_card && <p className="flex justify-between gap-2"><span className="text-muted-foreground shrink-0">Twitter card</span><span className="text-[10px] text-foreground">{pageDetailQuery.data.twitter_card}</span></p>}
                          {pageDetailQuery.data.redirect_url && <p className="flex justify-between gap-2"><span className="text-muted-foreground shrink-0">Redirect</span><span className="font-mono text-[10px] text-amber-400 truncate">{pageDetailQuery.data.redirect_url}</span></p>}
                          {pageDetailQuery.data.redirect_chain && pageDetailQuery.data.redirect_chain.length > 0 && <p className="flex justify-between gap-2"><span className="text-muted-foreground shrink-0">Chain hops</span><span className="text-[10px] font-semibold text-amber-400">{pageDetailQuery.data.redirect_chain.length}</span></p>}
                        </div>
                      </div>
                      {(Object.keys(pageDetailQuery.data.hreflang_tags ?? {}).length > 0 || pageDetailQuery.data.hreflang_errors?.length > 0) && (
                        <div className="rounded-lg border border-border bg-background p-3">
                          <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Hreflang</p>
                          {Object.entries(pageDetailQuery.data.hreflang_tags as Record<string, string>).slice(0, 6).map(([lang, url]) => (
                            <p key={lang} className="flex justify-between gap-2 text-xs mb-0.5"><span className="text-muted-foreground font-mono shrink-0">{lang}</span><span className="text-[10px] truncate text-foreground">{url}</span></p>
                          ))}
                          {pageDetailQuery.data.hreflang_errors?.length > 0 && (
                            <div className="mt-1.5 space-y-0.5">
                              {(pageDetailQuery.data.hreflang_errors as string[]).map((e: string, i: number) => (
                                <p key={i} className="text-[10px] text-red-400">• {e}</p>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      <div className="rounded-lg border border-border bg-background p-3">
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">Schema</p>
                          {pageDetailQuery.data.schema_types?.length > 0 && pageDetailQuery.data.schema_valid != null && (
                            <span className={`text-[8px] px-1.5 py-0.5 rounded-full border font-semibold ${pageDetailQuery.data.schema_valid ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                              {pageDetailQuery.data.schema_valid ? '✓ Valid' : '✗ Invalid'}
                            </span>
                          )}
                        </div>
                        {pageDetailQuery.data.schema_types?.length > 0 ? (
                          <div className="flex flex-wrap gap-1 mb-2">
                            {(pageDetailQuery.data.schema_types as string[]).map((t: string) => (
                              <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">{t}</span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-muted-foreground mb-2">No schema detected</p>
                        )}
                        {pageDetailQuery.data.schema_errors?.length > 0 && (
                          <div className="space-y-0.5">
                            {(pageDetailQuery.data.schema_errors as string[]).map((e: string, i: number) => (
                              <p key={i} className="text-[10px] text-red-400">• {e}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {pageDetailQuery.data.heading_structure?.length > 0 && (
                      <div className="rounded-lg border border-border bg-background p-3">
                        <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Heading structure</p>
                        <div className="space-y-0.5">
                          {(pageDetailQuery.data.heading_structure as any[]).slice(0, 8).map((h: any, i: number) => (
                            <p key={i} className="text-[10px] text-foreground" style={{ paddingLeft: `${(h.level - 1) * 12}px` }}>
                              <span className="text-muted-foreground font-mono mr-1.5">H{h.level}</span>{h.text}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}

                    {pageDetailQuery.data.issues?.length > 0 && (
                      <div className="rounded-lg border border-border bg-background p-3">
                        <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Issues on this page ({pageDetailQuery.data.issues.length})</p>
                        <div className="space-y-1.5">
                          {(pageDetailQuery.data.issues as any[]).map((issue: any) => (
                            <div key={issue.id} className="flex items-start gap-2">
                              <span className={`mt-0.5 h-1.5 w-1.5 rounded-full flex-shrink-0 ${issue.severity === 'critical' ? 'bg-red-500' : issue.severity === 'high' ? 'bg-red-400' : issue.severity === 'medium' ? 'bg-amber-400' : 'bg-muted-foreground/40'}`} />
                              <div className="min-w-0 flex-1">
                                <p className="text-[10px] font-semibold text-foreground">{ISSUE_LABELS[issue.type] ?? issue.type.replace(/_/g, ' ')}</p>
                                {issue.current_value && <p className="text-[10px] text-muted-foreground truncate">Current: {issue.current_value}</p>}
                                {issue.proposed_fix && <p className="text-[10px] text-green-400/80 truncate">Fix: {issue.proposed_fix}</p>}
                                <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                                  {issue.category && <span className="text-[9px] text-muted-foreground/70 capitalize">{issue.category}</span>}
                                  {issue.impact_score != null && <span className="text-[9px] text-muted-foreground/70">impact {issue.impact_score}</span>}
                                  {issue.fix_status && <span className={`text-[9px] px-1 py-0.5 rounded border ${issue.fix_status === 'pending' ? 'bg-muted/50 text-muted-foreground border-border' : issue.fix_status === 'deployed' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>{issue.fix_status}</span>}
                                  {issue.created_at && <span className="text-[9px] text-muted-foreground/50">{new Date(issue.created_at).toLocaleDateString()}</span>}
                                </div>
                              </div>
                              <span className={`text-[9px] shrink-0 px-1.5 py-0.5 rounded-full border ${issue.fix_type === 'auto' ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20' : 'bg-muted/50 text-muted-foreground border-border'}`}>{issue.fix_type}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        )}

        {tab === 'log' && (
          <div className="space-y-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-border">
                <h3 className="text-sm font-semibold text-foreground">Change Log</h3>
                <p className="text-xs text-muted-foreground mt-1">Append-only audit trail of all automated and manual actions for this site.</p>
              </div>
              {changeLogQuery.isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-5 w-5 text-primary animate-spin" />
                </div>
              ) : (changeLogQuery.data?.entries ?? []).length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center px-4">
                  <CheckCircle2 className="h-8 w-8 text-muted-foreground/30 mb-3" />
                  <p className="text-sm text-muted-foreground">No changes logged yet</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">Dismissed issues and applied fixes will appear here.</p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {(changeLogQuery.data?.entries ?? []).map((entry: any) => (
                    <div key={entry.id} className="px-5 py-4">
                      <div className="flex items-start justify-between gap-4 flex-wrap">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-semibold ${
                              entry.action === 'bulk_dismiss' || entry.action === 'dismiss' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' :
                              entry.action === 'fix_deployed' || entry.action === 'fix_applied' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                              entry.action === 'fix_rolled_back' || entry.action === 'rollback' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
                              entry.action === 'fix_approved' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                              entry.action === 'fix_apply_failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                              entry.action === 'crawl_complete' || entry.action === 'crawl_started' ? 'bg-violet-500/10 text-violet-400 border-violet-500/20' :
                              entry.action === 'ownership_verified' ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                              'bg-blue-500/10 text-blue-500 border-blue-500/20'
                            }`}>
                              {entry.action.replace(/_/g, ' ')}
                            </span>
                            <span className="text-xs text-muted-foreground capitalize">{entry.actor_type}</span>
                          </div>
                          {entry.metadata && (
                            <div className="mt-1.5 text-xs text-muted-foreground">
                              {entry.metadata.count !== undefined && <span>{entry.metadata.count} issue(s) affected</span>}
                              {entry.metadata.reason && entry.metadata.reason !== 'dismissed_by_user' && <span className="ml-2">· {entry.metadata.reason}</span>}
                            </div>
                          )}
                          {entry.old_value && entry.new_value && (
                            <p className="text-xs text-muted-foreground mt-1">
                              <span className="line-through text-red-400/70">{entry.old_value}</span>
                              <span className="mx-1">→</span>
                              <span className="text-green-400/70">{entry.new_value}</span>
                            </p>
                          )}
                        </div>
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {entry.created_at ? formatRelativeTime(entry.created_at) : '—'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {changeLogQuery.data?.total > 0 && (
                <div className="px-5 py-3 border-t border-border text-xs text-muted-foreground">
                  {changeLogQuery.data.total} total entries
                </div>
              )}
            </div>
          </div>
        )}

        {tab === 'fixes' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Pending', value: fixSummary.pending ?? 0 },
                { label: 'Approved', value: fixSummary.approved ?? 0 },
                { label: 'Deployed', value: fixSummary.deployed ?? 0 },
                { label: 'Apply Failed', value: fixSummary.apply_failed ?? 0 },
              ].map((card) => (
                <div key={card.label} className="rounded-xl border border-border bg-card p-5">
                  <p className="text-2xl font-bold text-foreground">{card.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{card.label}</p>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="px-5 py-4 border-b border-border flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Recent site fixes</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    This view keeps raw fix rows available while the main audit stays grouped by root cause.
                  </p>
                </div>
                <Link to="/dashboard/fixes" className="text-xs text-primary hover:underline">Open global fix queue</Link>
              </div>
              <div className="divide-y divide-border">
                {rawIssues.length === 0 ? (
                  <div className="py-12 text-center text-sm text-muted-foreground">No fixable issues found for this site yet.</div>
                ) : (
                  rawIssues.map((issue: any) => (
                    <div key={issue.id} className="px-5 py-4">
                      <div className="flex items-center justify-between gap-4 flex-wrap">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">{ISSUE_TYPE_LABELS[issue.type] || issue.type.replace(/_/g, ' ')}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {issue.fix_type} - {issue.fix_status}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <TinyPill label={issue.severity} />
                          <TinyPill label={issue.fix_status} />
                        </div>
                      </div>
                      {issue.current_value && <p className="text-xs text-muted-foreground mt-2">Current: {issue.current_value}</p>}
                      {issue.proposed_fix && <p className="text-xs text-green-400 mt-1">Proposed: {issue.proposed_fix}</p>}
                      <div className="flex flex-wrap gap-2 mt-2">
                        {issue.ai_confidence != null && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">AI {Math.round(issue.ai_confidence * 100)}%</span>
                        )}
                        {issue.impact_score != null && (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${issue.impact_score >= 70 ? 'bg-red-500/10 text-red-400 border-red-500/20' : issue.impact_score >= 40 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-muted border-border text-muted-foreground'}`}>Impact {issue.impact_score}</span>
                        )}
                        {issue.category && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground capitalize">{issue.category.replace(/_/g, ' ')}</span>
                        )}
                        {issue.fix_type && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 capitalize">{issue.fix_type.replace(/_/g, ' ')}</span>
                        )}
                      </div>
                      {(issue.applied_at || issue.verified_at || issue.rolled_back_at) && (
                        <p className="text-[10px] text-muted-foreground/60 mt-1.5">
                          {issue.applied_at && <span>Applied {new Date(issue.applied_at).toLocaleDateString()}</span>}
                          {issue.verified_at && <span className="ml-2 text-green-400/60">✓ Verified{issue.verified_score != null ? ` score ${issue.verified_score}` : ''}</span>}
                          {issue.rolled_back_at && <span className="ml-2 text-red-400/60">↩ Rolled back {new Date(issue.rolled_back_at).toLocaleDateString()}</span>}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </motion.div>

      <DeleteSiteDialog
        site={site}
        open={showDelete}
        onClose={() => setShowDelete(false)}
        onDeleted={() => navigate('/dashboard/sites')}
      />
    </div>
  )
}
