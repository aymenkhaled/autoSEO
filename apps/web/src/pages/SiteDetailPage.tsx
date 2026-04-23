import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { motion } from 'framer-motion'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  Globe,
  Loader2,
  RefreshCw,
  Shield,
  Sparkles,
} from 'lucide-react'
import { api, connectionsApi, snippetApi } from '@/lib/api-client'
import { formatRelativeTime } from '@/lib/utils'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'issues', label: 'Issues' },
  { id: 'pages', label: 'Pages' },
  { id: 'settings', label: 'Settings' },
] as const

function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-sm text-muted-foreground">—</span>
  const color = score >= 80
    ? 'text-green-500 bg-green-500/10 border-green-500/20'
    : score >= 60
      ? 'text-amber-500 bg-amber-500/10 border-amber-500/20'
      : 'text-red-500 bg-red-500/10 border-red-500/20'
  return <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-sm font-bold border ${color}`}>{score}</span>
}

function StatusPill({ label, good }: { label: string; good?: boolean }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${good ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'}`}>
      {label}
    </span>
  )
}

export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<typeof TABS[number]['id']>('overview')
  const [activeCrawlId, setActiveCrawlId] = useState<string | null>(null)

  const siteQuery = useQuery({
    queryKey: ['site', id],
    queryFn: () => api.get(`sites/${id}`).json<any>(),
    enabled: !!id,
  })

  const summaryQuery = useQuery({
    queryKey: ['site-summary', id],
    queryFn: () => api.get(`sites/${id}/summary`).json<any>(),
    enabled: !!id,
  })

  const issuesQuery = useQuery({
    queryKey: ['site-issues', id],
    queryFn: () => api.get('issues', { searchParams: { site_id: id!, per_page: 50 } }).json<any>(),
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

  const snippetInstallQuery = useQuery({
    queryKey: ['snippet-install', id],
    queryFn: () => snippetApi.installCode(id!),
    enabled: !!id && connectionQuery.data?.connection_type === 'snippet',
  })

  const crawlProgressQuery = useQuery({
    queryKey: ['crawl-progress', activeCrawlId],
    queryFn: () => api.get(`crawls/${activeCrawlId}`).json<any>(),
    enabled: !!activeCrawlId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && ['completed', 'failed', 'cancelled'].includes(status) ? false : 2000
    },
  })

  const triggerCrawl = useMutation({
    mutationFn: () => api.post('crawls', { json: { site_id: id, trigger: 'manual' } }).json<any>(),
    onSuccess: (crawl) => {
      setActiveCrawlId(crawl.id)
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

  const loading = siteQuery.isLoading || summaryQuery.isLoading
  const site = siteQuery.data
  const summary = summaryQuery.data
  const issues = issuesQuery.data?.issues ?? []
  const pages = pagesQuery.data?.pages ?? []
  const progress = crawlProgressQuery.data

  const onboardingSteps = useMemo(() => {
    return [
      {
        label: 'Ownership verified',
        done: !!site?.ownership_verified,
        action: site?.ownership_verified ? 'Verified' : 'Add the verification meta tag, then click Check',
      },
      {
        label: 'Connection configured',
        done: !!connectionQuery.data?.configured,
        action: connectionQuery.data?.configured ? connectionQuery.data.connection_type : 'Pick a connection method in this site’s settings',
      },
      {
        label: 'First crawl completed',
        done: !!summary?.latest_crawl,
        action: summary?.latest_crawl ? 'Crawl completed' : 'Run the first crawl',
      },
    ]
  }, [connectionQuery.data, site?.ownership_verified, summary?.latest_crawl])

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
              <StatusPill label={site.status} good={site.status === 'active'} />
              <StatusPill label={site.ownership_verified ? 'Verified' : 'Unverified'} good={site.ownership_verified} />
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
              <span>
                Last crawl {site.last_crawled_at ? formatRelativeTime(site.last_crawled_at) : 'never'}
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={() => triggerCrawl.mutate()}
          disabled={triggerCrawl.isPending || (!!progress && ['queued', 'running'].includes(progress.status))}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-semibold hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${triggerCrawl.isPending || progress?.status === 'running' ? 'animate-spin' : ''}`} />
          {progress && ['queued', 'running'].includes(progress.status) ? 'Crawling…' : 'Run Crawl'}
        </button>
      </div>

      {progress && ['queued', 'running'].includes(progress.status) && (
        <div className="bg-card border border-border rounded-xl p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-foreground">Crawl in progress</span>
            <span className="text-muted-foreground">{progress.pages_crawled}/{progress.pages_total ?? '—'} pages</span>
          </div>
          <div className="mt-3 h-2 rounded-full bg-muted overflow-hidden">
            <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-600" style={{ width: `${progress.pages_total ? Math.min((progress.pages_crawled / progress.pages_total) * 100, 100) : 10}%` }} />
          </div>
        </div>
      )}

      <div className="border-b border-border">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {TABS.map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
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
        {tab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Pages', value: summary?.metrics?.pages_count ?? 0 },
                { label: 'Open Issues', value: summary?.metrics?.open_issues ?? 0 },
                { label: 'Deployed Fixes', value: summary?.metrics?.deployed_fixes ?? 0 },
                { label: 'Ownership', value: site.ownership_verified ? 'Verified' : 'Pending' },
              ].map((card) => (
                <div key={card.label} className="rounded-xl border border-border bg-card p-5">
                  <p className="text-2xl font-bold text-foreground">{card.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{card.label}</p>
                </div>
              ))}
            </div>

            <div className="grid lg:grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-card p-6">
                <h3 className="text-sm font-semibold text-foreground mb-4">Onboarding Checklist</h3>
                <div className="space-y-3">
                  {onboardingSteps.map((step) => (
                    <div key={step.label} className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${step.done ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'}`}>
                        <CheckCircle2 className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">{step.label}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{step.action}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-6">
                <h3 className="text-sm font-semibold text-foreground mb-4">Latest Crawl</h3>
                {summary?.latest_crawl ? (
                  <div className="space-y-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Status</span>
                      <StatusPill label={summary.latest_crawl.status} good={summary.latest_crawl.status === 'completed'} />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Pages crawled</span>
                      <span className="font-medium text-foreground">{summary.latest_crawl.pages_crawled}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Issues found</span>
                      <span className="font-medium text-foreground">{summary.latest_crawl.issues_found}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Completed</span>
                      <span className="font-medium text-foreground">
                        {summary.latest_crawl.completed_at ? formatRelativeTime(summary.latest_crawl.completed_at) : '—'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">No crawl data yet.</div>
                )}
              </div>
            </div>
          </div>
        )}

        {tab === 'issues' && (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">Issues</h3>
              <Link to="/dashboard/fixes" className="text-xs text-primary hover:underline">Open Fix Queue</Link>
            </div>
            <div className="divide-y divide-border">
              {issues.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">No issues found for this site.</div>
              ) : (
                issues.map((issue: any) => (
                  <div key={issue.id} className="px-5 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{issue.type.replace(/_/g, ' ')}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {issue.fix_status} · {issue.fix_type}
                        </p>
                      </div>
                      <StatusPill label={issue.severity} good={issue.severity === 'low'} />
                    </div>
                    {issue.current_value && <p className="text-xs text-muted-foreground mt-2">Current: {issue.current_value}</p>}
                    {issue.proposed_fix && <p className="text-xs text-green-600 mt-1">Fix: {issue.proposed_fix}</p>}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {tab === 'pages' && (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">URL</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Score</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Issues</th>
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
                      <td className="px-4 py-3 text-muted-foreground">{page.status_code ?? '—'}</td>
                      <td className="px-4 py-3 text-muted-foreground">{page.issue_count}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'settings' && (
          <div className="space-y-4">
            <div className="rounded-xl border border-border bg-card p-6 space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Ownership Verification</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                {site.ownership_verified
                  ? `Verified ${site.verified_at ? formatRelativeTime(site.verified_at) : ''}`
                  : 'Verify site ownership before treating this property as fully active.'}
              </p>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => startVerification.mutate()}
                  disabled={startVerification.isPending}
                  className="h-9 px-4 rounded-lg border border-border text-sm text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                >
                  {startVerification.isPending ? 'Preparing…' : 'Generate Meta Tag'}
                </button>
                <button
                  onClick={() => checkVerification.mutate()}
                  disabled={checkVerification.isPending}
                  className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {checkVerification.isPending ? 'Checking…' : 'Check Verification'}
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

            <div className="rounded-xl border border-border bg-card p-6 space-y-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Connection</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                {connectionQuery.data?.configured
                  ? `Connected via ${connectionQuery.data.connection_type}`
                  : 'No write connection configured yet.'}
              </p>
              {snippetInstallQuery.data?.script_tag && (
                <code className="block p-3 rounded-lg bg-muted text-xs text-foreground break-all">
                  {snippetInstallQuery.data.script_tag}
                </code>
              )}
              <p className="text-xs text-muted-foreground">
                Connection editing still lives in the dedicated site connection flow; this screen now shows live status and snippet install code.
              </p>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}
