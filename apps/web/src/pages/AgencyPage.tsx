import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Globe, Plus, Users } from 'lucide-react'
import { toast } from 'sonner'

import { agencyApi } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'

export default function AgencyPage() {
  const queryClient = useQueryClient()
  const { data: sitesData } = useSites()
  const { data } = useQuery({ queryKey: ['agency-clients'], queryFn: () => agencyApi.clients() })
  const clients = data?.clients ?? []
  const sites = sitesData?.sites ?? []
  const [form, setForm] = useState({ name: '', contact_email: '', brand_name: '', logo_url: '' })
  const [assignForm, setAssignForm] = useState({ client_id: '', site_id: '' })

  const createClient = useMutation({
    mutationFn: () => agencyApi.createClient({
      name: form.name,
      contact_email: form.contact_email || undefined,
      brand_name: form.brand_name || undefined,
      logo_url: form.logo_url || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agency-clients'] })
      setForm({ name: '', contact_email: '', brand_name: '', logo_url: '' })
      toast.success('Client created')
    },
  })
  const assignSite = useMutation({
    mutationFn: () => agencyApi.assignSite(assignForm.client_id, assignForm.site_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agency-clients'] })
      toast.success('Site assigned to client')
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Agency</h1>
        <p className="text-sm text-muted-foreground mt-1">Client workspaces, white-label report context, and proof-of-work organization for agencies.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-5">
          <Users className="h-5 w-5 text-primary" />
          <p className="mt-4 text-2xl font-bold text-foreground">{clients.length}</p>
          <p className="text-xs text-muted-foreground">Clients</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <Globe className="h-5 w-5 text-primary" />
          <p className="mt-4 text-2xl font-bold text-foreground">{sites.length}</p>
          <p className="text-xs text-muted-foreground">Managed sites</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <Building2 className="h-5 w-5 text-primary" />
          <p className="mt-4 text-2xl font-bold text-foreground">Read-only</p>
          <p className="text-xs text-muted-foreground">Client share links use snapshots, not credentials</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground">Create client</h2>
          <div className="mt-4 space-y-3">
            <input value={form.name} onChange={(event) => setForm(f => ({ ...f, name: event.target.value }))} placeholder="Client name" className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
            <input value={form.contact_email} onChange={(event) => setForm(f => ({ ...f, contact_email: event.target.value }))} placeholder="Contact email" className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
            <input value={form.brand_name} onChange={(event) => setForm(f => ({ ...f, brand_name: event.target.value }))} placeholder="Brand/report name" className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
            <input value={form.logo_url} onChange={(event) => setForm(f => ({ ...f, logo_url: event.target.value }))} placeholder="Logo URL" className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
            <button onClick={() => createClient.mutate()} disabled={!form.name.trim() || createClient.isPending} className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              <Plus className="h-4 w-4" />
              Create client
            </button>
          </div>
        </section>

        <section className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-foreground">Assign site to client</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <select value={assignForm.client_id} onChange={(event) => setAssignForm(f => ({ ...f, client_id: event.target.value }))} className="h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground focus:outline-none">
              <option value="">Choose client</option>
              {clients.map((client: any) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
            <select value={assignForm.site_id} onChange={(event) => setAssignForm(f => ({ ...f, site_id: event.target.value }))} className="h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground focus:outline-none">
              <option value="">Choose site</option>
              {sites.map((site: any) => <option key={site.id} value={site.id}>{site.name}</option>)}
            </select>
            <button onClick={() => assignSite.mutate()} disabled={!assignForm.client_id || !assignForm.site_id || assignSite.isPending} className="h-9 rounded-lg border border-border px-4 text-sm text-foreground hover:bg-muted disabled:opacity-50">Assign</button>
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold text-foreground">Clients</h2>
        </div>
        {clients.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">No agency clients yet.</p>
        ) : (
          <div className="divide-y divide-border">
            {clients.map((client: any) => (
              <div key={client.id} className="flex items-center justify-between gap-4 px-5 py-4">
                <div>
                  <p className="text-sm font-semibold text-foreground">{client.brand_name || client.name}</p>
                  <p className="text-xs text-muted-foreground">{client.contact_email || 'No contact email'} - {client.site_count} site(s)</p>
                </div>
                <span className="rounded-full border border-border bg-muted/30 px-2 py-0.5 text-[11px] text-muted-foreground">Snapshot-safe reports</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
