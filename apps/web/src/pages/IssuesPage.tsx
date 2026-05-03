import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertTriangle, ChevronDown, CheckCircle2, Filter, Globe, Info,
  Layers3, ListTree, Loader2, MinusCircle, Search, Square, TrendingUp, X, XCircle,
} from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient, issuesBulkApi, issuesApi } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'

const SEVERITY_CONFIG: Record<string, { icon: any; className: string; label: string }> = {
  critical: { icon: XCircle, className: 'bg-red-500/10 text-red-500 border-red-500/20', label: 'Critical' },
  high: { icon: AlertTriangle, className: 'bg-orange-500/10 text-orange-500 border-orange-500/20', label: 'High' },
  medium: { icon: AlertTriangle, className: 'bg-amber-500/10 text-amber-500 border-amber-500/20', label: 'Medium' },
  low: { icon: Info, className: 'bg-blue-500/10 text-blue-500 border-blue-500/20', label: 'Low' },
  info: { icon: Info, className: 'bg-slate-500/10 text-slate-500 border-slate-500/20', label: 'Info' },
}

const CATEGORY_LABELS: Record<string, string> = {
  meta: 'Meta Tags',
  headings: 'Headings',
  images: 'Images',
  links: 'Links',
  schema: 'Schema',
  performance: 'Performance',
  social: 'Social',
  content: 'Content',
  technical: 'Technical',
  rendering: 'Rendering',
  security: 'Security',
  mobile: 'Mobile',
}

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
  thin_content: 'Thin Content',
}

const FIX_STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  approved: 'Approved',
  deployed: 'Deployed',
  deployed_after_merge: 'Deployed via PR',
  apply_failed: 'Apply failed',
  rolled_back: 'Rolled back',
  dismissed: 'Dismissed',
  diagnosed: 'Diagnosed',
  github_pr_ready: 'PR ready',
  github_pr_created: 'PR created',
  manual_instructions_ready: 'Manual fix ready',
  cannot_auto_fix: 'Manual fix required',
  rejected_unsafe: 'Rejected (unsafe)',
}

function useGroupedIssues(params: { site_id?: string; severity?: string; fix_status?: string }) {
  const searchParams: Record<string, string> = {}
  if (params.site_id) searchParams.site_id = params.site_id
  if (params.severity) searchParams.severity = params.severity
  if (params.fix_status) searchParams.fix_status = params.fix_status

  return useQuery({
    queryKey: ['issues-aggregated', params],
    queryFn: () => apiClient.get('issues/aggregated', { searchParams }).json<any>(),
  })
}

function useRawIssues(params: { site_id?: string; severity?: string; fix_status?: string; page: number }) {
  const searchParams: Record<string, string> = { page: String(params.page), per_page: '50' }
  if (params.site_id) searchParams.site_id = params.site_id
  if (params.severity) searchParams.severity = params.severity
  if (params.fix_status) searchParams.fix_status = params.fix_status

  return useQuery({
    queryKey: ['issues-raw', params],
    queryFn: () => apiClient.get('issues', { searchParams }).json<any>(),
    placeholderData: (prev: any) => prev,
  })
}

function SeverityBadge({ severity }: { severity: string }) {
  const config = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.info
  const Icon = config.icon
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${config.className}`}>
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  )
}

function FixStatusBadge({ status }: { status: string }) {
  const cls = (status === 'deployed' || status === 'deployed_after_merge') ? 'text-green-500 bg-green-500/10'
    : status === 'dismissed' ? 'text-muted-foreground bg-muted'
    : (status === 'apply_failed' || status === 'rejected_unsafe') ? 'text-red-500 bg-red-500/10'
    : status === 'rolled_back' ? 'text-orange-500 bg-orange-500/10'
    : (status === 'github_pr_created' || status === 'github_pr_ready') ? 'text-cyan-500 bg-cyan-500/10'
    : status === 'approved' ? 'text-blue-500 bg-blue-500/10'
    : status === 'cannot_auto_fix' ? 'text-slate-400 bg-slate-500/10'
    : 'text-amber-500 bg-amber-500/10'
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize ${cls}`}>
      {FIX_STATUS_LABELS[status] ?? status.replace(/_/g, ' ')}
    </span>
  )
}

export default function IssuesPage() {
  const queryClient = useQueryClient()
  const { data: sitesData } = useSites()
  const sites: any[] = sitesData?.sites ?? []
  const [view, setView] = useState<'groups' | 'raw' | 'prioritized'>('groups')
  const [expandedPriority, setExpandedPriority] = useState<string | null>(null)
  const [siteId, setSiteId] = useState<string | null>(null)
  const [severity, setSeverity] = useState<string | null>(null)
  const [fixStatus, setFixStatus] = useState<string>('pending')
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const prioritizedQuery = useQuery({
    queryKey: ['issues-prioritized', siteId],
    queryFn: () => issuesApi.prioritizedIssues(siteId ?? ''),
    enabled: view === 'prioritized',
  })
  const prioritizedItems: any[] = prioritizedQuery.data?.issues ?? []

  const groupedQuery = useGroupedIssues({
    site_id: siteId ?? undefined,
    severity: severity ?? undefined,
    fix_status: fixStatus || undefined,
  })
  const rawQuery = useRawIssues({
    site_id: siteId ?? undefined,
    severity: severity ?? undefined,
    fix_status: fixStatus || undefined,
    page,
  })

  const groups: any[] = groupedQuery.data?.groups ?? []
  const rawIssues: any[] = rawQuery.data?.issues ?? []
  const rawTotal: number = rawQuery.data?.total ?? 0
  const activeFilters = [siteId, severity, fixStatus && fixStatus !== 'pending' ? fixStatus : null].filter(Boolean).length
  const visibleGroups = search
    ? groups.filter(group =>
        `${group.title} ${group.summary} ${group.type} ${group.category}`.toLowerCase().includes(search.toLowerCase())
      )
    : groups
  const visibleRaw = search
    ? rawIssues.filter(issue =>
        `${ISSUE_TYPE_LABELS[issue.type] || issue.type} ${issue.current_value || ''}`.toLowerCase().includes(search.toLowerCase())
      )
    : rawIssues
  const totalGroupedIssues = groups.reduce((sum, group) => sum + (group.count ?? 0), 0)

  const allVisible = visibleRaw.map((i: any) => i.id)
  const allSelected = allVisible.length > 0 && allVisible.every((id: string) => selectedIds.has(id))
  const someSelected = allVisible.some((id: string) => selectedIds.has(id))

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(prev => {
        const next = new Set(prev)
        allVisible.forEach((id: string) => next.delete(id))
        return next
      })
    } else {
      setSelectedIds(prev => new Set([...prev, ...allVisible]))
    }
  }

  const toggleOne = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const dismissMutation = useMutation({
    mutationFn: (ids: string[]) => issuesBulkApi.bulkDismiss(ids, 'dismissed_by_user'),
    onSuccess: (data) => {
      toast.success(`Dismissed ${data.dismissed_count} issue${data.dismissed_count !== 1 ? 's' : ''}`)
      setSelectedIds(new Set())
      queryClient.invalidateQueries({ queryKey: ['issues-raw'] })
      queryClient.invalidateQueries({ queryKey: ['issues-aggregated'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-overview'] })
      queryClient.invalidateQueries({ queryKey: ['site-summary'] })
    },
    onError: async (error: any) => {
      const detail = error?.response ? await error.response.json().catch(() => null) : null
      toast.error(detail?.detail || error?.message || 'Bulk dismiss failed')
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Issues</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Root causes first, raw rows only when you need debugging detail.
            {totalGroupedIssues > 0 && <span className="ml-1 text-foreground font-semibold">({totalGroupedIssues} affected pages/items)</span>}
          </p>
        </div>
        <button onClick={() => setShowFilters(!showFilters)}
          className={`inline-flex items-center gap-2 h-9 px-4 rounded-lg border text-sm font-medium transition-all ${showFilters || activeFilters > 0
            ? 'border-primary/40 bg-primary/10 text-primary'
            : 'border-border text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}>
          <Filter className="h-4 w-4" />
          Filters
          {activeFilters > 0 && (
            <span className="h-4 w-4 rounded-full bg-primary text-primary-foreground text-[10px] font-bold flex items-center justify-center">{activeFilters}</span>
          )}
          <ChevronDown className={`h-3 w-3 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <button onClick={() => setView('groups')}
          className={`inline-flex items-center gap-2 h-9 px-4 rounded-lg border text-sm font-semibold ${view === 'groups' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:text-foreground'}`}>
          <Layers3 className="h-4 w-4" />
          Root causes
        </button>
        <button onClick={() => setView('prioritized')}
          className={`inline-flex items-center gap-2 h-9 px-4 rounded-lg border text-sm font-semibold ${view === 'prioritized' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:text-foreground'}`}>
          <TrendingUp className="h-4 w-4" />
          Priority engine
        </button>
        <button onClick={() => setView('raw')}
          className={`inline-flex items-center gap-2 h-9 px-4 rounded-lg border text-sm font-semibold ${view === 'raw' ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:text-foreground'}`}>
          <ListTree className="h-4 w-4" />
          Raw issues
        </button>
      </div>

      {showFilters && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
          className="bg-card border border-border rounded-xl p-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search root causes"
                className="w-full h-9 bg-background border border-border rounded-lg pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select value={siteId ?? ''} onChange={(e) => { setSiteId(e.target.value || null); setPage(1) }}
                className="w-full h-9 bg-background border border-border rounded-lg pl-9 pr-8 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/30">
                <option value="">All sites</option>
                {sites.map(site => <option key={site.id} value={site.id}>{site.domain || site.name}</option>)}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            </div>
            <div className="relative">
              <select value={severity ?? ''} onChange={(e) => { setSeverity(e.target.value || null); setPage(1) }}
                className="w-full h-9 bg-background border border-border rounded-lg px-3 pr-8 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/30">
                <option value="">All severities</option>
                {Object.entries(SEVERITY_CONFIG).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            </div>
            <div className="relative">
              <select value={fixStatus} onChange={(e) => { setFixStatus(e.target.value); setPage(1) }}
                className="w-full h-9 bg-background border border-border rounded-lg px-3 pr-8 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/30">
                <option value="">All statuses</option>
                {Object.entries(FIX_STATUS_LABELS).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            </div>
          </div>
          {(activeFilters > 0 || search) && (
            <button onClick={() => { setSiteId(null); setSeverity(null); setFixStatus('pending'); setSearch(''); setPage(1) }}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
              <X className="h-3 w-3" /> Clear filters
            </button>
          )}
        </motion.div>
      )}

      {groupedQuery.data?.note && (
        <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-3 text-xs text-blue-200 flex items-start justify-between gap-3">
          <span>{groupedQuery.data.note}</span>
          {groupedQuery.data.total_groups != null && (
            <span className="shrink-0 text-[10px] font-semibold text-blue-300/70">{groupedQuery.data.total_groups} groups</span>
          )}
        </div>
      )}

      {view === 'prioritized' ? (
        prioritizedQuery.isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-8 w-8 text-primary animate-spin" />
          </div>
        ) : prioritizedItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 bg-card border border-dashed border-border rounded-xl text-center">
            <TrendingUp className="h-8 w-8 text-muted-foreground mb-3" />
            <p className="text-sm font-medium text-foreground">No prioritized issues found</p>
            <p className="text-xs text-muted-foreground mt-1">Run a crawl and connect GSC/GA4 to generate priority scores.</p>
            {prioritizedQuery.data?.message && (
              <p className="text-xs text-muted-foreground mt-2 italic">{prioritizedQuery.data.message}</p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {prioritizedQuery.data?.message && (
              <p className="text-xs text-muted-foreground italic">{prioritizedQuery.data.message}</p>
            )}
            {prioritizedItems.map((item: any, index: number) => {
              const isOpen = expandedPriority === `${item.type}-${item.category}`
              const bd = item.breakdown ?? {}
              const gsc = item.gsc_impact ?? {}
              const rev = item.revenue_impact ?? {}
              return (
                <motion.article key={`${item.type}-${item.category}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.02 }}
                  className="rounded-xl border border-border bg-card overflow-hidden">
                  <button
                    className="w-full text-left px-5 py-4 hover:bg-muted/40 transition-colors"
                    onClick={() => setExpandedPriority(isOpen ? null : `${item.type}-${item.category}`)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1.5">
                          <SeverityBadge severity={item.severity} />
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground uppercase tracking-wider">
                            {CATEGORY_LABELS[item.category] ?? item.category}
                          </span>
                          {item.impact_label && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-semibold">
                              {item.impact_label}
                            </span>
                          )}
                          <span className="text-[10px] text-muted-foreground">{item.affected_count} affected</span>
                        </div>
                        <h2 className="text-sm font-semibold text-foreground">{ISSUE_TYPE_LABELS[item.type] || item.type.replace(/_/g, ' ')}</h2>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <div className="text-right">
                          <p className="text-lg font-bold text-foreground">{item.priority_score}</p>
                          <p className="text-[10px] text-muted-foreground">priority</p>
                        </div>
                        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                      </div>
                    </div>
                  </button>
                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden border-t border-border"
                      >
                        <div className="px-5 py-4 space-y-4">
                          <div>
                            <p className="text-xs font-semibold text-foreground mb-2">Impact breakdown</p>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                              {Object.entries(bd).map(([k, v]) => (
                                <div key={k} className="rounded-lg bg-muted/40 px-3 py-2 text-center">
                                  <p className="text-sm font-bold text-foreground">{typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(1)) : String(v)}</p>
                                  <p className="text-[10px] text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                          {(gsc.impressions > 0 || gsc.clicks > 0 || gsc.estimated_click_loss > 0) && (
                            <div>
                              <p className="text-xs font-semibold text-foreground mb-2">Search Console impact</p>
                              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-center"><p className="text-sm font-bold text-foreground">{gsc.impressions?.toLocaleString()}</p><p className="text-[10px] text-muted-foreground">Impressions</p></div>
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-center"><p className="text-sm font-bold text-foreground">{gsc.clicks?.toLocaleString()}</p><p className="text-[10px] text-muted-foreground">Clicks</p></div>
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-center"><p className="text-sm font-bold text-foreground">{gsc.ctr != null ? `${(gsc.ctr * 100).toFixed(1)}%` : '—'}</p><p className="text-[10px] text-muted-foreground">CTR</p></div>
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-center"><p className="text-sm font-bold text-foreground">{gsc.position != null ? gsc.position.toFixed(1) : '—'}</p><p className="text-[10px] text-muted-foreground">Avg position</p></div>
                                {gsc.estimated_click_loss > 0 && <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2 text-center"><p className="text-sm font-bold text-red-400">~{gsc.estimated_click_loss}</p><p className="text-[10px] text-red-400/70">Lost clicks</p></div>}
                              </div>
                            </div>
                          )}
                          {(rev.sessions > 0 || rev.transactions > 0 || rev.revenue > 0) && (
                            <div>
                              <p className="text-xs font-semibold text-foreground mb-2">Revenue / GA4 impact</p>
                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-center"><p className="text-sm font-bold text-foreground">{rev.sessions?.toLocaleString()}</p><p className="text-[10px] text-muted-foreground">Sessions</p></div>
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-center"><p className="text-sm font-bold text-foreground">{rev.key_events?.toLocaleString()}</p><p className="text-[10px] text-muted-foreground">Key events</p></div>
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-center"><p className="text-sm font-bold text-foreground">{rev.transactions?.toLocaleString()}</p><p className="text-[10px] text-muted-foreground">Transactions</p></div>
                                <div className="rounded-lg bg-muted/40 px-3 py-2 text-center"><p className="text-sm font-bold text-foreground">${rev.revenue != null ? rev.revenue.toFixed(2) : '0.00'}</p><p className="text-[10px] text-muted-foreground">Revenue</p></div>
                              </div>
                            </div>
                          )}
                          {item.sample_urls?.length > 0 && (
                            <div>
                              <p className="text-xs font-semibold text-foreground mb-2">Sample URLs</p>
                              <div className="space-y-1">
                                {[...new Set(item.sample_urls as string[])].slice(0, 3).map((url: string, i: number) => (
                                  <p key={i} className="text-[11px] font-mono text-muted-foreground truncate">{url}</p>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.article>
              )
            })}
          </div>
        )
      ) : view === 'groups' ? (
        groupedQuery.isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-8 w-8 text-primary animate-spin" />
          </div>
        ) : visibleGroups.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 bg-card border border-dashed border-border rounded-xl text-center">
            <CheckCircle2 className="h-8 w-8 text-green-500 mb-3" />
            <p className="text-sm font-medium text-foreground">No grouped issues found</p>
            <p className="text-xs text-muted-foreground mt-1">Run a crawl or adjust filters to review results.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {visibleGroups.map((group, index) => (
              <motion.article key={`${group.type}-${group.category}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.03 }}
                className="rounded-xl border border-border bg-card p-5 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <SeverityBadge severity={group.severity} />
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground uppercase tracking-wider">
                        {CATEGORY_LABELS[group.category] ?? group.category}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                        {group.count} affected
                      </span>
                      {group.can_bulk_fix && (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          Bulk-fixable
                        </span>
                      )}
                      {group.fix_type && (
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${group.fix_type === 'auto' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' : 'bg-muted text-muted-foreground border-border'}`}>
                          {group.fix_type === 'auto' ? 'Auto-fixable' : group.fix_type.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                    <h2 className="text-base font-semibold text-foreground">{group.title || ISSUE_TYPE_LABELS[group.type] || group.type}</h2>
                    <p className="text-sm text-muted-foreground mt-1">{group.summary}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <span className="text-xs font-mono text-muted-foreground">Impact {group.total_impact}</span>
                    {group.severity_explanation && (
                      <p className="text-[10px] text-muted-foreground/70 mt-0.5 max-w-[160px] leading-tight">{group.severity_explanation}</p>
                    )}
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 gap-3">
                  <div className="rounded-lg bg-muted/40 p-3">
                    <p className="text-xs font-semibold text-foreground mb-1">Why it matters</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{group.why_it_matters}</p>
                  </div>
                  <div className="rounded-lg bg-muted/40 p-3">
                    <p className="text-xs font-semibold text-foreground mb-1">Recommended fix</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{group.recommended_fix}</p>
                  </div>
                </div>

                {group.examples?.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-foreground mb-2">Examples</p>
                    <div className="space-y-2">
                      {group.examples.slice(0, 4).map((example: any) => (
                        <div key={example.issue_id} className="rounded-lg border border-border bg-background px-3 py-2">
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
                  <div className="rounded-lg border border-border bg-background px-3 py-3 space-y-2">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <p className="text-xs font-semibold text-foreground">Fix workflow</p>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {group.fix_workflow.status && (
                          <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${
                            group.fix_workflow.status === 'ready' ? 'bg-green-500/10 text-green-500 border-green-500/20'
                            : group.fix_workflow.status === 'cannot_auto_fix' ? 'bg-muted text-muted-foreground border-border'
                            : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                          }`}>
                            {group.fix_workflow.status.replace(/_/g, ' ')}
                          </span>
                        )}
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${
                          group.fix_workflow.can_create_github_pr
                            ? 'bg-green-500/10 text-green-500 border-green-500/20'
                            : 'bg-muted text-muted-foreground border-border'
                        }`}>
                          {group.fix_workflow.can_create_github_pr ? 'GitHub PR ready' : group.fix_workflow.action_label ?? 'Setup needed'}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-muted-foreground/70">
                      {group.fix_workflow.required_fix_type && (
                        <span>Fix type: <span className="text-foreground/80 capitalize">{group.fix_workflow.required_fix_type.replace(/_/g, ' ')}</span></span>
                      )}
                      {group.fix_workflow.github_strategy && group.fix_workflow.github_strategy !== 'manual_only' && (
                        <span>Strategy: <span className="text-foreground/80 capitalize">{group.fix_workflow.github_strategy.replace(/_/g, ' ')}</span></span>
                      )}
                      {group.fix_workflow.affected_count != null && (
                        <span>Affected: <span className="text-foreground/80 font-semibold">{group.fix_workflow.affected_count}</span></span>
                      )}
                      {group.fix_workflow.can_preview_ai != null && (
                        <span>AI preview: <span className={group.fix_workflow.can_preview_ai ? 'text-green-400' : 'text-muted-foreground/50'}>{group.fix_workflow.can_preview_ai ? 'available' : 'unavailable'}</span></span>
                      )}
                      {group.fix_workflow.ai_configured === false && group.fix_workflow.can_preview_ai && (
                        <span className="text-amber-400/80">AI not configured</span>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground">{group.fix_workflow.truth_note}</p>
                    {group.fix_workflow.missing_requirements?.length > 0 && (
                      <div className="space-y-1">
                        {group.fix_workflow.missing_requirements.map((item: string) => (
                          <p key={item} className="text-[11px] text-amber-300">• {item}</p>
                        ))}
                      </div>
                    )}
                    {group.fix_workflow.manual_steps?.length > 0 && (
                      <div className="border-t border-border pt-2 space-y-1">
                        <p className="text-[10px] font-semibold text-foreground uppercase tracking-wider">Manual steps</p>
                        {group.fix_workflow.manual_steps.map((step: string, i: number) => (
                          <p key={i} className="text-[11px] text-muted-foreground">{i + 1}. {step}</p>
                        ))}
                      </div>
                    )}
                    {group.fix_workflow.examples?.length > 0 && group.fix_workflow.examples.some((e: any) => e.current_value) && (
                      <div className="border-t border-border pt-2 space-y-1">
                        <p className="text-[10px] font-semibold text-foreground/60 uppercase tracking-wider">Workflow examples</p>
                        {(group.fix_workflow.examples as any[]).slice(0, 2).map((ex: any) => (
                          <div key={ex.issue_id} className="text-[10px] space-y-0.5">
                            {ex.url && <p className="text-muted-foreground/70 truncate">{ex.url}</p>}
                            {ex.current_value && <p className="font-mono text-muted-foreground/60 truncate">{ex.current_value}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </motion.article>
            ))}
          </div>
        )
      ) : (
        rawQuery.isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-8 w-8 text-primary animate-spin" />
          </div>
        ) : (
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            {/* Bulk action bar */}
            {selectedIds.size > 0 && (
              <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-primary/5">
                <span className="text-sm font-medium text-foreground">{selectedIds.size} selected</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => dismissMutation.mutate([...selectedIds])}
                    disabled={dismissMutation.isPending}
                    className="inline-flex items-center gap-2 h-8 px-4 rounded-lg bg-amber-500/10 text-amber-500 border border-amber-500/20 text-xs font-semibold hover:bg-amber-500/20 transition-colors disabled:opacity-50"
                  >
                    <MinusCircle className="h-3.5 w-3.5" />
                    {dismissMutation.isPending ? 'Dismissing...' : `Dismiss ${selectedIds.size}`}
                  </button>
                  <button
                    onClick={() => setSelectedIds(new Set())}
                    className="h-8 px-3 rounded-lg border border-border text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </div>
            )}
            <div className="grid grid-cols-[auto,1fr,auto,auto,auto] gap-4 px-5 py-3 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <button onClick={toggleAll} className="flex items-center justify-center w-4 h-4 mt-0.5">
                {allSelected
                  ? <CheckCircle2 className="h-4 w-4 text-primary" />
                  : someSelected
                    ? <MinusCircle className="h-4 w-4 text-primary/60" />
                    : <Square className="h-4 w-4 text-muted-foreground/40" />
                }
              </button>
              <span>Issue</span>
              <span className="hidden md:block">Category</span>
              <span>Severity</span>
              <span>Status</span>
            </div>
            <div className="divide-y divide-border">
              {visibleRaw.length === 0 ? (
                <div className="py-16 text-center text-sm text-muted-foreground">No raw issues found.</div>
              ) : visibleRaw.map((issue, index) => (
                <motion.div key={issue.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: index * 0.01 }}
                  className={`grid grid-cols-[auto,1fr,auto,auto,auto,auto] gap-4 items-center px-5 py-3.5 hover:bg-muted/50 transition-colors cursor-pointer ${selectedIds.has(issue.id) ? 'bg-primary/5' : ''}`}
                  onClick={() => toggleOne(issue.id)}>
                  <div className="flex items-center justify-center w-4 h-4" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => toggleOne(issue.id)}>
                      {selectedIds.has(issue.id)
                        ? <CheckCircle2 className="h-4 w-4 text-primary" />
                        : <Square className="h-4 w-4 text-muted-foreground/40" />
                      }
                    </button>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{ISSUE_TYPE_LABELS[issue.type] || issue.type.replace(/_/g, ' ')}</p>
                    {issue.current_value && <p className="text-xs text-muted-foreground mt-0.5 truncate font-mono">{issue.current_value}</p>}
                    {issue.proposed_fix && <p className="text-[11px] text-green-400/80 mt-0.5 truncate">↳ {issue.proposed_fix}</p>}
                    {issue.proposed_fix_metadata?.description && (
                      <p className="text-[10px] text-muted-foreground/70 mt-0.5 truncate">{issue.proposed_fix_metadata.description}</p>
                    )}
                    {(issue.applied_at || issue.verified_at || issue.rolled_back_at) && (
                      <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                        {issue.applied_at && <span>Applied {new Date(issue.applied_at).toLocaleDateString()}</span>}
                        {issue.verified_at && <span className="ml-2 text-green-400/60">✓ Verified{issue.verified_score != null ? ` (${issue.verified_score})` : ''}</span>}
                        {issue.rolled_back_at && <span className="ml-2 text-red-400/60">↩ Rolled back {new Date(issue.rolled_back_at).toLocaleDateString()}</span>}
                      </p>
                    )}
                    {issue.created_at && (
                      <p className="text-[10px] text-muted-foreground/40 mt-0.5">Detected {new Date(issue.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</p>
                    )}
                  </div>
                  <span className="text-xs font-medium text-muted-foreground whitespace-nowrap hidden md:block">
                    {CATEGORY_LABELS[issue.category] ?? issue.category}
                  </span>
                  <span className="text-xs font-medium text-muted-foreground whitespace-nowrap hidden lg:block" title="Impact score">
                    {issue.impact_score != null ? (
                      <span className={`font-semibold ${issue.impact_score >= 70 ? 'text-red-400' : issue.impact_score >= 40 ? 'text-amber-400' : 'text-muted-foreground'}`}>
                        {issue.impact_score}
                      </span>
                    ) : '—'}
                    {issue.ai_confidence != null && (
                      <span className="text-muted-foreground/50 ml-0.5 text-[10px]"> AI {Math.round(issue.ai_confidence * 100)}%</span>
                    )}
                  </span>
                  <SeverityBadge severity={issue.severity} />
                  <FixStatusBadge status={issue.fix_status} />
                  {issue.fix_type && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded-full border text-[9px] font-semibold bg-muted/40 text-muted-foreground border-border whitespace-nowrap hidden xl:inline-flex">
                      {issue.fix_type}
                    </span>
                  )}
                </motion.div>
              ))}
            </div>
            {rawTotal > 50 && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-border">
                <span className="text-xs text-muted-foreground">
                  Showing {(page - 1) * 50 + 1}-{Math.min(page * 50, rawTotal)} of {rawTotal}
                </span>
                <div className="flex items-center gap-2">
                  <button onClick={() => setPage(value => Math.max(1, value - 1))} disabled={page === 1}
                    className="h-7 px-3 rounded-md border border-border text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-40 transition-colors">
                    Previous
                  </button>
                  <button onClick={() => setPage(value => value + 1)} disabled={page * 50 >= rawTotal}
                    className="h-7 px-3 rounded-md border border-border text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-40 transition-colors">
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )
      )}
    </div>
  )
}
