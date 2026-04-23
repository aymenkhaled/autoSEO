import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, Globe, Plus, Webhook, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { useSites } from '@/hooks/use-data'
import { webhooksApi } from '@/lib/api-client'

function WebhookModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    name: '',
    url: '',
    events: 'crawl_completed,fix_deployed',
  })

  const createWebhook = useMutation({
    mutationFn: (data: any) => webhooksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      toast.success('Webhook created')
      onClose()
    },
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    createWebhook.mutate({
      name: form.name,
      url: form.url,
      events: form.events.split(',').map((value) => value.trim()).filter(Boolean),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-foreground">Create Webhook</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Name</label>
            <input
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Endpoint URL</label>
            <input
              value={form.url}
              onChange={(event) => setForm((current) => ({ ...current, url: event.target.value }))}
              placeholder="https://example.com/webhooks/autoseo"
              className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Events</label>
            <input
              value={form.events}
              onChange={(event) => setForm((current) => ({ ...current, events: event.target.value }))}
              className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground"
            />
          </div>
          <div className="flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 h-10 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={createWebhook.isPending} className="flex-1 h-10 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
              {createWebhook.isPending ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}

export default function IntegrationsPage() {
  const { data: sitesData } = useSites()
  const { data: webhooksData } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => webhooksApi.list(),
  })
  const queryClient = useQueryClient()
  const [showWebhookModal, setShowWebhookModal] = useState(false)

  const testWebhook = useMutation({
    mutationFn: (id: string) => webhooksApi.test(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      toast.success('Webhook test sent')
    },
  })

  const sites = sitesData?.sites ?? []
  const webhooks = webhooksData?.webhooks ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Integrations</h1>
        <p className="text-sm text-muted-foreground mt-1">Live site connections and outbound webhooks.</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center gap-2">
            <Globe className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Site Connections</h2>
          </div>
          {sites.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">No sites added yet.</div>
          ) : (
            <div className="divide-y divide-border">
              {sites.map((site: any) => (
                <a key={site.id} href={`/dashboard/sites/${site.id}`} className="flex items-center justify-between px-5 py-4 hover:bg-muted/40 transition-colors">
                  <div>
                    <p className="text-sm font-medium text-foreground">{site.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{site.connection_type}</p>
                  </div>
                  <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${site.connection_type !== 'crawler' ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'}`}>
                    {site.connection_type !== 'crawler' && <CheckCircle2 className="h-3 w-3" />}
                    {site.connection_type}
                  </span>
                </a>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Webhook className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Webhooks</h2>
            </div>
            <button onClick={() => setShowWebhookModal(true)} className="inline-flex items-center gap-2 h-8 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors">
              <Plus className="h-3.5 w-3.5" /> Add
            </button>
          </div>
          {webhooks.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">No outbound webhooks configured.</div>
          ) : (
            <div className="divide-y divide-border">
              {webhooks.map((webhook: any) => (
                <div key={webhook.id} className="px-5 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{webhook.name}</p>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">{webhook.url}</p>
                    </div>
                    <button
                      onClick={() => testWebhook.mutate(webhook.id)}
                      disabled={testWebhook.isPending}
                      className="h-8 px-3 rounded-lg border border-border text-xs text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                    >
                      Test
                    </button>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-2">
                    Events: {(webhook.events ?? []).join(', ') || '—'}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
        {showWebhookModal && <WebhookModal onClose={() => setShowWebhookModal(false)} />}
      </AnimatePresence>
    </div>
  )
}
