import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Code2, Globe, Info, Plus, Send, Settings, Webhook, X } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { useSites } from '@/hooks/use-data'
import { connectionSummary } from '@/lib/readiness'
import { connectionsApi, githubApi, webhooksApi, type ConnectionPayload, type ConnectionType } from '@/lib/api-client'

const CONNECTION_FIELDS: Record<ConnectionType, Array<{ key: keyof ConnectionPayload; label: string; placeholder?: string; secret?: boolean }>> = {
  crawler: [],
  snippet: [],
  wordpress: [
    { key: 'site_url', label: 'WordPress URL', placeholder: 'https://example.com' },
    { key: 'username', label: 'Username' },
    { key: 'app_password', label: 'Application password', secret: true },
  ],
  shopify: [
    { key: 'shop_domain', label: 'Shop domain', placeholder: 'store.myshopify.com' },
    { key: 'access_token', label: 'Admin API access token', secret: true },
  ],
  webflow: [
    { key: 'site_id', label: 'Webflow site ID' },
    { key: 'token', label: 'Webflow API token', secret: true },
  ],
  github: [
    { key: 'owner', label: 'Owner' },
    { key: 'repo', label: 'Repository' },
    { key: 'branch', label: 'Branch', placeholder: 'main' },
    { key: 'project_root', label: 'Project root', placeholder: 'apps/web or blank' },
    { key: 'build_command', label: 'Build command', placeholder: 'npm run build' },
    { key: 'package_manager', label: 'Package manager', placeholder: 'npm' },
    { key: 'github_token', label: 'GitHub token', secret: true },
  ],
}

function ConnectionModal({ site, onClose }: { site: any; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<ConnectionPayload>({
    connection_type: site.connection_type || 'crawler',
    branch: site.github_branch || 'main',
  })
  const [testResult, setTestResult] = useState<any>(null)
  const [githubInstallationId, setGithubInstallationId] = useState('')

  const capabilitiesQuery = useQuery({
    queryKey: ['connection-capabilities', site.id],
    queryFn: () => connectionsApi.capabilities(site.id),
  })

  const githubInstallQuery = useQuery({
    queryKey: ['github-install-url', site.id],
    queryFn: () => githubApi.installUrl(site.id),
    enabled: form.connection_type === 'github',
  })

  const repoAnalysis = useMutation({
    mutationFn: () => githubApi.repoAnalysis(site.id),
    onSuccess: () => toast.success('Repository analysis loaded'),
    onError: (error: any) => toast.error(error?.message || 'Repository analysis failed'),
  })

  const testConnection = useMutation({
    mutationFn: (payload: ConnectionPayload) => connectionsApi.test(site.id, payload),
    onSuccess: (result) => {
      setTestResult(result)
      if (result.success) toast.success(result.message)
      else toast.error(result.message)
    },
  })

  const saveConnection = useMutation({
    mutationFn: (payload: ConnectionPayload) => connectionsApi.save(site.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites'] })
      queryClient.invalidateQueries({ queryKey: ['site-connection', site.id] })
      queryClient.invalidateQueries({ queryKey: ['site-summary', site.id] })
      toast.success('Connection saved')
      onClose()
    },
    onError: async (error: any) => {
      toast.error(error?.message || 'Connection could not be saved')
    },
  })

  const completeGithubApp = useMutation({
    mutationFn: () => githubApi.completeInstall({
      site_id: site.id,
      installation_id: Number(githubInstallationId),
      owner: form.owner || '',
      repo: form.repo || '',
      branch: form.branch || 'main',
      project_root: form.project_root || '',
      build_command: form.build_command,
      package_manager: form.package_manager,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites'] })
      queryClient.invalidateQueries({ queryKey: ['site-connection', site.id] })
      queryClient.invalidateQueries({ queryKey: ['site-summary', site.id] })
      toast.success('GitHub App connection saved')
      onClose()
    },
    onError: async (error: any) => {
      const detail = error?.response ? await error.response.json().catch(() => null) : null
      toast.error(detail?.detail || error?.message || 'GitHub App connection could not be saved')
    },
  })

  const certifyConnection = useMutation({
    mutationFn: (mode: 'sandbox' | 'credentials') => connectionsApi.certify(site.id, form.connection_type, {
      mode,
      credentials: mode === 'credentials' ? form : undefined,
    }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['connection-capabilities', site.id] })
      toast.success(result.message || 'Connection certification updated')
    },
    onError: async (error: any) => {
      const detail = error?.response ? await error.response.json().catch(() => null) : null
      toast.error(detail?.detail || error?.message || 'Certification failed')
    },
  })

  const capabilities = capabilitiesQuery.data?.capabilities ?? []
  const selectedCapability = capabilities.find((item: any) => item.connection_type === form.connection_type)
  const fields = CONNECTION_FIELDS[form.connection_type]
  const isWritableChoice = !['crawler', 'snippet'].includes(form.connection_type)
  const needsVerification = isWritableChoice && !site.ownership_verified

  const updateField = (key: keyof ConnectionPayload, value: string | boolean) => {
    setForm(current => ({ ...current, [key]: value }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
        className="relative z-10 w-full max-w-2xl rounded-2xl border border-border bg-card p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-semibold text-foreground">Configure {site.name}</h2>
            <p className="text-xs text-muted-foreground mt-1">Pick the monitoring method or the real fix deployment method. Audit still uses the public crawler.</p>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5">
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Monitoring / fix deployment method</label>
            <select value={form.connection_type} onChange={(event) => updateField('connection_type', event.target.value as ConnectionType)}
              className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground">
              {capabilities.map((item: any) => (
                <option key={item.connection_type} value={item.connection_type}>{item.label}</option>
              ))}
            </select>
          </div>

          {selectedCapability && (
            <div className="rounded-xl border border-border bg-muted/30 p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Info className="h-4 w-4 text-primary mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-foreground">{selectedCapability.label}</p>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{selectedCapability.description}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {(selectedCapability.supported_fix_fields ?? []).length === 0 ? (
                  <span className="text-[11px] px-2 py-1 rounded-full bg-background border border-border text-muted-foreground">Read-only deployment</span>
                ) : selectedCapability.supported_fix_fields.map((field: string) => (
                  <span key={field} className="text-[11px] px-2 py-1 rounded-full bg-green-500/10 text-green-500 border border-green-500/20">
                    Can fix {field}
                  </span>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">{selectedCapability.unsupported_message}</p>
              <div className="rounded-lg border border-border bg-background p-3">
                <p className="text-xs font-semibold text-foreground">Certification: {selectedCapability.certification?.status?.replace(/_/g, ' ') || 'not tested'}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {selectedCapability.certification?.message || 'Run sandbox or credential certification before trusting this connection for a customer.'}
                </p>
              </div>
            </div>
          )}

          {form.connection_type === 'github' && (
            <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4 space-y-3">
              <div>
                <p className="text-sm font-semibold text-foreground">Recommended: GitHub App PR-only access</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Install the AutoSEO GitHub App on one selected repo. AutoSEO creates branches and PRs; it does not push to main or deploy silently.
                </p>
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Installation ID</label>
                  <input
                    value={githubInstallationId}
                    onChange={(event) => setGithubInstallationId(event.target.value)}
                    placeholder="Returned by GitHub after install"
                    className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground"
                  />
                </div>
                <div className="flex items-end gap-2">
                  <a
                    href={githubInstallQuery.data?.install_url || undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex-1 inline-flex items-center justify-center h-10 rounded-lg border border-border text-xs font-semibold transition-colors ${
                      githubInstallQuery.data?.install_url ? 'text-foreground hover:bg-muted' : 'text-muted-foreground pointer-events-none opacity-60'
                    }`}
                  >
                    Install GitHub App
                  </a>
                  <button
                    type="button"
                    onClick={() => completeGithubApp.mutate()}
                    disabled={completeGithubApp.isPending || needsVerification || !githubInstallationId || !form.owner || !form.repo}
                    className="flex-1 h-10 rounded-lg bg-green-600 text-white text-xs font-semibold hover:bg-green-700 transition-colors disabled:opacity-50"
                  >
                    {completeGithubApp.isPending ? 'Saving...' : 'Complete app setup'}
                  </button>
                </div>
              </div>
              {githubInstallQuery.data && !githubInstallQuery.data.configured && (
                <p className="text-xs text-amber-300">{githubInstallQuery.data.message}</p>
              )}
              <div className="rounded-lg border border-border bg-background p-3">
                <p className="text-xs font-semibold text-foreground">Advanced fallback</p>
                <p className="text-xs text-muted-foreground mt-1">
                  If the GitHub App is not configured yet, use a fine-grained token limited to one repo with Contents and Pull Requests read/write.
                </p>
              </div>
            </div>
          )}

          {fields.length > 0 && (
            <div className="grid sm:grid-cols-2 gap-3">
              {fields.map(field => (
                <div key={field.key}>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">{field.label}</label>
                  <input
                    type={field.secret ? 'password' : 'text'}
                    value={(form[field.key] as string) ?? ''}
                    onChange={(event) => updateField(field.key, event.target.value)}
                    placeholder={field.placeholder}
                    className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground"
                  />
                </div>
              ))}
            </div>
          )}

          {needsVerification && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              Verify ownership from the site Setup page before saving WordPress, Shopify, Webflow, or GitHub deployment credentials.
            </div>
          )}

          <label className="flex items-start gap-3 rounded-xl border border-border bg-background p-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!form.sandbox}
              onChange={(event) => updateField('sandbox', event.target.checked)}
              className="mt-1"
            />
            <span>
              <span className="block text-sm font-medium text-foreground">Sandbox test only</span>
              <span className="block text-xs text-muted-foreground mt-0.5">Use this to verify UI/API wiring without real WordPress, Shopify, Webflow, or GitHub credentials. Sandbox tests cannot be saved.</span>
            </span>
          </label>

          {testResult && (
            <div className={`rounded-lg px-3 py-2 text-xs border ${testResult.success ? 'border-green-500/20 bg-green-500/10 text-green-500' : 'border-red-500/20 bg-red-500/10 text-red-500'}`}>
              {testResult.message}
            </div>
          )}

          {repoAnalysis.data && (
            <div className="rounded-lg border border-border bg-background p-3 text-xs text-muted-foreground space-y-1">
              <p className="font-semibold text-foreground">Repo analysis: {repoAnalysis.data.analysis?.framework || 'unknown'}</p>
              <p>Project root: {repoAnalysis.data.analysis?.project_root || '.'}</p>
              <p>Candidate files: {(repoAnalysis.data.candidate_files ?? []).slice(0, 5).map((item: any) => item.path).join(', ') || 'none found'}</p>
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={() => testConnection.mutate(form)} disabled={testConnection.isPending}
              className="flex-1 h-10 rounded-lg border border-border text-sm text-foreground hover:bg-muted transition-colors disabled:opacity-50">
              {testConnection.isPending ? 'Testing...' : 'Test connection'}
            </button>
            <button onClick={() => certifyConnection.mutate(form.sandbox ? 'sandbox' : 'credentials')} disabled={certifyConnection.isPending || (isWritableChoice && needsVerification)}
              className="flex-1 h-10 rounded-lg border border-border text-sm text-foreground hover:bg-muted transition-colors disabled:opacity-50">
              {certifyConnection.isPending ? 'Certifying...' : form.sandbox ? 'Certify sandbox' : 'Certify credentials'}
            </button>
            {form.connection_type === 'github' && (
              <button onClick={() => repoAnalysis.mutate()} disabled={repoAnalysis.isPending}
                className="flex-1 h-10 rounded-lg border border-border text-sm text-foreground hover:bg-muted transition-colors disabled:opacity-50">
                {repoAnalysis.isPending ? 'Analyzing...' : 'Analyze repo'}
              </button>
            )}
            <button onClick={() => saveConnection.mutate({ ...form, sandbox: false })} disabled={saveConnection.isPending || form.sandbox || needsVerification}
              className="flex-1 h-10 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
              {saveConnection.isPending ? 'Saving...' : 'Save real connection'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

function WebhookModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ name: '', url: '', events: 'crawl.completed,fix.pr_created,fix.deployed,fix.apply_failed,webhook.test' })

  const createWebhook = useMutation({
    mutationFn: (data: any) => webhooksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      toast.success('Outbound webhook created')
      onClose()
    },
    onError: () => toast.error('Webhook could not be created'),
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    createWebhook.mutate({
      name: form.name,
      url: form.url,
      events: form.events.split(',').map(value => value.trim()).filter(Boolean),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-foreground">Create Outbound Webhook</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors"><X className="h-5 w-5" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Name</label>
            <input value={form.name} onChange={(event) => setForm(current => ({ ...current, name: event.target.value }))}
              required className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Public HTTPS endpoint</label>
            <input value={form.url} onChange={(event) => setForm(current => ({ ...current, url: event.target.value }))}
              placeholder="https://hooks.zapier.com/..." required
              className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Events</label>
            <input value={form.events} onChange={(event) => setForm(current => ({ ...current, events: event.target.value }))}
              className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground" />
          </div>
          <div className="flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 h-10 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">Cancel</button>
            <button type="submit" disabled={createWebhook.isPending} className="flex-1 h-10 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
              {createWebhook.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}

export default function IntegrationsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: sitesData } = useSites()
  const { data: webhooksData } = useQuery({ queryKey: ['webhooks'], queryFn: () => webhooksApi.list() })
  const queryClient = useQueryClient()
  const [showWebhookModal, setShowWebhookModal] = useState(false)
  const [selectedSite, setSelectedSite] = useState<any | null>(null)
  const [selectedWebhookId, setSelectedWebhookId] = useState<string | null>(null)

  const deliveriesQuery = useQuery({
    queryKey: ['webhook-deliveries', selectedWebhookId],
    queryFn: () => webhooksApi.deliveries(selectedWebhookId!),
    enabled: !!selectedWebhookId,
  })

  const testWebhook = useMutation({
    mutationFn: (id: string) => webhooksApi.test(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['webhook-deliveries', id] })
      setSelectedWebhookId(id)
      toast.success('Webhook test sent')
    },
    onError: () => toast.error('Webhook test failed'),
  })

  const sites = sitesData?.sites ?? []
  const webhooks = webhooksData?.webhooks ?? []
  const requestedSiteId = searchParams.get('site_id')

  useEffect(() => {
    if (!requestedSiteId || selectedSite || sites.length === 0) return
    const matched = sites.find((site: any) => site.id === requestedSiteId)
    if (matched) {
      setSelectedSite(matched)
    }
  }, [requestedSiteId, selectedSite, sites])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Integrations</h1>
        <p className="text-sm text-muted-foreground mt-1">Monitoring finds issues. Fix deployment needs a real writable integration. Outbound webhooks notify other tools.</p>
      </div>

      <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-4 flex items-start gap-3">
        <Info className="h-4 w-4 text-blue-300 mt-0.5" />
        <p className="text-xs text-blue-100 leading-relaxed">
          Webhooks are not WordPress/Shopify/Webflow/GitHub connections. They send AutoSEO events to systems like Zapier, Make, Slack, or your own backend.
        </p>
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
                <div key={site.id} className="flex items-center justify-between gap-4 px-5 py-4">
                  <button
                    type="button"
                    onClick={() => navigate(`/dashboard/sites/${site.id}?tab=setup`)}
                    className="min-w-0 text-left"
                  >
                    <p className="text-sm font-medium text-foreground truncate">{site.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Monitoring: {connectionSummary(site).monitoringLabel} - Write integration: {connectionSummary(site).writeLabel}
                    </p>
                  </button>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${site.connection_type !== 'crawler' && site.connection_type !== 'snippet' ? 'bg-amber-500/10 text-amber-300' : 'bg-muted text-muted-foreground'}`}>
                      {site.connection_type !== 'crawler' && site.connection_type !== 'snippet' && <Info className="h-3 w-3" />}
                      {site.connection_type === 'crawler' || site.connection_type === 'snippet' ? 'Monitoring only' : 'Write setup needed'}
                    </span>
                    <button
                      onClick={() => {
                        setSelectedSite(site)
                        setSearchParams({ site_id: site.id })
                      }}
                      className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border border-border text-xs text-foreground hover:bg-muted transition-colors"
                    >
                      <Settings className="h-3.5 w-3.5" /> Configure
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Webhook className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Outbound Webhooks</h2>
            </div>
            <button onClick={() => setShowWebhookModal(true)} className="inline-flex items-center gap-2 h-8 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors">
              <Plus className="h-3.5 w-3.5" /> Add
            </button>
          </div>

          <div className="px-5 py-3 border-b border-border bg-muted/20 text-xs text-muted-foreground space-y-1">
            <p className="flex items-center gap-2"><Send className="h-3.5 w-3.5" /> Sends JSON POST requests to your endpoint.</p>
            <p className="flex items-center gap-2"><Code2 className="h-3.5 w-3.5" /> Verify `X-AutoSEO-Signature` using HMAC-SHA256 over the raw body.</p>
          </div>

          {webhooks.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">No outbound webhooks configured.</div>
          ) : (
            <div className="divide-y divide-border">
              {webhooks.map((webhook: any) => (
                <div key={webhook.id} className="px-5 py-4 space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{webhook.name}</p>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">{webhook.url}</p>
                    </div>
                    <button onClick={() => testWebhook.mutate(webhook.id)} disabled={testWebhook.isPending}
                      className="h-8 px-3 rounded-lg border border-border text-xs text-foreground hover:bg-muted transition-colors disabled:opacity-50">
                      Test
                    </button>
                  </div>
                  <button onClick={() => setSelectedWebhookId(selectedWebhookId === webhook.id ? null : webhook.id)}
                    className="text-[11px] text-primary hover:underline">
                    {selectedWebhookId === webhook.id ? 'Hide deliveries' : 'Show deliveries'}
                  </button>
                  {selectedWebhookId === webhook.id && (
                    <div className="rounded-lg border border-border bg-background p-3 space-y-2">
                      {(deliveriesQuery.data?.deliveries ?? []).length === 0 ? (
                        <p className="text-xs text-muted-foreground">No deliveries yet. Send a test event first.</p>
                      ) : deliveriesQuery.data.deliveries.slice(0, 5).map((delivery: any) => (
                        <div key={delivery.id} className="flex items-center justify-between gap-3 text-xs">
                          <span className={delivery.success ? 'text-green-500' : 'text-red-500'}>
                            {delivery.success ? 'Success' : 'Failed'} {delivery.status_code ?? 'no status'}
                          </span>
                          <span className="text-muted-foreground truncate">{delivery.event}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
        {showWebhookModal && <WebhookModal onClose={() => setShowWebhookModal(false)} />}
        {selectedSite && (
          <ConnectionModal
            site={selectedSite}
            onClose={() => {
              setSelectedSite(null)
              if (requestedSiteId) setSearchParams({})
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
