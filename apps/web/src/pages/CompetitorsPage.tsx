import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Swords, Globe, Trash2, X, ChevronDown, ExternalLink, BarChart2 } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'
import { toast } from 'sonner'

function useCompetitors(siteId: string) {
  return useQuery({
    queryKey: ['competitors', siteId],
    queryFn: () => apiClient.get('/competitors', { searchParams: { site_id: siteId } }).json<any>(),
    enabled: !!siteId,
  })
}

function useAddCompetitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => apiClient.post('/competitors', { json: data }).json<any>(),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['competitors', vars.site_id] })
      toast.success('Competitor added')
    },
    onError: () => toast.error('Failed to add competitor'),
  })
}

function useRemoveCompetitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string; site_id: string }) =>
      apiClient.delete(`/competitors/${id}`).json<any>(),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['competitors', vars.site_id] })
      toast.success('Competitor removed')
    },
    onError: () => toast.error('Failed to remove competitor'),
  })
}

function ScoreBar({ score }: { score?: number }) {
  if (!score) return <span className="text-muted-foreground text-xs">Not analyzed</span>
  const color = score >= 70 ? 'bg-green-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-medium text-foreground w-6 text-right">{score}</span>
    </div>
  )
}

export default function CompetitorsPage() {
  const { data: sitesData } = useSites()
  const sites = sitesData?.sites ?? []
  const [selectedSite, setSelectedSite] = useState<string>('')
  const siteId = selectedSite || sites[0]?.id || ''

  const { data, isLoading } = useCompetitors(siteId)
  const add = useAddCompetitor()
  const remove = useRemoveCompetitor()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ domain: '', name: '' })

  const competitors = data?.competitors ?? []

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!siteId || !form.domain.trim()) return
    await add.mutateAsync({ ...form, site_id: siteId })
    setForm({ domain: '', name: '' })
    setShowAdd(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Competitors</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Monitor competitor SEO performance and benchmark your sites</p>
        </div>
        <div className="flex items-center gap-3">
          {sites.length > 0 && (
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select
                value={selectedSite}
                onChange={e => setSelectedSite(e.target.value)}
                className="h-9 pl-9 pr-8 rounded-lg border border-border bg-background text-sm text-foreground appearance-none cursor-pointer focus:outline-none">
                {sites.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            </div>
          )}
          <button onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
            <Plus className="h-4 w-4" /> Add Competitor
          </button>
        </div>
      </div>

      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }}
              className="bg-card border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-foreground">Add Competitor</h2>
                <button onClick={() => setShowAdd(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleAdd} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Domain *</label>
                  <input value={form.domain} onChange={e => setForm(f => ({ ...f, domain: e.target.value }))}
                    placeholder="competitor.com" required
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Display Name</label>
                  <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Competitor Inc."
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setShowAdd(false)}
                    className="flex-1 h-9 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={add.isPending}
                    className="flex-1 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {add.isPending ? 'Adding…' : 'Add Competitor'}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-5 animate-pulse">
              <div className="h-4 bg-muted rounded w-40 mb-3" />
              <div className="h-3 bg-muted rounded w-24 mb-4" />
              <div className="h-2 bg-muted rounded w-full" />
            </div>
          ))}
        </div>
      ) : competitors.length === 0 ? (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 bg-card border border-dashed border-border rounded-xl text-center">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
            <Swords className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-base font-semibold text-foreground mb-1">No competitors tracked</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-sm">
            Add your competitors to benchmark your SEO performance and spot opportunities.
          </p>
          <button onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-2 h-9 px-5 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
            <Plus className="h-4 w-4" /> Add First Competitor
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {competitors.map((c: any, i: number) => (
            <motion.div key={c.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
              className="bg-card border border-border rounded-xl p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-foreground">{c.name || c.domain}</h3>
                  <a href={`https://${c.domain}`} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors mt-0.5">
                    {c.domain} <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <button onClick={() => remove.mutate({ id: c.id, site_id: siteId })}
                  className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-muted-foreground">SEO Score</span>
                  </div>
                  <ScoreBar score={c.seo_score} />
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Keywords</span>
                  <span className="font-medium text-foreground">{c.keywords_count ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Backlinks</span>
                  <span className="font-medium text-foreground">{c.backlinks_count?.toLocaleString() ?? '—'}</span>
                </div>
              </div>
              {c.last_analyzed_at && (
                <p className="text-[10px] text-muted-foreground/60 mt-3 pt-3 border-t border-border">
                  Last analyzed: {new Date(c.last_analyzed_at).toLocaleDateString()}
                </p>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
