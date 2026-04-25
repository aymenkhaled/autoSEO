import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Calendar, Download, ExternalLink, FileText, Globe, Mail, Plus, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { reportsApi, systemApi } from '@/lib/api-client'
import { readinessMeta } from '@/lib/readiness'
import { useSites } from '@/hooks/use-data'

const REPORT_TYPES = [
  { value: 'weekly', label: 'Weekly digest' },
  { value: 'monthly', label: 'Monthly summary' },
  { value: 'on_demand', label: 'On demand' },
]

export default function ReportsPage() {
  const queryClient = useQueryClient()
  const { data: sitesData } = useSites()
  const { data: reportsData } = useQuery({ queryKey: ['reports'], queryFn: () => reportsApi.list() })
  const { data: readiness } = useQuery({ queryKey: ['system-readiness-reports'], queryFn: () => systemApi.readiness() })
  const createReport = useMutation({
    mutationFn: (data: any) => reportsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      toast.success('Report schedule saved')
    },
  })
  const generateReport = useMutation({
    mutationFn: (siteId: string) => reportsApi.generate({ site_id: siteId }),
    onSuccess: () => toast.success('Report generated with root causes'),
  })
  const digestPreview = useMutation({
    mutationFn: (siteId?: string) => reportsApi.digestPreview(siteId || undefined),
    onSuccess: () => toast.success('Digest preview generated'),
  })
  const shareLink = useMutation({
    mutationFn: (siteId: string) => reportsApi.shareLink({ site_id: siteId, title: 'SEO action report' }),
    onSuccess: () => toast.success('Read-only report link created'),
  })

  const sites = sitesData?.sites ?? []
  const reports = reportsData?.reports ?? []
  const [showCreate, setShowCreate] = useState(false)
  const [selectedSiteId, setSelectedSiteId] = useState('')
  const [form, setForm] = useState({ name: '', site_id: '', type: 'weekly', format: 'pdf', recipients: '' })
  const report = generateReport.data
  const digest = digestPreview.data as any
  const shared = shareLink.data as any
  const reportReadiness = readiness?.features?.reports

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    await createReport.mutateAsync({
      name: form.name,
      site_id: form.site_id || undefined,
      type: form.type,
      format: form.format,
      recipients: form.recipients.split(',').map(value => value.trim()).filter(Boolean),
    })
    setShowCreate(false)
    setForm({ name: '', site_id: '', type: 'weekly', format: 'pdf', recipients: '' })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Root-cause SEO summaries with affected pages and next actions.</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
          <Plus className="h-4 w-4" /> Schedule Report
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: FileText, title: 'Scheduled Reports', desc: `${reports.length} schedules configured`, color: 'text-red-500 bg-red-500/10' },
          { icon: Mail, title: 'Recipients', desc: 'Email digests and export routing are stored for later delivery jobs', color: 'text-blue-500 bg-blue-500/10' },
          { icon: Calendar, title: 'On-Demand Report', desc: 'Generates structured report data now; PDF rendering can layer on top', color: 'text-green-500 bg-green-500/10' },
        ].map(card => (
          <div key={card.title} className="bg-card border border-border rounded-xl p-5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-4 ${card.color}`}>
              <card.icon className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-2">{card.title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{card.desc}</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-orange-500/20 bg-orange-500/10 p-4">
        <p className="text-xs text-orange-100 leading-relaxed">
          Scheduled reports are currently <span className="font-semibold">{reportReadiness?.label?.toLowerCase() || 'saved only'}</span>. {reportReadiness?.description || 'The schedule, recipients, and format are stored, but recurring delivery and PDF/email workers are not wired yet.'}
        </p>
      </div>

      {sites.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Generate On-Demand Report</h2>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative flex-1 min-w-[240px] max-w-sm">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select value={selectedSiteId} onChange={(event) => setSelectedSiteId(event.target.value)}
                className="w-full h-9 pl-9 pr-3 rounded-lg border border-border bg-background text-sm text-foreground appearance-none focus:outline-none">
                <option value="">Select a site</option>
                {sites.map((site: any) => <option key={site.id} value={site.id}>{site.name}</option>)}
              </select>
            </div>
            <button onClick={() => selectedSiteId && generateReport.mutate(selectedSiteId)}
              disabled={!selectedSiteId || generateReport.isPending}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50">
              <Download className="h-4 w-4" />
              {generateReport.isPending ? 'Generating...' : 'Generate'}
            </button>
            <button onClick={() => digestPreview.mutate(selectedSiteId || undefined)}
              disabled={digestPreview.isPending}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50">
              <Mail className="h-4 w-4" />
              {digestPreview.isPending ? 'Building...' : 'Digest Preview'}
            </button>
            <button onClick={() => selectedSiteId && shareLink.mutate(selectedSiteId)}
              disabled={!selectedSiteId || shareLink.isPending}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50">
              <ExternalLink className="h-4 w-4" />
              {shareLink.isPending ? 'Creating...' : 'Share Link'}
            </button>
          </div>

          {shared?.share_url && (
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="text-xs font-semibold text-foreground">Read-only share link</p>
              <code className="block text-[11px] text-muted-foreground mt-1 break-all">{shared.share_url}</code>
            </div>
          )}

          {digest?.sites && (
            <div className="rounded-xl border border-border bg-background p-4">
              <p className="text-sm font-semibold text-foreground">Weekly digest preview</p>
              <p className="text-xs text-muted-foreground mt-1">{digest.message}</p>
              <div className="grid lg:grid-cols-2 gap-3 mt-3">
                {digest.sites.map((item: any) => (
                  <div key={item.site_id} className="rounded-lg border border-border bg-card p-3">
                    <p className="text-xs font-semibold text-foreground">{item.site_name}</p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      Score {item.seo_score ?? '-'} · {item.pages_crawled ?? 0} pages · {item.issues_found ?? 0} raw issues
                    </p>
                    {item.next_action && (
                      <p className="text-[11px] text-cyan-200 mt-2">Next: {item.next_action.title}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {report?.summary && (
            <div className="space-y-4">
              <div className="rounded-xl border border-border bg-muted/30 p-4">
                <p className="font-medium text-foreground">Latest crawl summary</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                  <div><p className="text-2xl font-bold text-foreground">{report.summary.seo_score ?? '-'}</p><p className="text-xs text-muted-foreground">Score</p></div>
                  <div><p className="text-2xl font-bold text-foreground">{report.summary.pages_crawled ?? 0}</p><p className="text-xs text-muted-foreground">Pages</p></div>
                  <div><p className="text-2xl font-bold text-foreground">{report.summary.issues_found ?? 0}</p><p className="text-xs text-muted-foreground">Raw issues</p></div>
                  <div><p className="text-2xl font-bold text-foreground">{report.root_causes?.length ?? 0}</p><p className="text-xs text-muted-foreground">Root causes</p></div>
                </div>
                {report.changed_since_last_crawl && (
                  <p className="text-xs text-muted-foreground mt-3">
                    Since previous crawl: score {report.changed_since_last_crawl.score_delta >= 0 ? '+' : ''}{report.changed_since_last_crawl.score_delta}, issues {report.changed_since_last_crawl.issues_delta >= 0 ? '+' : ''}{report.changed_since_last_crawl.issues_delta}, pages {report.changed_since_last_crawl.pages_delta >= 0 ? '+' : ''}{report.changed_since_last_crawl.pages_delta}.
                  </p>
                )}
                {report.summary.coverage_reason && (
                  <div className="mt-3 rounded-lg border border-border bg-background p-3">
                    <p className="text-xs font-semibold text-foreground">Coverage note</p>
                    <p className="text-xs text-muted-foreground mt-1">{report.summary.coverage_reason}</p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      Discovered {report.summary.urls_discovered ?? 0}, scanned {report.summary.pages_crawled ?? 0}, skipped {report.summary.urls_skipped ?? 0}, limit {report.summary.crawl_limit ?? '-'}.
                    </p>
                  </div>
                )}
              </div>

              <div className="grid lg:grid-cols-2 gap-4">
                <div className="rounded-xl border border-border bg-background p-4">
                  <p className="text-sm font-semibold text-foreground">Search Console impact</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {report.search_console?.connected ? `Property: ${report.search_console.property_url}` : 'Search Console is not connected for this site yet.'}
                  </p>
                  <div className="grid grid-cols-2 gap-3 mt-3">
                    <div><p className="text-xl font-bold text-foreground">{Math.round(report.search_console?.totals?.impressions ?? 0).toLocaleString()}</p><p className="text-xs text-muted-foreground">Impressions</p></div>
                    <div><p className="text-xl font-bold text-foreground">{Math.round(report.search_console?.totals?.clicks ?? 0).toLocaleString()}</p><p className="text-xs text-muted-foreground">Clicks</p></div>
                    <div><p className="text-xl font-bold text-foreground">{((report.search_console?.totals?.ctr ?? 0) * 100).toFixed(1)}%</p><p className="text-xs text-muted-foreground">CTR</p></div>
                    <div><p className="text-xl font-bold text-foreground">{(report.search_console?.totals?.position ?? 0).toFixed(1)}</p><p className="text-xs text-muted-foreground">Avg position</p></div>
                  </div>
                </div>
                <div className="rounded-xl border border-border bg-background p-4">
                  <p className="text-sm font-semibold text-foreground">GitHub proof status</p>
                  <p className="text-xs text-muted-foreground mt-1">{report.github_fix_status?.message}</p>
                  <p className="text-3xl font-bold text-foreground mt-4">{report.github_fix_status?.open_pr_issue_count ?? 0}</p>
                  <p className="text-xs text-muted-foreground">PR-created issue rows awaiting deploy + recrawl proof</p>
                </div>
              </div>

              <div className="grid lg:grid-cols-3 gap-4">
                <div className="rounded-xl border border-border bg-background p-4">
                  <p className="text-sm font-semibold text-foreground">GA4 business impact</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {report.analytics?.connected ? `Property: ${report.analytics.property_id}` : 'GA4 is not connected yet.'}
                  </p>
                  <p className="text-2xl font-bold text-foreground mt-3">${Number(report.analytics?.totals?.total_revenue ?? 0).toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">{Math.round(report.analytics?.totals?.sessions ?? 0).toLocaleString()} sessions · {report.analytics?.totals?.key_events ?? 0} key events</p>
                </div>
                <div className="rounded-xl border border-border bg-background p-4">
                  <p className="text-sm font-semibold text-foreground">PageSpeed</p>
                  <p className="text-2xl font-bold text-foreground mt-3">{report.pagespeed?.summary?.avg_performance_score ?? '-'}</p>
                  <p className="text-xs text-muted-foreground">Avg performance · LCP {report.pagespeed?.summary?.avg_lcp_ms ?? '-'}ms</p>
                </div>
                <div className="rounded-xl border border-border bg-background p-4">
                  <p className="text-sm font-semibold text-foreground">IndexNow</p>
                  <p className="text-2xl font-bold text-foreground mt-3">{report.indexnow?.verified ? 'Verified' : 'Setup needed'}</p>
                  <p className="text-xs text-muted-foreground truncate">{report.indexnow?.key_location || 'Upload key file to enable post-fix URL submission.'}</p>
                </div>
              </div>

              {(report.top_opportunities ?? []).length > 0 && (
                <div className="rounded-xl border border-border bg-background p-4">
                  <p className="text-sm font-semibold text-foreground">Top opportunities</p>
                  <div className="grid lg:grid-cols-2 gap-3 mt-3">
                    {report.top_opportunities.slice(0, 6).map((item: any) => (
                      <div key={`${item.source}-${item.type}-${item.affected_url || item.issue_type}`} className="rounded-lg border border-border bg-card p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold text-foreground">{item.title}</p>
                            <p className="text-[11px] text-muted-foreground mt-1">{item.description}</p>
                          </div>
                          <span className="text-[11px] px-2 py-0.5 rounded-full border border-cyan-500/20 bg-cyan-500/10 text-cyan-300">{item.priority_score}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {report.note && (
                <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-3 text-xs text-blue-100">
                  {report.note}
                </div>
              )}

              <div className="grid lg:grid-cols-2 gap-4">
                {(report.root_causes ?? []).slice(0, 6).map((cause: any) => (
                  <div key={`${cause.type}-${cause.category}`} className="rounded-xl border border-border bg-background p-4 space-y-3">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-foreground">{cause.title}</p>
                        <p className="text-xs text-muted-foreground mt-1">{cause.summary}</p>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground"><span className="text-foreground font-medium">Fix:</span> {cause.recommended_fix}</p>
                    <div className="text-[11px] text-muted-foreground">
                      {cause.affected_count} affected - {cause.severity} - impact {cause.impact}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">Scheduled Reports</h2>
        </div>
        {reports.length === 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground">No scheduled reports yet.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Site</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Type</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Delivery</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recipients</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {reports.map((item: any) => (
                <tr key={item.id}>
                  <td className="px-4 py-3 font-medium text-foreground">{item.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{item.site_name ?? 'All sites'}</td>
                  <td className="px-4 py-3 text-muted-foreground capitalize">{item.type}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold ${readinessMeta(item.delivery_state).className}`}>
                      {item.delivery_state_label ?? readinessMeta(item.delivery_state).label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{(item.recipients ?? []).join(', ') || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <AnimatePresence>
        {showCreate && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }} className="bg-card border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-foreground">Schedule a Report</h2>
                <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground transition-colors"><X className="h-5 w-5" /></button>
              </div>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Report Name *</label>
                  <input value={form.name} onChange={(event) => setForm(current => ({ ...current, name: event.target.value }))}
                    placeholder="Weekly SEO Digest" required className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Site</label>
                  <select value={form.site_id} onChange={(event) => setForm(current => ({ ...current, site_id: event.target.value }))}
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
                    <option value="">All sites</option>
                    {sites.map((site: any) => <option key={site.id} value={site.id}>{site.name}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Frequency</label>
                    <select value={form.type} onChange={(event) => setForm(current => ({ ...current, type: event.target.value }))}
                      className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
                      {REPORT_TYPES.map(type => <option key={type.value} value={type.value}>{type.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Format</label>
                    <select value={form.format} onChange={(event) => setForm(current => ({ ...current, format: event.target.value }))}
                      className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
                      <option value="pdf">PDF</option>
                      <option value="email">Email</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Recipients</label>
                  <input value={form.recipients} onChange={(event) => setForm(current => ({ ...current, recipients: event.target.value }))}
                    placeholder="you@company.com, team@company.com" className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setShowCreate(false)} className="flex-1 h-9 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">Cancel</button>
                  <button type="submit" disabled={createReport.isPending} className="flex-1 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {createReport.isPending ? 'Creating...' : 'Create'}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
