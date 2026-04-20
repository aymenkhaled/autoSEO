import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Key, Copy, Trash2, X, Check, Shield, AlertTriangle } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import { formatRelativeTime } from '@/lib/utils'

function useApiKeys() {
  return useQuery({
    queryKey: ['api-keys'],
    queryFn: () => apiClient.get('/api-keys').json<any>(),
  })
}

function useCreateKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => apiClient.post('/api-keys', { json: data }).json<any>(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['api-keys'] }),
    onError: () => toast.error('Failed to create API key'),
  })
}

function useRevokeKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api-keys/${id}`).json<any>(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['api-keys'] })
      toast.success('API key revoked')
    },
    onError: () => toast.error('Failed to revoke key'),
  })
}

const ALL_SCOPES = [
  { value: 'read:sites', label: 'Read Sites', description: 'List and view site details' },
  { value: 'write:sites', label: 'Write Sites', description: 'Create and update sites' },
  { value: 'read:issues', label: 'Read Issues', description: 'View SEO issues' },
  { value: 'write:fixes', label: 'Write Fixes', description: 'Apply and rollback fixes' },
  { value: 'read:analytics', label: 'Read Analytics', description: 'Access analytics data' },
]

export default function ApiKeysPage() {
  const { data, isLoading } = useApiKeys()
  const createKey = useCreateKey()
  const revokeKey = useRevokeKey()
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', scopes: [] as string[] })
  const [newKey, setNewKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const keys = data?.api_keys ?? []

  const toggleScope = (scope: string) => {
    setForm(f => ({
      ...f,
      scopes: f.scopes.includes(scope) ? f.scopes.filter(s => s !== scope) : [...f.scopes, scope],
    }))
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim() || form.scopes.length === 0) return
    const result = await createKey.mutateAsync(form)
    setNewKey(result.key)
    setForm({ name: '', scopes: [] })
    setShowCreate(false)
  }

  const copyKey = async () => {
    if (!newKey) return
    await navigator.clipboard.writeText(newKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    toast.success('Copied to clipboard')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">API Keys</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage API access keys for external integrations</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
          <Plus className="h-4 w-4" /> Create Key
        </button>
      </div>

      {/* New key reveal banner */}
      <AnimatePresence>
        {newKey && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground mb-1">Save your API key — this is the only time it will be shown</p>
                <div className="flex items-center gap-2 mt-2">
                  <code className="flex-1 text-xs font-mono bg-background border border-border rounded-lg px-3 py-2 text-foreground truncate">
                    {newKey}
                  </code>
                  <button onClick={copyKey}
                    className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-border bg-background text-xs font-medium text-foreground hover:bg-muted transition-colors flex-shrink-0">
                    {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </div>
              <button onClick={() => setNewKey(null)} className="text-muted-foreground hover:text-foreground transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Create key modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }}
              className="bg-card border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-foreground">Create API Key</h2>
                <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Key Name *</label>
                  <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="e.g. Production Integration" required
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-2">Permissions *</label>
                  <div className="space-y-2">
                    {ALL_SCOPES.map(scope => (
                      <label key={scope.value}
                        className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${form.scopes.includes(scope.value) ? 'border-primary/40 bg-primary/5' : 'border-border hover:bg-muted'}`}>
                        <input type="checkbox" checked={form.scopes.includes(scope.value)}
                          onChange={() => toggleScope(scope.value)} className="sr-only" />
                        <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-all ${form.scopes.includes(scope.value) ? 'bg-primary border-primary' : 'border-border'}`}>
                          {form.scopes.includes(scope.value) && <Check className="h-3 w-3 text-primary-foreground" />}
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-foreground">{scope.label}</p>
                          <p className="text-[10px] text-muted-foreground">{scope.description}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setShowCreate(false)}
                    className="flex-1 h-9 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={createKey.isPending || form.scopes.length === 0}
                    className="flex-1 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {createKey.isPending ? 'Creating…' : 'Create Key'}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Keys list */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
            ))}
          </div>
        ) : keys.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
              <Key className="h-6 w-6 text-primary" />
            </div>
            <p className="text-sm font-medium text-foreground mb-1">No API keys yet</p>
            <p className="text-xs text-muted-foreground mb-4">Create a key to access the AutoSEO API programmatically</p>
            <button onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 h-8 px-4 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors">
              <Plus className="h-3.5 w-3.5" /> Create First Key
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Name</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden sm:table-cell">Key</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Permissions</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Last Used</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {keys.map((k: any, i: number) => (
                <motion.tr key={k.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                  className="hover:bg-muted/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="font-medium text-foreground">{k.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <code className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">{k.key_prefix}</code>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <div className="flex flex-wrap gap-1">
                      {(k.scopes || []).map((s: string) => (
                        <span key={s} className="text-[10px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded">{s}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    <span className="text-xs text-muted-foreground">
                      {k.last_used_at ? formatRelativeTime(k.last_used_at) : 'Never used'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => revokeKey.mutate(k.id)}
                      className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
