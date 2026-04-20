import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  User, Building2, CreditCard, Key, Bell, Shield,
  Copy, Check, ExternalLink, ChevronDown,
} from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'

const TABS = [
  { id: 'profile',       label: 'Profile',       icon: User },
  { id: 'organization',  label: 'Organization',  icon: Building2 },
  { id: 'billing',       label: 'Billing',        icon: CreditCard },
  { id: 'api-keys',      label: 'API Keys',       icon: Key },
  { id: 'notifications', label: 'Notifications',  icon: Bell },
  { id: 'security',      label: 'Security',       icon: Shield },
]

const NOTIFICATIONS = [
  { key: 'crawl',    label: 'Crawl completed',       desc: 'When a site crawl finishes',              def: true  },
  { key: 'critical', label: 'Critical issues found', desc: 'When critical SEO issues are detected',   def: true  },
  { key: 'fix',      label: 'Fix applied',           desc: 'When an AI fix is applied to your site',  def: true  },
  { key: 'digest',   label: 'Weekly digest',         desc: 'Weekly summary of SEO performance',       def: false },
]

function Toggle({ defaultChecked }: { defaultChecked: boolean }) {
  const [on, setOn] = useState(defaultChecked)
  return (
    <button onClick={() => setOn(!on)} role="switch" aria-checked={on}
      className={`relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors ${on ? 'bg-primary' : 'bg-border'}`}>
      <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${on ? 'translate-x-4.5' : 'translate-x-0.5'}`} />
    </button>
  )
}

function InputField({ label, type = 'text', placeholder, value, disabled }: {
  label: string; type?: string; placeholder?: string; value?: string; disabled?: boolean
}) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-foreground">{label}</label>
      <input type={type} placeholder={placeholder} defaultValue={value} disabled={disabled}
        className="w-full h-10 bg-background border border-border rounded-lg px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all disabled:opacity-50 disabled:cursor-not-allowed" />
    </div>
  )
}

export default function SettingsPage() {
  const [tab, setTab] = useState('profile')
  const [copied, setCopied] = useState(false)
  const { user } = useAuth()

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Manage your account, organization, and integrations</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <div className="lg:w-52 flex-shrink-0">
          <nav className="flex flex-row lg:flex-col gap-1 overflow-x-auto pb-2 lg:pb-0">
            {TABS.map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all text-left w-full ${
                  tab === t.id
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted border border-transparent'
                }`}>
                <t.icon className="h-4 w-4 flex-shrink-0" />
                {t.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content panel */}
        <div className="flex-1 min-w-0">
          <motion.div key={tab} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.15 }}>

            {tab === 'profile' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-5">
                <h2 className="text-base font-semibold text-foreground">Profile Settings</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <InputField label="Full Name" placeholder="Jane Smith" />
                  <InputField label="Email" type="email" placeholder="you@company.com" value={user?.email} disabled />
                </div>
                <div>
                  <InputField label="Job Title" placeholder="SEO Manager" />
                </div>
                <button className="h-9 px-5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
                  Save Changes
                </button>
              </div>
            )}

            {tab === 'organization' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-5">
                <h2 className="text-base font-semibold text-foreground">Organization</h2>
                <div className="max-w-md">
                  <InputField label="Organization Name" placeholder="Acme Inc." />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">Current Plan</label>
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold">
                      Starter (Free)
                    </span>
                    <a href="#" className="text-sm font-medium text-primary hover:underline flex items-center gap-1">
                      Upgrade <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
                <button className="h-9 px-5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
                  Save Changes
                </button>
              </div>
            )}

            {tab === 'billing' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-5">
                <h2 className="text-base font-semibold text-foreground">Billing & Subscription</h2>
                <div className="bg-muted/50 border border-border rounded-lg p-4 space-y-1">
                  <p className="text-sm font-medium text-foreground">Starter Plan</p>
                  <p className="text-xs text-muted-foreground">Free forever — no credit card required</p>
                </div>
                <p className="text-sm text-muted-foreground">
                  Manage your subscription and payment methods via our secure billing portal.
                </p>
                <button className="inline-flex items-center gap-2 h-9 px-5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
                  <CreditCard className="h-4 w-4" /> Open Billing Portal
                </button>
              </div>
            )}

            {tab === 'api-keys' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-5">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold text-foreground">API Keys</h2>
                  <button className="h-9 px-4 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
                    Generate Key
                  </button>
                </div>
                <p className="text-sm text-muted-foreground">
                  API keys allow programmatic access to AutoSEO. Available on Pro and Agency plans.
                </p>
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center mb-3">
                    <Key className="h-5 w-5 text-muted-foreground/50" />
                  </div>
                  <p className="text-sm font-medium text-foreground">No API keys yet</p>
                  <p className="text-xs text-muted-foreground mt-1">Generate your first key to get started</p>
                </div>
              </div>
            )}

            {tab === 'notifications' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-1">
                <h2 className="text-base font-semibold text-foreground mb-4">Notification Preferences</h2>
                {NOTIFICATIONS.map((pref) => (
                  <div key={pref.key} className="flex items-center justify-between py-3.5 border-b border-border last:border-0">
                    <div>
                      <p className="text-sm font-medium text-foreground">{pref.label}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{pref.desc}</p>
                    </div>
                    <Toggle defaultChecked={pref.def} />
                  </div>
                ))}
              </div>
            )}

            {tab === 'security' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-6">
                <h2 className="text-base font-semibold text-foreground">Security</h2>

                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-foreground">Two-Factor Authentication</h3>
                  <p className="text-sm text-muted-foreground">Add an extra layer of security to your account with 2FA.</p>
                  <button className="h-9 px-4 rounded-lg border border-border text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                    Enable 2FA
                  </button>
                </div>

                <div className="h-px bg-border" />

                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-foreground">Active Sessions</h3>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-border">
                    <div>
                      <p className="text-sm text-foreground font-medium">Current session</p>
                      <p className="text-xs text-muted-foreground mt-0.5">This device · Active now</p>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 border border-green-500/20">Active</span>
                  </div>
                </div>

                <div className="h-px bg-border" />

                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-red-500">Danger Zone</h3>
                  <p className="text-sm text-muted-foreground">Permanently delete your account and all associated data.</p>
                  <button className="h-9 px-4 rounded-lg border border-red-500/30 text-sm font-medium text-red-500 hover:bg-red-500/5 transition-colors">
                    Delete Account
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
