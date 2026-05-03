import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Swords, Globe, Trash2, X, ChevronDown, ExternalLink, BarChart2, Info, Play } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'
import { toast } from 'sonner'

function useCompetitors(siteId: string) {
  return useQuery({
    queryKey: ['competitors', siteId],
    queryFn: () => apiClient.get('competitors', { searchParams: { site_id: siteId } }).json<any>(),
    enabled: !!siteId,
  })
}

function useAddCompetitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => apiClient.post('competitors', { json: data }).json<any>(),
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
      apiClient.delete(`competitors/${id}`),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['competitors', vars.site_id] })
      toast.success('Competitor removed')
    },
    onError: () => toast.error('Failed to remove competitor'),
  })
}

function useAnalyzeCompetitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string; site_id: string }) =>
      apiClient.post(`competitors/${id}/analyze`).json<any>(),
    onSuccess: (result, vars) => {
      qc.invalidateQueries({ queryKey: ['competitors', vars.site_id] })
      toast.success(result.message || 'Competitor analyzed')
    },
    onError: () => toast.error('Failed to analyze competitor'),
  })
}

function useCompareCompetitorPages() {
  return useMutation({
    mutationFn: ({ id, site_page_url, competitor_page_url }: { id: string; site_page_url: string; competitor_page_url: string }) =>
      apiClient.post(`competitors/${id}/compare-pages`, { json: { site_page_url, competitor_page_url } }).json<any>(),
    onSuccess: () => toast.success('Page comparison completed'),
    onError: () => toast.error('Failed to compare pages'),
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
  const analyze = useAnalyzeCompetitor()
  const comparePages = useCompareCompetitorPages()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ domain: '', name: '' })
  const [compareForm, setCompareForm] = useState({ competitor_id: '', site_page_url: '', competitor_page_url: '' })
  const pagesQuery = useQuery({
    queryKey: ['competitor-site-pages', siteId],
    queryFn: () => apiClient.get(`sites/${siteId}/pages`).json<any>(),
    enabled: !!siteId,
  })

  const competitors = data?.competitors ?? []
  const pages = pagesQuery.data?.pages ?? []
  const pageComparison = comparePages.data as any

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
          <p className="text-sm text-muted-foreground mt-0.5">Track competitors and run lightweight homepage comparisons with the crawler.</p>
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

      {(data?.readiness || data?.provider_gap) && (
        <div className="space-y-2">
          {data.readiness && (
            <div className={`rounded-xl border p-4 flex items-start gap-3 ${
              data.readiness.state === 'working' ? 'border-green-500/20 bg-green-500/10' : 'border-amber-500/20 bg-amber-500/10'
            }`}>
              <Info className={`h-4 w-4 mt-0.5 ${data.readiness.state === 'working' ? 'text-green-400' : 'text-amber-500'}`} />
              <p className={`text-xs leading-relaxed ${data.readiness.state === 'working' ? 'text-green-100' : 'text-amber-100'}`}>
                Current status: <span className="font-semibold">{data.readiness.label}</span>. {data.readiness.description}
              </p>
            </div>
          )}
          {data.provider_gap && data.provider_gap.state !== 'working' && (
            <div className="rounded-xl border border-slate-500/20 bg-slate-500/10 p-4 flex items-start gap-3">
              <Info className="h-4 w-4 text-slate-400 mt-0.5" />
              <p className="text-xs text-slate-300 leading-relaxed">
                <span className="font-semibold">{data.provider_gap.label}</span>: {data.provider_gap.description}
              </p>
            </div>
          )}
        </div>
      )}
      {!data && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 flex items-start gap-3">
          <Info className="h-4 w-4 text-amber-500 mt-0.5" />
          <p className="text-xs text-amber-100 leading-relaxed">
            Current status: <span className="font-semibold">Working for lightweight crawl comparison</span>, but keyword counts and backlinks still <span className="font-semibold">need a provider</span>.
          </p>
        </div>
      )}

      <div className="bg-card border border-border rounded-xl p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Page-vs-page gap comparison</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Compare one crawled page against a competitor page for title, meta, schema, content depth, and internal-link gaps.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-3">
          <select value={compareForm.competitor_id} onChange={e => setCompareForm(f => ({ ...f, competitor_id: e.target.value }))}
            className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
            <option value="">Choose competitor</option>
            {competitors.map((c: any) => <option key={c.id} value={c.id}>{c.name || c.domain}</option>)}
          </select>
          <select value={compareForm.site_page_url} onChange={e => setCompareForm(f => ({ ...f, site_page_url: e.target.value }))}
            className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none">
            <option value="">Choose your crawled page</option>
            {pages.map((page: any) => <option key={page.id} value={page.url}>{page.url}</option>)}
          </select>
          <input value={compareForm.competitor_page_url} onChange={e => setCompareForm(f => ({ ...f, competitor_page_url: e.target.value }))}
            placeholder="https://competitor.com/page"
            className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none" />
        </div>
        <button onClick={() => comparePages.mutate({
          id: compareForm.competitor_id,
          site_page_url: compareForm.site_page_url,
          competitor_page_url: compareForm.competitor_page_url,
        })} disabled={!compareForm.competitor_id || !compareForm.site_page_url || !compareForm.competitor_page_url || comparePages.isPending}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50">
          <BarChart2 className="h-4 w-4" />
          {comparePages.isPending ? 'Comparing...' : 'Compare Pages'}
        </button>
        {pageComparison && (
          <div className="rounded-lg border border-border bg-background p-4">
            <div className="grid grid-cols-2 gap-3 text-sm mb-3">
              <div><span className="text-muted-foreground">Your score</span><p className="text-xl font-bold text-foreground">{pageComparison.site_score ?? '-'}</p></div>
              <div><span className="text-muted-foreground">Competitor score</span><p className="text-xl font-bold text-foreground">{pageComparison.competitor_score ?? '-'}</p></div>
            </div>
            {(pageComparison.gaps ?? []).length === 0 ? (
              <p className="text-xs text-muted-foreground">No obvious page gaps detected.</p>
            ) : (
              <div className="space-y-2">
                {pageComparison.gaps.map((gap: any) => (
                  <div key={gap.type} className="rounded-md bg-muted/40 px-3 py-2">
                    <p className="text-xs font-semibold text-foreground">{gap.type.replaceAll('_', ' ')}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{gap.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
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
                <div className="flex items-center gap-1">
                  <button onClick={() => analyze.mutate({ id: c.id, site_id: siteId })} disabled={analyze.isPending}
                    className="p-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors disabled:opacity-50">
                    <Play className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={() => remove.mutate({ id: c.id, site_id: siteId })}
                    className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
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
              <p className="text-[10px] text-muted-foreground/60 mt-3 pt-3 border-t border-border flex items-center justify-between gap-2">
                {c.last_analyzed_at && (
                  <span>Last analyzed: {new Date(c.last_analyzed_at).toLocaleDateString()}</span>
                )}
                {c.created_at && (
                  <span className="text-muted-foreground/40">Added {new Date(c.created_at).toLocaleDateString()}</span>
                )}
              </p>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
