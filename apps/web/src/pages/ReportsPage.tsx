import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Calendar, Download, FileText, Globe, Mail, Plus, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { reportsApi } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'

const REPORT_TYPES = [
  { value: 'weekly', label: 'Weekly digest' },
  { value: 'monthly', label: 'Monthly summary' },
  { value: 'on_demand', label: 'On demand' },
]

export default function ReportsPage() {
  const queryClient = useQueryClient()
  const { data: sitesData } = useSites()
  const { data: reportsData } = useQuery({
    queryKey: ['reports'],
    queryFn: () => reportsApi.list(),
  })

  const createReport = useMutation({
    mutationFn: (data: any) => reportsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      toast.success('Report schedule created')
    },
  })

  const generateReport = useMutation({
    mutationFn: (siteId: string) => reportsApi.generate({ site_id: siteId }),
    onSuccess: () => toast.success('Report payload generated'),
  })

  const sites = sitesData?.sites ?? []
  const reports = reportsData?.reports ?? []
  const [showCreate, setShowCreate] = useState(false)
  const [selectedSiteId, setSelectedSiteId] = useState('')
  const [form, setForm] = useState({
    name: '',
    site_id: '',
    type: 'weekly',
    format: 'pdf',
    recipients: '',
  })

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    await createReport.mutateAsync({
      name: form.name,
      site_id: form.site_id || undefined,
      type: form.type,
      format: form.format,
      recipients: form.recipients.split(',').map((value) => value.trim()).filter(Boolean),
    })
    setShowCreate(false)
    setForm({ name: '', site_id: '', type: 'weekly', format: 'pdf', recipients: '' })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Scheduled digests and on-demand crawl summaries.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" /> Schedule Report
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: FileText, title: 'Scheduled Reports', desc: `${reports.length} schedules configured`, color: 'text-red-500 bg-red-500/10' },
          { icon: Mail, title: 'Recipients', desc: 'Email digests and PDF routing', color: 'text-blue-500 bg-blue-500/10' },
          { icon: Calendar, title: 'On-Demand Export', desc: 'Generate a crawl summary payload instantly', color: 'text-green-500 bg-green-500/10' },
        ].map((card) => (
          <div key={card.title} className="bg-card border border-border rounded-xl p-5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-4 ${card.color}`}>
              <card.icon className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-2">{card.title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{card.desc}</p>
          </div>
        ))}
      </div>

      {sites.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Generate On-Demand Report</h2>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative flex-1 min-w-[240px] max-w-sm">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select
                value={selectedSiteId}
                onChange={(event) => setSelectedSiteId(event.target.value)}
                className="w-full h-9 pl-9 pr-3 rounded-lg border border-border bg-background text-sm text-foreground appearance-none focus:outline-none"
              >
                <option value="">Select a site</option>
                {sites.map((site: any) => <option key={site.id} value={site.id}>{site.name}</option>)}
              </select>
            </div>
            <button
              onClick={() => selectedSiteId && generateReport.mutate(selectedSiteId)}
              disabled={!selectedSiteId || generateReport.isPending}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              {generateReport.isPending ? 'Generating…' : 'Generate'}
            </button>
          </div>
          {generateReport.data?.summary && (
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm">
              <p className="font-medium text-foreground">Latest crawl summary</p>
              <p className="text-xs text-muted-foreground mt-1">
                Score {generateReport.data.summary.seo_score ?? '—'} · {generateReport.data.summary.pages_crawled} pages · {generateReport.data.summary.issues_found} issues
              </p>
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
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recipients</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {reports.map((report: any) => (
                <tr key={report.id}>
                  <td className="px-4 py-3 font-medium text-foreground">{report.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{report.site_name ?? 'All sites'}</td>
                  <td className="px-4 py-3 text-muted-foreground capitalize">{report.type}</td>
                  <td className="px-4 py-3 text-muted-foreground">{(report.recipients ?? []).join(', ') || '—'}</td>
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
                <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Report Name *</label>
                  <input
                    value={form.name}
                    onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                    placeholder="Weekly SEO Digest"
                    required
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Site</label>
                  <select
                    value={form.site_id}
                    onChange={(event) => setForm((current) => ({ ...current, site_id: event.target.value }))}
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none"
                  >
                    <option value="">All sites</option>
                    {sites.map((site: any) => <option key={site.id} value={site.id}>{site.name}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Frequency</label>
                    <select
                      value={form.type}
                      onChange={(event) => setForm((current) => ({ ...current, type: event.target.value }))}
                      className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none"
                    >
                      {REPORT_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Format</label>
                    <select
                      value={form.format}
                      onChange={(event) => setForm((current) => ({ ...current, format: event.target.value }))}
                      className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none"
                    >
                      <option value="pdf">PDF</option>
                      <option value="email">Email</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Recipients</label>
                  <input
                    value={form.recipients}
                    onChange={(event) => setForm((current) => ({ ...current, recipients: event.target.value }))}
                    placeholder="you@company.com, team@company.com"
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setShowCreate(false)} className="flex-1 h-9 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={createReport.isPending} className="flex-1 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {createReport.isPending ? 'Creating…' : 'Create'}
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
