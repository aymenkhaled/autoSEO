import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertTriangle, ChevronDown, CheckCircle2, Filter, Globe, Info,
  Layers3, ListTree, Loader2, Search, X, XCircle,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
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

export default function IssuesPage() {
  const { data: sitesData } = useSites()
  const sites: any[] = sitesData?.sites ?? []
  const [view, setView] = useState<'groups' | 'raw'>('groups')
  const [siteId, setSiteId] = useState<string | null>(null)
  const [severity, setSeverity] = useState<string | null>(null)
  const [fixStatus, setFixStatus] = useState<string>('pending')
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(1)

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
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="deployed">Deployed</option>
                <option value="apply_failed">Apply failed</option>
                <option value="rolled_back">Rolled back</option>
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
        <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-3 text-xs text-blue-200">
          {groupedQuery.data.note}
        </div>
      )}

      {view === 'groups' ? (
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
                    </div>
                    <h2 className="text-base font-semibold text-foreground">{group.title || ISSUE_TYPE_LABELS[group.type] || group.type}</h2>
                    <p className="text-sm text-muted-foreground mt-1">{group.summary}</p>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground">Impact {group.total_impact}</span>
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
            <div className="grid grid-cols-[1fr,auto,auto,auto] gap-4 px-5 py-3 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                  className="grid grid-cols-[1fr,auto,auto,auto] gap-4 items-center px-5 py-3.5 hover:bg-muted/50 transition-colors">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{ISSUE_TYPE_LABELS[issue.type] || issue.type.replace(/_/g, ' ')}</p>
                    {issue.current_value && <p className="text-xs text-muted-foreground mt-0.5 truncate font-mono">{issue.current_value}</p>}
                  </div>
                  <span className="text-xs font-medium text-muted-foreground whitespace-nowrap hidden md:block">
                    {CATEGORY_LABELS[issue.category] ?? issue.category}
                  </span>
                  <SeverityBadge severity={issue.severity} />
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize text-amber-500 bg-amber-500/10">
                    {issue.fix_status}
                  </span>
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
