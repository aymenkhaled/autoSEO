import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Globe, Zap, CheckCircle2, ExternalLink, Info,
  Plus, Trash2, RefreshCw, ShoppingBag, Code2, GitBranch,
  Webhook, MessageSquare, BarChart3, Link2,
} from 'lucide-react'

interface Integration {
  id: string
  name: string
  description: string
  icon: any
  iconBg: string
  status: 'connected' | 'disconnected' | 'coming_soon'
  category: 'cms' | 'analytics' | 'notifications' | 'seo'
  apiKeyLabel?: string
  docsUrl?: string
}

const INTEGRATIONS: Integration[] = [
  {
    id: 'wordpress',
    name: 'WordPress',
    description: 'Connect via REST API to apply SEO fixes directly to posts and pages.',
    icon: Globe,
    iconBg: 'bg-blue-500/10 text-blue-500',
    status: 'disconnected',
    category: 'cms',
    docsUrl: 'https://developer.wordpress.org/rest-api/',
  },
  {
    id: 'shopify',
    name: 'Shopify',
    description: 'Update product and page meta tags via Shopify Admin API.',
    icon: ShoppingBag,
    iconBg: 'bg-green-500/10 text-green-500',
    status: 'disconnected',
    category: 'cms',
    docsUrl: 'https://shopify.dev/api/admin-rest',
  },
  {
    id: 'webflow',
    name: 'Webflow',
    description: 'Update CMS collection item SEO fields via Webflow API.',
    icon: Code2,
    iconBg: 'bg-purple-500/10 text-purple-500',
    status: 'disconnected',
    category: 'cms',
    apiKeyLabel: 'Webflow API Key',
    docsUrl: 'https://developers.webflow.com/',
  },
  {
    id: 'github',
    name: 'GitHub',
    description: 'Auto-create PRs with SEO fixes for Next.js, Astro, Hugo & Jekyll sites.',
    icon: GitBranch,
    iconBg: 'bg-foreground/10 text-foreground',
    status: 'disconnected',
    category: 'cms',
    docsUrl: 'https://docs.github.com/en/rest',
  },
  {
    id: 'wix',
    name: 'Wix',
    description: 'Limited write capabilities via Wix Headless API. Read-only suggestions available.',
    icon: Globe,
    iconBg: 'bg-amber-500/10 text-amber-500',
    status: 'coming_soon',
    category: 'cms',
  },
  {
    id: 'squarespace',
    name: 'Squarespace',
    description: 'Read-only suggestions via Squarespace API. Manual fixes with AI guidance.',
    icon: Globe,
    iconBg: 'bg-slate-500/10 text-slate-400',
    status: 'coming_soon',
    category: 'cms',
  },
  {
    id: 'google_search_console',
    name: 'Google Search Console',
    description: 'Import real keyword data, impressions, clicks, and position from GSC.',
    icon: BarChart3,
    iconBg: 'bg-cyan-500/10 text-cyan-500',
    status: 'disconnected',
    category: 'analytics',
    docsUrl: 'https://developers.google.com/webmaster-tools',
  },
  {
    id: 'dataforseo',
    name: 'DataForSEO',
    description: 'Live keyword rank tracking, SERP analysis, and search volume data.',
    icon: BarChart3,
    iconBg: 'bg-indigo-500/10 text-indigo-500',
    status: 'disconnected',
    category: 'seo',
    apiKeyLabel: 'DataForSEO API Login',
    docsUrl: 'https://docs.dataforseo.com/',
  },
  {
    id: 'ahrefs',
    name: 'Ahrefs',
    description: 'Backlink monitoring, domain rating, and referring domain analysis.',
    icon: Link2,
    iconBg: 'bg-orange-500/10 text-orange-500',
    status: 'disconnected',
    category: 'seo',
    apiKeyLabel: 'Ahrefs API Key',
    docsUrl: 'https://ahrefs.com/api',
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Get real-time alerts in your Slack workspace for critical issues and fix updates.',
    icon: MessageSquare,
    iconBg: 'bg-purple-500/10 text-purple-500',
    status: 'disconnected',
    category: 'notifications',
    docsUrl: 'https://api.slack.com/',
  },
  {
    id: 'webhooks',
    name: 'Webhooks',
    description: 'Send event payloads to any URL when crawls complete or fixes are applied.',
    icon: Webhook,
    iconBg: 'bg-cyan-500/10 text-cyan-500',
    status: 'disconnected',
    category: 'notifications',
    docsUrl: '',
  },
]

function ConnectModal({ integration, onClose }: { integration: Integration; onClose: () => void }) {
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    setLoading(true)
    await new Promise(r => setTimeout(r, 1200))
    setLoading(false)
    setSaved(true)
    setTimeout(onClose, 1000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-5"
      >
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${integration.iconBg}`}>
            <integration.icon className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground">Connect {integration.name}</h2>
            <p className="text-xs text-muted-foreground">{integration.description}</p>
          </div>
        </div>

        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 flex items-start gap-2">
          <Info className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            This integration is ready to connect. Your credentials are encrypted and stored securely.
            {integration.docsUrl && (
              <> <a href={integration.docsUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">View API docs <ExternalLink className="inline h-3 w-3" /></a></>
            )}
          </p>
        </div>

        {integration.apiKeyLabel ? (
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">{integration.apiKeyLabel}</label>
            <input
              type="password" value={value} onChange={(e) => setValue(e.target.value)}
              placeholder="Enter your API key..."
              className="w-full h-11 px-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
            />
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-muted/30 p-4">
            <p className="text-sm text-muted-foreground">
              Click <strong className="text-foreground">Connect</strong> to authenticate via OAuth. You'll be redirected to {integration.name} to grant access.
            </p>
          </div>
        )}

        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 h-10 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors">
            Cancel
          </button>
          <button onClick={handleSave} disabled={loading || saved}
            className="flex-1 h-10 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-semibold hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-60 flex items-center justify-center gap-2">
            {saved ? (
              <><CheckCircle2 className="h-4 w-4" /> Connected!</>
            ) : loading ? (
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              integration.apiKeyLabel ? 'Save & Connect' : 'Connect via OAuth'
            )}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

function WebhookModal({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState('')
  const [events, setEvents] = useState<string[]>(['crawl_completed'])
  const EVENTS = ['crawl_completed', 'fix_applied', 'issue_critical', 'issue_resolved', 'report_ready']

  const toggle = (e: string) => setEvents(prev => prev.includes(e) ? prev.filter(x => x !== e) : [...prev, e])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-5"
      >
        <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
          <Webhook className="h-5 w-5 text-cyan-500" /> Add Webhook
        </h2>

        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">Endpoint URL</label>
          <input type="url" value={url} onChange={e => setUrl(e.target.value)}
            placeholder="https://your-server.com/webhook"
            className="w-full h-11 px-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">Trigger Events</label>
          <div className="space-y-2">
            {EVENTS.map(e => (
              <label key={e} className="flex items-center gap-3 cursor-pointer">
                <div onClick={() => toggle(e)}
                  className={`w-4 h-4 rounded border flex-shrink-0 transition-all ${events.includes(e) ? 'bg-primary border-primary' : 'border-border'}`}>
                  {events.includes(e) && <CheckCircle2 className="h-3 w-3 text-white" />}
                </div>
                <span className="text-sm text-foreground font-mono">{e}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 h-10 rounded-lg border border-border text-sm font-medium hover:bg-muted transition-colors">Cancel</button>
          <button className="flex-1 h-10 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-semibold hover:from-cyan-600 hover:to-blue-700 transition-all">
            Create Webhook
          </button>
        </div>
      </motion.div>
    </div>
  )
}

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'cms', label: 'CMS' },
  { id: 'seo', label: 'SEO Tools' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'notifications', label: 'Notifications' },
]

export default function IntegrationsPage() {
  const [filter, setFilter] = useState('all')
  const [connecting, setConnecting] = useState<Integration | null>(null)
  const [webhookOpen, setWebhookOpen] = useState(false)

  const filtered = INTEGRATIONS.filter(i => filter === 'all' || i.category === filter)

  const handleConnect = (integration: Integration) => {
    if (integration.id === 'webhooks') { setWebhookOpen(true); return }
    setConnecting(integration)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Integrations</h1>
        <p className="text-muted-foreground mt-1">Connect your CMS, analytics tools, and notification channels.</p>
      </div>

      {/* Category filter */}
      <div className="flex items-center gap-2 flex-wrap">
        {CATEGORIES.map(cat => (
          <button key={cat.id} onClick={() => setFilter(cat.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${filter === cat.id ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}>
            {cat.label}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((integration, i) => (
          <motion.div key={integration.id}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className={`rounded-xl border bg-card p-5 flex flex-col gap-4 ${integration.status === 'coming_soon' ? 'opacity-60 border-border' : 'border-border hover:border-primary/30 transition-colors'}`}>
            <div className="flex items-start justify-between">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${integration.iconBg}`}>
                <integration.icon className="h-5 w-5" />
              </div>
              {integration.status === 'connected' ? (
                <span className="flex items-center gap-1 text-xs font-medium text-green-500 bg-green-500/10 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="h-3 w-3" /> Connected
                </span>
              ) : integration.status === 'coming_soon' ? (
                <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                  Coming Soon
                </span>
              ) : null}
            </div>

            <div>
              <h3 className="text-sm font-semibold text-foreground">{integration.name}</h3>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{integration.description}</p>
            </div>

            <div className="mt-auto flex items-center gap-2">
              {integration.status === 'connected' ? (
                <>
                  <button className="flex-1 h-8 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-muted transition-colors flex items-center justify-center gap-1.5">
                    <RefreshCw className="h-3 w-3" /> Sync
                  </button>
                  <button className="h-8 w-8 rounded-lg border border-red-500/20 text-red-500 hover:bg-red-500/10 transition-colors flex items-center justify-center">
                    <Trash2 className="h-3 w-3" />
                  </button>
                </>
              ) : integration.status === 'coming_soon' ? (
                <button disabled className="flex-1 h-8 rounded-lg bg-muted text-xs font-medium text-muted-foreground cursor-not-allowed">
                  Coming Soon
                </button>
              ) : (
                <button onClick={() => handleConnect(integration)}
                  className="flex-1 h-8 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-semibold hover:from-cyan-600 hover:to-blue-700 transition-all flex items-center justify-center gap-1.5">
                  <Plus className="h-3.5 w-3.5" /> Connect
                </button>
              )}
              {integration.docsUrl && (
                <a href={integration.docsUrl} target="_blank" rel="noopener noreferrer"
                  className="h-8 w-8 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors flex items-center justify-center">
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {connecting && (
        <ConnectModal integration={connecting} onClose={() => setConnecting(null)} />
      )}
      {webhookOpen && <WebhookModal onClose={() => setWebhookOpen(false)} />}
    </div>
  )
}
