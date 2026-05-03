import { useState } from 'react'
import { motion } from 'framer-motion'
import { Bell, Building2, CreditCard, Key, Shield, User } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { authApi, notificationsApi, systemApi, teamApi } from '@/lib/api-client'
import { readinessMeta } from '@/lib/readiness'

const TABS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'organization', label: 'Organization', icon: Building2 },
  { id: 'billing', label: 'Billing', icon: CreditCard },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'api', label: 'API', icon: Key },
] as const

export default function SettingsPage() {
  const [tab, setTab] = useState<typeof TABS[number]['id']>('profile')
  const queryClient = useQueryClient()

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: () => authApi.getMe(),
  })

  const orgQuery = useQuery({
    queryKey: ['org'],
    queryFn: () => authApi.getOrg(),
  })

  const teamQuery = useQuery({
    queryKey: ['team-members'],
    queryFn: () => teamApi.list(),
    enabled: tab === 'organization',
  })

  const notificationPrefsQuery = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: () => notificationsApi.preferences(),
  })
  const readinessQuery = useQuery({
    queryKey: ['system-readiness-settings'],
    queryFn: () => systemApi.readiness(),
  })

  const updatePreferences = useMutation({
    mutationFn: (data: any) => notificationsApi.updatePreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-bell'] })
      toast.success('Notification preferences updated')
    },
  })

  const me = meQuery.data
  const org = orgQuery.data
  const prefs = notificationPrefsQuery.data
  const readiness = readinessQuery.data
  const billingReadiness = readiness?.features?.billing
  const aiReadiness = readiness?.features?.ai_fixes

  const togglePref = (field: string, value?: string) => {
    if (!prefs) return
    updatePreferences.mutate({ [field]: value !== undefined ? value : !prefs[field] })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Account, organization, notifications, and security.</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        <div className="lg:w-56 flex-shrink-0">
          <nav className="flex flex-row lg:flex-col gap-1 overflow-x-auto pb-2 lg:pb-0">
            {TABS.map((item) => (
              <button
                key={item.id}
                onClick={() => setTab(item.id)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all text-left w-full ${
                  tab === item.id
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted border border-transparent'
                }`}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex-1 min-w-0">
          <motion.div key={tab} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.15 }}>
            {tab === 'profile' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-4">
                <h2 className="text-base font-semibold text-foreground">Profile</h2>
                <div className="flex items-center gap-4 mb-2">
                  {me?.avatar_url ? (
                    <img src={me.avatar_url} alt={me.full_name || 'Avatar'} className="w-14 h-14 rounded-full border border-border object-cover flex-shrink-0" />
                  ) : (
                    <div className="w-14 h-14 rounded-full border border-border bg-muted flex items-center justify-center flex-shrink-0">
                      <span className="text-lg font-bold text-muted-foreground">{(me?.full_name || me?.email || 'U').charAt(0).toUpperCase()}</span>
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-semibold text-foreground">{me?.full_name || 'Not set'}</p>
                    <p className="text-xs text-muted-foreground">{me?.email || '—'}</p>
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Full name</p>
                    <p className="text-sm text-foreground">{me?.full_name || 'Not set'}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Email</p>
                    <p className="text-sm text-foreground">{me?.email || '—'}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Role</p>
                    <p className="text-sm text-foreground capitalize">{me?.role || 'member'}</p>
                  </div>
                  {me?.created_at && (
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Member since</p>
                      <p className="text-sm text-foreground">{new Date(me.created_at).toLocaleDateString()}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {tab === 'organization' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-4">
                <h2 className="text-base font-semibold text-foreground">Organization</h2>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Name</p>
                    <p className="text-sm text-foreground">{org?.name || '—'}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Plan</p>
                    <p className="text-sm text-foreground capitalize">{org?.plan || 'free'}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Slug</p>
                    <p className="text-sm text-foreground">{org?.slug || '—'}</p>
                  </div>
                  {org?.created_at && (
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Created</p>
                      <p className="text-sm text-foreground">{new Date(org.created_at).toLocaleDateString()}</p>
                    </div>
                  )}
                  {org?.updated_at && (
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Last updated</p>
                      <p className="text-sm text-foreground">{new Date(org.updated_at).toLocaleDateString()}</p>
                    </div>
                  )}
                </div>
                {(teamQuery.data?.members?.length > 0) && (
                  <div className="pt-2 border-t border-border space-y-2">
                    <p className="text-sm font-semibold text-foreground">Team members <span className="text-muted-foreground font-normal text-xs">({teamQuery.data.total ?? teamQuery.data.members.length})</span></p>
                    <div className="divide-y divide-border rounded-lg border border-border overflow-hidden">
                      {(teamQuery.data.members as any[]).map((member: any) => (
                        <div key={member.id} className="flex items-center gap-3 px-4 py-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold flex-shrink-0">
                            {(member.full_name || member.email || '?').charAt(0).toUpperCase()}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-foreground truncate">{member.full_name || member.email}</p>
                            {member.full_name && <p className="text-xs text-muted-foreground truncate">{member.email}</p>}
                            {member.status === 'pending' && member.invited_at && (
                              <p className="text-[10px] text-amber-500">Invited {new Date(member.invited_at).toLocaleDateString()}</p>
                            )}
                            {member.delivery_state?.label && (
                              <p className="text-[10px] text-muted-foreground/70">{member.delivery_state.label}</p>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1 flex-shrink-0">
                            <span className="text-[10px] font-semibold capitalize px-1.5 py-0.5 rounded-full border bg-muted text-muted-foreground border-border">{member.role}</span>
                            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${member.status === 'active' ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>{member.status}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {tab === 'billing' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-3">
                <h2 className="text-base font-semibold text-foreground">Billing</h2>
                <p className="text-sm text-muted-foreground">
                  Billing state is sourced from your organization record. Stripe portal wiring can build on this without changing the page contract again.
                </p>
                <div className="rounded-lg border border-border bg-muted/40 p-4">
                  <p className="text-sm font-medium text-foreground">Current plan</p>
                  <p className="text-xs text-muted-foreground mt-1 capitalize">{org?.plan || 'free'}</p>
                  {billingReadiness && (
                    <span className={`inline-flex items-center mt-3 px-2 py-0.5 rounded-full border text-[10px] font-semibold ${readinessMeta(billingReadiness.state).className}`}>
                      {billingReadiness.label}
                    </span>
                  )}
                </div>
              </div>
            )}

            {tab === 'notifications' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-1">
                <h2 className="text-base font-semibold text-foreground mb-4">Notification Preferences</h2>
                {[
                  ['email_enabled', 'Email notifications'],
                  ['in_app_enabled', 'In-app notifications'],
                  ['email_crawl_complete', 'Crawl complete emails'],
                  ['email_new_issues', 'New issue emails'],
                  ['email_fix_applied', 'Fix applied emails'],
                  ['email_weekly_digest', 'Weekly digest'],
                  ['slack_enabled', 'Slack notifications'],
                ].map(([field, label]) => (
                  <button
                    key={field}
                    onClick={() => togglePref(field)}
                    className="w-full flex items-center justify-between py-3.5 border-b border-border last:border-0 text-left"
                  >
                    <span className="text-sm font-medium text-foreground">{label}</span>
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${prefs?.[field] ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'}`}>
                      {prefs?.[field] ? 'On' : 'Off'}
                    </span>
                  </button>
                ))}
                {prefs?.slack_enabled && (
                  <div className="pt-2 pb-1">
                    <p className="text-xs text-muted-foreground mb-1.5">Slack webhook URL</p>
                    <input
                      type="url"
                      defaultValue={prefs?.slack_webhook_url ?? ''}
                      placeholder="https://hooks.slack.com/services/…"
                      className="w-full h-9 rounded-lg border border-border bg-background px-3 text-xs text-foreground placeholder:text-muted-foreground"
                      onBlur={(e) => e.target.value !== (prefs?.slack_webhook_url ?? '') && togglePref('slack_webhook_url', e.target.value)}
                    />
                    <p className="text-[10px] text-muted-foreground/70 mt-1">Create an incoming webhook in your Slack app settings and paste the URL here.</p>
                  </div>
                )}
              </div>
            )}

            {tab === 'security' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-4">
                <h2 className="text-base font-semibold text-foreground">Security</h2>
                <div className="rounded-lg border border-border bg-muted/30 p-4">
                  <p className="text-sm font-medium text-foreground">Authentication</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {readiness?.auth_mode === 'supabase'
                      ? 'Supabase browser auth is the active session source in this environment.'
                      : 'Local FastAPI JWT auth is the active browser session source in this environment.'}
                  </p>
                </div>
                <div className="rounded-lg border border-border bg-muted/30 p-4">
                  <p className="text-sm font-medium text-foreground">AI readiness</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {aiReadiness?.description ?? 'AI readiness is loading.'}
                  </p>
                </div>
                {readiness?.features && (
                  <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-2">
                    <p className="text-sm font-semibold text-foreground">Feature readiness</p>
                    <div className="space-y-2">
                      {Object.entries(readiness.features as Record<string, any>)
                        .filter(([k]) => k !== 'billing' && k !== 'ai_fixes')
                        .map(([key, feat]) => (
                          <div key={key} className="flex items-start gap-3">
                            <span className={`mt-0.5 flex-shrink-0 inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                              feat.state === 'working' ? 'bg-green-500/10 text-green-500 border-green-500/20'
                              : feat.state === 'setup_required' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                              : feat.state === 'saved_only' ? 'bg-blue-500/10 text-blue-500 border-blue-500/20'
                              : 'bg-muted text-muted-foreground border-border'
                            }`}>{feat.state === 'working' ? '✓' : feat.state === 'setup_required' ? '!' : feat.state === 'saved_only' ? '~' : '✗'}</span>
                            <div className="min-w-0">
                              <p className="text-xs font-medium text-foreground">{feat.label}</p>
                              <p className="text-[10px] text-muted-foreground leading-snug">{feat.description}</p>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
                {readiness?.providers && (
                  <div className="rounded-lg border border-border bg-muted/30 p-4">
                    <p className="text-sm font-semibold text-foreground mb-2">Provider status</p>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(readiness.providers as Record<string, boolean>).map(([name, active]) => (
                        <span key={name} className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                          active ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-muted text-muted-foreground border-border'
                        }`}>{name.replace(/_/g, ' ')}{active ? ' ✓' : ''}</span>
                      ))}
                    </div>
                  </div>
                )}
                {readiness && (
                  <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-2">
                    <p className="text-sm font-semibold text-foreground">Delivery &amp; auth status</p>
                    {[
                      { key: 'webhook_delivery_available', label: 'Webhook delivery' },
                      { key: 'report_delivery_configured', label: 'Report email delivery' },
                      { key: 'team_invite_delivery_configured', label: 'Team invite delivery' },
                    ].map(({ key, label }) => {
                      const active = readiness[key as keyof typeof readiness] as boolean
                      return (
                        <div key={key} className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">{label}</span>
                          <span className={`inline-flex px-1.5 py-0.5 rounded-full text-[10px] font-semibold border ${active ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}`}>
                            {active ? 'Ready' : 'Not configured'}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {tab === 'api' && (
              <div className="bg-card border border-border rounded-xl p-6 space-y-3">
                <h2 className="text-base font-semibold text-foreground">API Access</h2>
                <p className="text-sm text-muted-foreground">
                  API keys and webhook delivery configuration now live on dedicated pages backed by real endpoints.
                </p>
                <div className="grid sm:grid-cols-2 gap-4">
                  <a href="/dashboard/api-keys" className="rounded-lg border border-border bg-muted/30 p-4 hover:bg-muted transition-colors">
                    <p className="text-sm font-medium text-foreground">API Keys</p>
                    <p className="text-xs text-muted-foreground mt-1">Create and revoke scoped keys.</p>
                  </a>
                  <a href="/dashboard/integrations" className="rounded-lg border border-border bg-muted/30 p-4 hover:bg-muted transition-colors">
                    <p className="text-sm font-medium text-foreground">Integrations</p>
                    <p className="text-xs text-muted-foreground mt-1">Manage webhook endpoints and external connections.</p>
                  </a>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
