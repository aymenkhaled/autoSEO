import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Target, TrendingUp, TrendingDown, Minus, Globe, Trash2, X, ChevronDown } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'
import { toast } from 'sonner'

function useKeywords(siteId: string) {
  return useQuery({
    queryKey: ['keywords', siteId],
    queryFn: () => apiClient.get('/keywords', { searchParams: { site_id: siteId } }).json<any>(),
    enabled: !!siteId,
  })
}

function useAddKeyword() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => apiClient.post('/keywords', { json: data }).json<any>(),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['keywords', vars.site_id] })
      toast.success('Keyword added for tracking')
    },
    onError: () => toast.error('Failed to add keyword'),
  })
}

function useDeleteKeyword() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string; site_id: string }) =>
      apiClient.delete(`/keywords/${id}`).json<any>(),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['keywords', vars.site_id] })
      toast.success('Keyword removed')
    },
    onError: () => toast.error('Failed to remove keyword'),
  })
}

const INTENT_LABELS: Record<string, { label: string; color: string }> = {
  informational: { label: 'Informational', color: 'text-blue-500 bg-blue-500/10 border-blue-500/20' },
  navigational: { label: 'Navigational', color: 'text-purple-500 bg-purple-500/10 border-purple-500/20' },
  transactional: { label: 'Transactional', color: 'text-green-500 bg-green-500/10 border-green-500/20' },
  commercial: { label: 'Commercial', color: 'text-amber-500 bg-amber-500/10 border-amber-500/20' },
}

function RankDelta({ current, prev }: { current?: number; prev?: number }) {
  if (!current || !prev) return <span className="text-muted-foreground">—</span>
  const delta = prev - current
  if (delta > 0) return <span className="flex items-center gap-0.5 text-green-500 text-xs font-semibold"><TrendingUp className="h-3 w-3" />+{delta}</span>
  if (delta < 0) return <span className="flex items-center gap-0.5 text-red-500 text-xs font-semibold"><TrendingDown className="h-3 w-3" />{delta}</span>
  return <span className="flex items-center gap-0.5 text-muted-foreground text-xs"><Minus className="h-3 w-3" />0</span>
}

export default function KeywordsPage() {
  const { data: sitesData } = useSites()
  const sites = sitesData?.sites ?? []
  const [selectedSite, setSelectedSite] = useState<string>('')
  const siteId = selectedSite || sites[0]?.id || ''

  const { data, isLoading } = useKeywords(siteId)
  const addKw = useAddKeyword()
  const deleteKw = useDeleteKeyword()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ keyword: '', target_url: '', intent: 'informational', priority: '1' })

  const keywords = data?.keywords ?? []

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!siteId || !form.keyword.trim()) return
    await addKw.mutateAsync({ ...form, site_id: siteId, priority: parseInt(form.priority) })
    setForm({ keyword: '', target_url: '', intent: 'informational', priority: '1' })
    setShowAdd(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Keywords</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Track keyword rankings and monitor position changes</p>
        </div>
        <div className="flex items-center gap-3">
          {sites.length > 0 && (
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select
                value={selectedSite}
                onChange={e => setSelectedSite(e.target.value)}
                className="h-9 pl-9 pr-8 rounded-lg border border-border bg-background text-sm text-foreground appearance-none cursor-pointer focus:outline-none"
              >
                {sites.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            </div>
          )}
          <button onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
            <Plus className="h-4 w-4" /> Add Keyword
          </button>
        </div>
      </div>

      {/* Add keyword modal */}
      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }}
              className="bg-card border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-foreground">Track New Keyword</h2>
                <button onClick={() => setShowAdd(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleAdd} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Keyword *</label>
                  <input value={form.keyword} onChange={e => setForm(f => ({ ...f, keyword: e.target.value }))}
                    placeholder="e.g. best SEO tools 2024"
                    required
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Target URL</label>
                  <input value={form.target_url} onChange={e => setForm(f => ({ ...f, target_url: e.target.value }))}
                    placeholder="https://example.com/page"
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Intent</label>
                    <select value={form.intent} onChange={e => setForm(f => ({ ...f, intent: e.target.value }))}
                      className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
                      {Object.keys(INTENT_LABELS).map(k => <option key={k} value={k}>{INTENT_LABELS[k].label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground block mb-1.5">Priority</label>
                    <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                      className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
                      <option value="1">Low</option>
                      <option value="2">Medium</option>
                      <option value="3">High</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setShowAdd(false)}
                    className="flex-1 h-9 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={addKw.isPending}
                    className="flex-1 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {addKw.isPending ? 'Adding…' : 'Add Keyword'}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Keyword</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Intent</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Position</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden sm:table-cell">Change</th>
              <th className="text-center px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Volume</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-muted rounded animate-pulse" style={{ width: j === 0 ? '60%' : '40%' }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : keywords.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
                      <Target className="h-6 w-6 text-primary" />
                    </div>
                    <p className="text-sm font-medium text-foreground mb-1">No keywords tracked yet</p>
                    <p className="text-xs text-muted-foreground mb-4">Add keywords to monitor your search rankings</p>
                    <button onClick={() => setShowAdd(true)}
                      className="inline-flex items-center gap-2 h-8 px-4 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors">
                      <Plus className="h-3.5 w-3.5" /> Add First Keyword
                    </button>
                  </div>
                </td>
              </tr>
            ) : keywords.map((kw: any, i: number) => {
              const intent = INTENT_LABELS[kw.intent] ?? INTENT_LABELS.informational
              const rank = kw.latest_ranking
              return (
                <motion.tr key={kw.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                  className="hover:bg-muted/50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium text-foreground">{kw.keyword}</p>
                    {kw.target_url && <p className="text-xs text-muted-foreground truncate max-w-[200px]">{kw.target_url}</p>}
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${intent.color}`}>{intent.label}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {rank?.position ? (
                      <span className="text-base font-bold text-foreground">#{rank.position}</span>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center hidden sm:table-cell">
                    <RankDelta current={rank?.position} prev={rank?.previous_position} />
                  </td>
                  <td className="px-4 py-3 text-center hidden lg:table-cell">
                    <span className="text-sm text-muted-foreground">
                      {rank?.search_volume ? rank.search_volume.toLocaleString() : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => deleteKw.mutate({ id: kw.id, site_id: siteId })}
                      className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </motion.tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
