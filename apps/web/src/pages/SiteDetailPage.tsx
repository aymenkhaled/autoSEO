import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { motion } from 'framer-motion'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
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
import { api, connectionsApi, issuesApi, opportunitiesApi, searchConsoleApi, sitesApi, snippetApi } from '@/lib/api-client'
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
] as const

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
  const [crawlLimit, setCrawlLimit] = useState('500')
  const [workflowPanel, setWorkflowPanel] = useState<any | null>(null)

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
    if (siteQuery.data?.crawl_max_pages) {
      setCrawlLimit(String(siteQuery.data.crawl_max_pages))
    }
  }, [siteQuery.data?.crawl_max_pages])

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
    mutationFn: () => sitesApi.update(id!, { crawl_max_pages: Number(crawlLimit) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['site', id] })
      queryClient.invalidateQueries({ queryKey: ['site-summary', id] })
      toast.success('Crawl limit updated')
    },
    onError: () => toast.error('Crawl limit could not be updated'),
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
  const setup = summary?.setup
  const groups: any[] = groupedIssuesQuery.data?.groups ?? []
  const rawIssues: any[] = rawIssuesQuery.data?.issues ?? []
  const pages = pagesQuery.data?.pages ?? []
  const connection = connectionQuery.data ?? summary?.connection
  const searchConsole = searchConsoleStatusQuery.data ?? summary?.search_console
  const gscPerformance = searchConsolePerformanceQuery.data
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
              {connection && <span>{connection.monitoring_mode_label} monitoring</span>}
              {connection?.write_integration_label && <span>Write integration: {connection.write_integration_label}</span>}
            </div>
          </div>
        </div>

        <button
          onClick={() => triggerCrawl.mutate()}
          disabled={triggerCrawl.isPending || (!!progress && ['queued', 'running'].includes(progress.status))}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-semibold hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${triggerCrawl.isPending || progress?.status === 'running' ? 'animate-spin' : ''}`} />
          {progress && ['queued', 'running'].includes(progress.status) ? 'Crawling...' : 'Run Crawl'}
        </button>
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
                </div>
                <p className="text-sm text-muted-foreground mt-2">{connection?.explanation}</p>
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
                  {connection?.auto_deploy_capable && <TinyPill label="Auto-deploy capable" className="bg-green-500/10 text-green-500 border-green-500/20" />}
                </div>
                <button
                  onClick={() => navigate(`/dashboard/integrations?site_id=${site.id}`)}
                  className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-border text-sm text-foreground hover:bg-muted transition-colors"
                >
                  <Link2 className="h-4 w-4" />
                  Open connection setup
                </button>
                {snippetInstallQuery.data?.script_tag && (
                  <code className="block p-3 rounded-lg bg-muted text-xs text-foreground break-all">
                    {snippetInstallQuery.data.script_tag}
                  </code>
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
                    label={searchConsole?.connected ? 'Connected' : 'Not connected'}
                    className={searchConsole?.connected ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}
                  />
                  {searchConsole?.property_url && <TinyPill label={searchConsole.property_url} />}
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
                </p>
              </div>

              <div className="rounded-xl border border-border bg-card p-6 space-y-3">
                <div className="flex items-center gap-2">
                  <Layers3 className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Crawl coverage</h3>
                </div>
                <p className="text-xs text-muted-foreground">
                  The crawler scans public URLs discovered from the sitemap, then stops at this site's limit. If you saw only 10 pages, this panel shows whether the sitemap only exposed 10 URLs or the limit stopped the crawl.
                </p>
                <label className="text-xs font-medium text-muted-foreground block">Max pages per crawl</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min={1}
                    max={50000}
                    value={crawlLimit}
                    onChange={(event) => setCrawlLimit(event.target.value)}
                    className="w-full h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground"
                  />
                  <button
                    onClick={() => updateCrawlSettings.mutate()}
                    disabled={updateCrawlSettings.isPending || Number(crawlLimit) < 1}
                    className="h-9 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    Save
                  </button>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Current plan limit shown by backend: {summary?.latest_crawl?.crawl_limit ?? site.crawl_max_pages ?? 'not crawled yet'}.
                </p>
              </div>

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
            </div>

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
                <div className="space-y-3">
                  {opportunities.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Connect Search Console, install snippet, or run a crawl to generate prioritized opportunities.</p>
                  ) : opportunities.slice(0, 5).map((item) => (
                    <div key={`${item.source}-${item.type}-${item.affected_url || item.issue_type}`} className="rounded-lg border border-border bg-background p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-foreground">{item.title}</p>
                          <p className="text-[11px] text-muted-foreground mt-1 line-clamp-2">{item.description}</p>
                        </div>
                        <TinyPill label={`${item.priority_score}`} className="bg-cyan-500/10 text-cyan-300 border-cyan-500/20" />
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <TinyPill label={item.source} />
                        {item.impact_label && <TinyPill label={item.impact_label} />}
                      </div>
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
                  <TinyPill label={searchConsole?.connected ? 'GSC connected' : 'GSC missing'} />
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
                    <p className="text-lg font-bold text-foreground">{snippetInsights.length}</p>
                    <p className="text-[11px] text-muted-foreground">Runtime insights</p>
                  </div>
                </div>
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
                        <div>
                          <p className="text-sm font-semibold text-foreground">{group.title}</p>
                          <p className="text-xs text-muted-foreground mt-1">{group.summary}</p>
                        </div>
                        <TinyPill label={`${group.count} affected`} />
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
                              <p className="text-xs font-semibold text-foreground">Fix workflow</p>
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
                              View exact fix steps
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
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Issues</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {pages.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-12 text-center text-sm text-muted-foreground">No page data yet.</td>
                  </tr>
                ) : (
                  pages.map((page: any) => (
                    <tr key={page.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-foreground truncate">{page.title || page.url}</p>
                          <p className="text-xs text-muted-foreground truncate">{page.url}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3"><ScoreBadge score={page.seo_score} /></td>
                      <td className="px-4 py-3 text-muted-foreground">{page.issue_count}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {page.source ? (
                          <div>
                            <p className="text-foreground">{page.source.connection_type}</p>
                            <p className="truncate">{page.source.source_path || page.source.source_page_id || page.source.source_url}</p>
                          </div>
                        ) : (
                          'No source mapping'
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
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
                          <p className="text-sm font-medium text-foreground truncate">{issue.type.replace(/_/g, ' ')}</p>
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
