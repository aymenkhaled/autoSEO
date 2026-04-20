import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Bug, Filter, ChevronDown, AlertTriangle,
  XCircle, Info, CheckCircle2, Search, X, Loader2,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

const SEVERITY_CONFIG: Record<string, { icon: any; className: string; label: string }> = {
  critical: { icon: XCircle,       className: 'bg-red-500/10 text-red-500 border-red-500/20',    label: 'Critical' },
  high:     { icon: AlertTriangle, className: 'bg-orange-500/10 text-orange-500 border-orange-500/20', label: 'High' },
  medium:   { icon: AlertTriangle, className: 'bg-amber-500/10 text-amber-500 border-amber-500/20',  label: 'Medium' },
  low:      { icon: Info,          className: 'bg-blue-500/10 text-blue-500 border-blue-500/20',    label: 'Low' },
  info:     { icon: Info,          className: 'bg-slate-500/10 text-slate-500 border-slate-500/20', label: 'Info' },
}

const CATEGORY_LABELS: Record<string, string> = {
  meta: 'Meta Tags', headings: 'Headings', images: 'Images', links: 'Links',
  schema: 'Schema', performance: 'Performance', social: 'Social', content: 'Content', technical: 'Technical',
}

const ISSUE_TYPE_LABELS: Record<string, string> = {
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

function useIssues(params: { severity?: string; category?: string; fix_status?: string; page: number }) {
  const searchParams: Record<string, string> = { page: String(params.page), per_page: '50' }
  if (params.severity) searchParams.severity = params.severity
  if (params.category) searchParams.category = params.category
  if (params.fix_status) searchParams.fix_status = params.fix_status

  return useQuery({
    queryKey: ['issues', params],
    queryFn: () => apiClient.get('/issues', { searchParams }).json<any>(),
    placeholderData: (prev: any) => prev,
  })
}

export default function IssuesPage() {
  const [severity, setSeverity] = useState<string | null>(null)
  const [category, setCategory] = useState<string | null>(null)
  const [fixStatus, setFixStatus] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(1)

  const { data, isLoading } = useIssues({
    severity: severity ?? undefined,
    category: category ?? undefined,
    fix_status: fixStatus ?? undefined,
    page,
  })

  const issues: any[] = data?.issues ?? []
  const total: number = data?.total ?? 0

  const filtered = search
    ? issues.filter(i =>
        (ISSUE_TYPE_LABELS[i.type] || i.type).toLowerCase().includes(search.toLowerCase()) ||
        (i.current_value || '').toLowerCase().includes(search.toLowerCase())
      )
    : issues

  const activeFilters = [severity, category, fixStatus].filter(Boolean).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Issues</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            SEO issues found across your sites, sorted by impact
            {total > 0 && <span className="ml-1 text-foreground font-semibold">({total} total)</span>}
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

      {/* Filters */}
      {showFilters && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
          className="bg-card border border-border rounded-xl p-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search issues…"
                className="w-full h-9 bg-background border border-border rounded-lg pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
            <div className="relative">
              <select value={severity ?? ''} onChange={(e) => { setSeverity(e.target.value || null); setPage(1) }}
                className="w-full h-9 bg-background border border-border rounded-lg px-3 pr-8 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/30">
                <option value="">All severities</option>
                {Object.entries(SEVERITY_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            </div>
            <div className="relative">
              <select value={category ?? ''} onChange={(e) => { setCategory(e.target.value || null); setPage(1) }}
                className="w-full h-9 bg-background border border-border rounded-lg px-3 pr-8 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/30">
                <option value="">All categories</option>
                {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            </div>
            <div className="relative">
              <select value={fixStatus ?? ''} onChange={(e) => { setFixStatus(e.target.value || null); setPage(1) }}
                className="w-full h-9 bg-background border border-border rounded-lg px-3 pr-8 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/30">
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="applied">Applied</option>
                <option value="rolled_back">Rolled back</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            </div>
          </div>
          {(activeFilters > 0 || search) && (
            <button onClick={() => { setSeverity(null); setCategory(null); setFixStatus(null); setSearch(''); setPage(1) }}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
              <X className="h-3 w-3" /> Clear all filters
            </button>
          )}
        </motion.div>
      )}

      {/* Summary badges */}
      {issues.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(SEVERITY_CONFIG).map(([k, v]) => {
            const count = issues.filter(i => i.severity === k).length
            if (!count) return null
            return (
              <button key={k} onClick={() => { setSeverity(severity === k ? null : k); setPage(1) }}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                  severity === k ? v.className : 'bg-muted border-border text-muted-foreground hover:text-foreground'
                }`}>
                <v.icon className="h-3 w-3" /> {v.label}: {count}
              </button>
            )
          })}
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 bg-card border border-dashed border-border rounded-xl text-center">
          <div className="w-14 h-14 rounded-2xl bg-green-500/10 flex items-center justify-center mb-4">
            <CheckCircle2 className="h-7 w-7 text-green-500" />
          </div>
          <h3 className="text-base font-semibold text-foreground mb-1">
            {issues.length === 0 ? 'No issues detected yet' : 'No matching issues'}
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            {issues.length === 0
              ? 'Add a site and run your first crawl to start detecting SEO issues automatically.'
              : 'Try adjusting your filters to see more results.'}
          </p>
        </motion.div>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="grid grid-cols-[1fr,auto,auto,auto,auto] gap-4 px-5 py-3 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <span>Issue</span>
            <span className="hidden md:block">Category</span>
            <span>Severity</span>
            <span className="hidden sm:block">Fix type</span>
            <span>Status</span>
          </div>
          <div className="divide-y divide-border">
            {filtered.map((issue, i) => {
              const sev = SEVERITY_CONFIG[issue.severity] ?? SEVERITY_CONFIG.info
              const SevIcon = sev.icon
              const title = ISSUE_TYPE_LABELS[issue.type] || issue.type.replace(/_/g, ' ')
              const statusColor: Record<string, string> = {
                pending: 'text-amber-500 bg-amber-500/10',
                applied: 'text-green-500 bg-green-500/10',
                rolled_back: 'text-slate-500 bg-slate-500/10',
              }
              return (
                <motion.div key={issue.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.02 }}
                  className="grid grid-cols-[1fr,auto,auto,auto,auto] gap-4 items-center px-5 py-3.5 hover:bg-muted/50 transition-colors">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <SevIcon className={`h-4 w-4 flex-shrink-0 ${sev.className.split(' ')[1]}`} />
                      <p className="text-sm font-medium text-foreground truncate capitalize">{title}</p>
                    </div>
                    {issue.current_value && (
                      <p className="text-xs text-muted-foreground mt-0.5 ml-6 truncate font-mono max-w-sm">
                        {issue.current_value}
                      </p>
                    )}
                  </div>
                  <span className="text-xs font-medium text-muted-foreground whitespace-nowrap hidden md:block">
                    {CATEGORY_LABELS[issue.category] ?? issue.category}
                  </span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border whitespace-nowrap ${sev.className}`}>
                    {sev.label}
                  </span>
                  <span className="hidden sm:block text-xs text-muted-foreground capitalize whitespace-nowrap">
                    {issue.fix_type === 'auto' ? '⚡ Auto' : '👤 Manual'}
                  </span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize ${statusColor[issue.fix_status] ?? 'text-muted-foreground bg-muted'}`}>
                    {issue.fix_status}
                  </span>
                </motion.div>
              )
            })}
          </div>
          {/* Pagination */}
          {total > 50 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-border">
              <span className="text-xs text-muted-foreground">
                Showing {(page - 1) * 50 + 1}–{Math.min(page * 50, total)} of {total}
              </span>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                  className="h-7 px-3 rounded-md border border-border text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-40 transition-colors">
                  Previous
                </button>
                <button onClick={() => setPage(p => p + 1)} disabled={page * 50 >= total}
                  className="h-7 px-3 rounded-md border border-border text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-40 transition-colors">
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
