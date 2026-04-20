import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, Globe, ExternalLink, MoreVertical, Trash2,
  Settings, Play, Loader2, X, ChevronDown,
} from 'lucide-react'
import { useSites, useCreateSite, useDeleteSite, useTriggerCrawl } from '@/hooks/use-data'
import { formatRelativeTime } from '@/lib/utils'

const CONNECTION_TYPES = [
  { value: 'crawler', label: 'Web Crawler (default)' },
  { value: 'wordpress', label: 'WordPress API' },
  { value: 'shopify', label: 'Shopify API' },
  { value: 'webflow', label: 'Webflow API' },
  { value: 'github', label: 'GitHub App' },
  { value: 'snippet', label: 'JS Snippet' },
]

const CONNECTION_LABELS: Record<string, string> = {
  crawler: 'Crawler', wordpress: 'WordPress', shopify: 'Shopify',
  webflow: 'Webflow', github: 'GitHub', snippet: 'JS Snippet',
}

function statusConfig(status: string) {
  const m: Record<string, { dot: string; label: string }> = {
    active:   { dot: 'bg-green-500',  label: 'Active' },
    crawling: { dot: 'bg-amber-500 animate-pulse', label: 'Crawling' },
    error:    { dot: 'bg-red-500',    label: 'Error' },
    inactive: { dot: 'bg-slate-400',  label: 'Inactive' },
  }
  return m[status] ?? m.inactive
}

export default function SitesPage() {
  const { data, isLoading } = useSites()
  const createSite = useCreateSite()
  const deleteSite = useDeleteSite()
  const triggerCrawl = useTriggerCrawl()
  const [showAdd, setShowAdd] = useState(false)
  const [newSite, setNewSite] = useState({ name: '', domain: '', connection_type: 'crawler' })
  const [menuOpen, setMenuOpen] = useState<string | null>(null)

  const sites = data?.sites ?? []

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createSite.mutateAsync(newSite)
      setShowAdd(false)
      setNewSite({ name: '', domain: '', connection_type: 'crawler' })
    } catch (err) {
      console.error('Failed to add site:', err)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Sites</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage and monitor your connected websites</p>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
          <Plus className="h-4 w-4" /> Add Site
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
      ) : sites.length === 0 ? (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 bg-card border border-dashed border-border rounded-xl text-center">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
            <Globe className="h-7 w-7 text-primary" />
          </div>
          <h3 className="text-base font-semibold text-foreground mb-1">No sites yet</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-sm">Add your first site to start monitoring its SEO health automatically.</p>
          <button onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-2 h-9 px-5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
            <Plus className="h-4 w-4" /> Add Your First Site
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {sites.map((site: any, i: number) => {
            const status = statusConfig(site.status ?? 'inactive')
            return (
              <motion.div key={site.id}
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="relative bg-card border border-border rounded-xl p-5 group hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Globe className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-foreground truncate">{site.name}</h3>
                      <a href={site.domain} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors truncate">
                        {site.domain?.replace('https://', '')}
                        <ExternalLink className="h-3 w-3 flex-shrink-0" />
                      </a>
                    </div>
                  </div>

                  <div className="relative flex-shrink-0">
                    <button onClick={() => setMenuOpen(menuOpen === site.id ? null : site.id)}
                      className="h-7 w-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted opacity-0 group-hover:opacity-100 transition-all">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                    <AnimatePresence>
                      {menuOpen === site.id && (
                        <motion.div initial={{ opacity: 0, scale: 0.95, y: -4 }} animate={{ opacity: 1, scale: 1, y: 0 }}
                          exit={{ opacity: 0, scale: 0.95, y: -4 }} transition={{ duration: 0.1 }}
                          className="absolute right-0 mt-1 w-40 rounded-xl bg-popover border border-border shadow-lg py-1 z-50">
                          <button onClick={() => { triggerCrawl.mutate(site.id); setMenuOpen(null) }}
                            className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors text-left">
                            <Play className="h-3.5 w-3.5 text-muted-foreground" /> Run Crawl
                          </button>
                          <button className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors text-left">
                            <Settings className="h-3.5 w-3.5 text-muted-foreground" /> Settings
                          </button>
                          <div className="h-px bg-border mx-2 my-1" />
                          <button onClick={() => { deleteSite.mutate(site.id); setMenuOpen(null) }}
                            className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-red-500 hover:bg-red-500/5 transition-colors text-left">
                            <Trash2 className="h-3.5 w-3.5" /> Delete
                          </button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${status.dot}`} />
                    <span className="text-xs text-muted-foreground">{status.label}</span>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                    {CONNECTION_LABELS[site.connection_type] ?? site.connection_type}
                  </span>
                </div>

                {site.last_crawled_at && (
                  <p className="text-xs text-muted-foreground/60 mt-3">Last crawled {formatRelativeTime(site.last_crawled_at)}</p>
                )}
              </motion.div>
            )
          })}
        </div>
      )}

      {/* Add Site Modal */}
      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowAdd(false)}>
            <motion.div initial={{ scale: 0.95, opacity: 0, y: 8 }} animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 8 }} transition={{ duration: 0.15 }}
              className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl p-6"
              onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-semibold text-foreground">Add New Site</h2>
                <button onClick={() => setShowAdd(false)} className="h-7 w-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleAdd} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">Site Name</label>
                  <input type="text" value={newSite.name} onChange={(e) => setNewSite({ ...newSite, name: e.target.value })}
                    placeholder="My Blog" required
                    className="w-full h-10 bg-background border border-border rounded-lg px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all" />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">Domain</label>
                  <input type="text" value={newSite.domain} onChange={(e) => setNewSite({ ...newSite, domain: e.target.value })}
                    placeholder="example.com" required
                    className="w-full h-10 bg-background border border-border rounded-lg px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all" />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">Connection Method</label>
                  <div className="relative">
                    <select value={newSite.connection_type} onChange={(e) => setNewSite({ ...newSite, connection_type: e.target.value })}
                      className="w-full h-10 bg-background border border-border rounded-lg px-3 pr-8 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all">
                      {CONNECTION_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={() => setShowAdd(false)}
                    className="flex-1 h-10 rounded-lg border border-border text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={createSite.isPending}
                    className="flex-1 h-10 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all flex items-center justify-center gap-2 disabled:opacity-60">
                    {createSite.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    {createSite.isPending ? 'Adding…' : 'Add Site'}
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
