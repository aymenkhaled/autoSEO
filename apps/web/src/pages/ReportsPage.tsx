import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, Plus, Download, X, Mail, Calendar, Globe, ChevronDown } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'
import { toast } from 'sonner'

function useScheduledReports() {
  return useQuery({
    queryKey: ['scheduled-reports'],
    queryFn: () => apiClient.get('/change-log').json<any>(),
  })
}

const REPORT_TYPES = [
  { value: 'weekly', label: 'Weekly digest' },
  { value: 'monthly', label: 'Monthly summary' },
  { value: 'on_demand', label: 'On demand' },
]

export default function ReportsPage() {
  const { data: sitesData } = useSites()
  const sites = sitesData?.sites ?? []
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    name: '',
    site_id: '',
    type: 'weekly',
    format: 'pdf',
    recipients: '',
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    toast.success('Scheduled report created')
    setShowCreate(false)
    setForm({ name: '', site_id: '', type: 'weekly', format: 'pdf', recipients: '' })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground mt-0.5">PDF reports, email digests, and scheduled audits</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
          <Plus className="h-4 w-4" /> Schedule Report
        </button>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            icon: FileText,
            title: 'PDF Reports',
            desc: 'Generate detailed SEO audit reports with score breakdowns, issue lists, and fix recommendations.',
            color: 'text-red-500 bg-red-500/10',
            action: 'Generate PDF',
          },
          {
            icon: Mail,
            title: 'Email Digests',
            desc: 'Receive weekly summaries of your site\'s SEO performance, new issues, and applied fixes.',
            color: 'text-blue-500 bg-blue-500/10',
            action: 'Configure Email',
          },
          {
            icon: Calendar,
            title: 'Scheduled Audits',
            desc: 'Set up automatic recurring crawls and receive reports on a daily, weekly, or monthly cadence.',
            color: 'text-green-500 bg-green-500/10',
            action: 'Set Schedule',
          },
        ].map((card, i) => {
          const Icon = card.icon
          return (
            <motion.div key={card.title} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
              className="bg-card border border-border rounded-xl p-5">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-4 ${card.color}`}>
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold text-foreground mb-2">{card.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">{card.desc}</p>
              <button onClick={() => setShowCreate(true)}
                className="h-8 px-3 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-muted transition-colors">
                {card.action}
              </button>
            </motion.div>
          )
        })}
      </div>

      {/* On-demand report */}
      {sites.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
          className="bg-card border border-border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Generate On-Demand Report</h2>
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select className="w-full h-9 pl-9 pr-8 rounded-lg border border-border bg-background text-sm text-foreground appearance-none focus:outline-none">
                {sites.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            </div>
            <button onClick={() => toast.info('PDF generation coming soon')}
              className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors">
              <Download className="h-4 w-4" /> Download PDF
            </button>
          </div>
        </motion.div>
      )}

      {/* Scheduled reports table — empty for now */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
        className="bg-card border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4">Scheduled Reports</h2>
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <Calendar className="h-10 w-10 text-muted-foreground/30 mb-3" />
          <p className="text-sm text-muted-foreground">No scheduled reports yet</p>
          <p className="text-xs text-muted-foreground/60 mt-1">Set up automatic reports to stay on top of your SEO</p>
        </div>
      </motion.div>

      {/* Create modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }}
              className="bg-card border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-foreground">Schedule a Report</h2>
                <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Report Name *</label>
                  <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Weekly SEO Digest" required
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Frequency</label>
                    <select value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
                      className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
                      {REPORT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Format</label>
                    <select value={form.format} onChange={e => setForm(f => ({ ...f, format: e.target.value }))}
                      className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
                      <option value="pdf">PDF</option>
                      <option value="email">Email only</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Recipients (comma separated)</label>
                  <input value={form.recipients} onChange={e => setForm(f => ({ ...f, recipients: e.target.value }))}
                    placeholder="you@company.com, team@company.com"
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setShowCreate(false)}
                    className="flex-1 h-9 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">
                    Cancel
                  </button>
                  <button type="submit"
                    className="flex-1 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
                    Create Schedule
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
