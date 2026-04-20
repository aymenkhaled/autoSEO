import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Users, Mail, Shield, Trash2, X, Crown, Eye } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'

function useTeam() {
  return useQuery({
    queryKey: ['team'],
    queryFn: () => apiClient.get('/team').json<any>(),
  })
}

function useInvite() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => apiClient.post('/team/invite', { json: data }).json<any>(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['team'] })
      toast.success('Invitation sent')
    },
    onError: (e: any) => toast.error(e?.message || 'Failed to send invitation'),
  })
}

function useRemoveMember() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/team/${id}`).json<any>(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['team'] })
      toast.success('Member removed')
    },
    onError: () => toast.error('Failed to remove member'),
  })
}

const ROLE_CONFIG: Record<string, { label: string; icon: any; color: string; description: string }> = {
  owner: { label: 'Owner', icon: Crown, color: 'text-amber-500 bg-amber-500/10 border-amber-500/20', description: 'Full access' },
  admin: { label: 'Admin', icon: Shield, color: 'text-purple-500 bg-purple-500/10 border-purple-500/20', description: 'Manage sites & members' },
  member: { label: 'Member', icon: Users, color: 'text-blue-500 bg-blue-500/10 border-blue-500/20', description: 'View & fix issues' },
  viewer: { label: 'Viewer', icon: Eye, color: 'text-slate-500 bg-slate-500/10 border-slate-500/20', description: 'Read-only access' },
}

function StatusDot({ status }: { status: string }) {
  return (
    <span className={`inline-block w-1.5 h-1.5 rounded-full ${status === 'active' ? 'bg-green-500' : 'bg-amber-500'}`} />
  )
}

export default function TeamPage() {
  const { data, isLoading } = useTeam()
  const invite = useInvite()
  const remove = useRemoveMember()
  const [showInvite, setShowInvite] = useState(false)
  const [form, setForm] = useState({ email: '', role: 'member' })

  const members = data?.members ?? []

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.email.trim()) return
    await invite.mutateAsync(form)
    setForm({ email: '', role: 'member' })
    setShowInvite(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Team</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage team members and their access levels</p>
        </div>
        <button onClick={() => setShowInvite(true)}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors">
          <Plus className="h-4 w-4" /> Invite Member
        </button>
      </div>

      <AnimatePresence>
        {showInvite && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }}
              className="bg-card border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-base font-semibold text-foreground">Invite Team Member</h2>
                <button onClick={() => setShowInvite(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleInvite} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Email address *</label>
                  <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    placeholder="colleague@company.com" required
                    className="w-full h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30" />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1.5">Role</label>
                  <div className="grid grid-cols-2 gap-2">
                    {['admin', 'member', 'viewer'].map(role => {
                      const cfg = ROLE_CONFIG[role]
                      const Icon = cfg.icon
                      return (
                        <button key={role} type="button" onClick={() => setForm(f => ({ ...f, role }))}
                          className={`flex items-center gap-2 p-3 rounded-lg border text-left transition-all ${form.role === role ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted'}`}>
                          <Icon className={`h-4 w-4 ${form.role === role ? 'text-primary' : 'text-muted-foreground'}`} />
                          <div>
                            <p className={`text-xs font-semibold ${form.role === role ? 'text-primary' : 'text-foreground'}`}>{cfg.label}</p>
                            <p className="text-[10px] text-muted-foreground">{cfg.description}</p>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setShowInvite(false)}
                    className="flex-1 h-9 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={invite.isPending}
                    className="flex-1 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50">
                    {invite.isPending ? 'Sending…' : 'Send Invite'}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Member</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden sm:table-cell">Role</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 4 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-muted rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : members.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <Users className="h-10 w-10 text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">No team members yet</p>
                  </div>
                </td>
              </tr>
            ) : members.map((m: any, i: number) => {
              const role = ROLE_CONFIG[m.role] ?? ROLE_CONFIG.member
              const Icon = role.icon
              return (
                <motion.tr key={m.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                  className="hover:bg-muted/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                        {(m.full_name || m.email).charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-foreground">{m.full_name || m.email}</p>
                        {m.full_name && <p className="text-xs text-muted-foreground">{m.email}</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${role.color}`}>
                      <Icon className="h-3 w-3" /> {role.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <div className="flex items-center gap-2">
                      <StatusDot status={m.status} />
                      <span className="text-xs text-muted-foreground capitalize">{m.status}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {!m.is_self && (
                      <button onClick={() => remove.mutate(m.id)}
                        className="p-1.5 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-colors">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </td>
                </motion.tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Role legend */}
      <div className="bg-card border border-border rounded-xl p-4">
        <p className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Role permissions</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(ROLE_CONFIG).map(([key, cfg]) => {
            const Icon = cfg.icon
            return (
              <div key={key} className="flex items-start gap-2.5">
                <div className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 border ${cfg.color}`}>
                  <Icon className="h-3.5 w-3.5" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-foreground">{cfg.label}</p>
                  <p className="text-[10px] text-muted-foreground">{cfg.description}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
