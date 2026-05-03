import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Bot, CheckCircle2, Clock, FileText, Globe, Lock, Mail, Radar, RefreshCw, Search, Server, Sparkles } from 'lucide-react'

import { aiVisibilityApi, autopilotApi, contentBriefsApi, crawlBudgetApi, proofApi } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'

function Pill({ children, tone = 'default' }: { children: React.ReactNode; tone?: 'default' | 'good' | 'warn' }) {
  const cls = tone === 'good'
    ? 'border-green-500/20 bg-green-500/10 text-green-300'
    : tone === 'warn'
      ? 'border-amber-500/20 bg-amber-500/10 text-amber-200'
      : 'border-border bg-muted/30 text-muted-foreground'
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${cls}`}>{children}</span>
}

export default function AutopilotPage() {
  const queryClient = useQueryClient()
  const { data: sitesData } = useSites()
  const sites = sitesData?.sites ?? []
  const [selectedSite, setSelectedSite] = useState('')
  const siteId = selectedSite || sites[0]?.id || ''
  const [aiPrompt, setAiPrompt] = useState('What is the best SEO automation platform for fixing technical SEO issues?')
  const [targetEntity, setTargetEntity] = useState('')
  const [competitors, setCompetitors] = useState('')
  const [briefForm, setBriefForm] = useState({ page_url: '', target_keyword: '' })
  const [rawLog, setRawLog] = useState('')

  const nextActions = useQuery({
    queryKey: ['autopilot-next-actions', siteId],
    queryFn: () => autopilotApi.nextActions(siteId || undefined),
    enabled: !!siteId,
  })
  const proof = useQuery({
    queryKey: ['proof', siteId],
    queryFn: () => proofApi.site(siteId),
    enabled: !!siteId,
  })
  const aiRuns = useQuery({
    queryKey: ['ai-visibility', siteId],
    queryFn: () => aiVisibilityApi.list(siteId),
    enabled: !!siteId,
  })
  const briefs = useQuery({
    queryKey: ['content-briefs', siteId],
    queryFn: () => contentBriefsApi.list(siteId),
    enabled: !!siteId,
  })
  const crawlBudget = useQuery({
    queryKey: ['crawl-budget', siteId],
    queryFn: () => crawlBudgetApi.summary(siteId),
    enabled: !!siteId,
  })

  const runAutopilot = useMutation({
    mutationFn: () => autopilotApi.run({ site_id: siteId, run_type: 'manual', create_snapshot: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autopilot-next-actions', siteId] })
      queryClient.invalidateQueries({ queryKey: ['proof', siteId] })
      toast.success('Autopilot run completed')
    },
  })
  const runAiVisibility = useMutation({
    mutationFn: () => aiVisibilityApi.run(siteId, {
      prompt: aiPrompt,
      target_entity: targetEntity || undefined,
      competitor_domains: competitors.split(',').map(item => item.trim()).filter(Boolean),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-visibility', siteId] })
      toast.success('AI visibility check completed')
    },
  })
  const createBrief = useMutation({
    mutationFn: () => contentBriefsApi.create({ site_id: siteId, page_url: briefForm.page_url, target_keyword: briefForm.target_keyword || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-briefs', siteId] })
      toast.success('Content brief created')
    },
  })
  const createBriefPr = useMutation({
    mutationFn: (id: string) => contentBriefsApi.createGithubPr(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-briefs', siteId] })
      toast.success('GitHub PR plan created for brief')
    },
  })
  const importLogs = useMutation({
    mutationFn: () => crawlBudgetApi.importLogs(siteId, { filename: 'manual-import.log', raw_log: rawLog }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawl-budget', siteId] })
      setRawLog('')
      toast.success('Logs imported')
    },
  })
  const digestPreview = useMutation({
    mutationFn: () => autopilotApi.digestPreview(siteId),
    onSuccess: () => toast.success('Digest preview ready'),
  })
  const digestSend = useMutation({
    mutationFn: () => autopilotApi.digestSend(siteId),
    onSuccess: (result: any) => toast.success(result.sent ? 'Digest sent' : 'Digest preview ready'),
  })

  const actions = nextActions.data?.actions ?? []
  const providerHealth: Record<string, { configured: boolean; role: string }> = nextActions.data?.provider_health ?? {}
  const proofCurrent = proof.data?.current
  const proofPairs: any[] = proof.data?.proof_pairs ?? []
  const proofStatus: string | undefined = proof.data?.proof_status
  const proofMessage: string | undefined = proof.data?.message
  const proofTimeline: any[] = (proof.data?.timeline ?? [])
    .slice().sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  const allSnapshots = proofPairs.flatMap((p: any) => p.manual_snapshots ?? [])
    .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  const displaySnapshots = proofTimeline.length > 0 ? proofTimeline : allSnapshots
  const latestAiRun = aiRuns.data?.runs?.[0]
  const briefRows = briefs.data?.briefs ?? []
  const digest = digestPreview.data as any

  const PROVIDER_LABELS: Record<string, string> = {
    gsc: 'Search Console',
    ga4: 'GA4',
    pagespeed: 'PageSpeed',
    github: 'GitHub',
    resend: 'Email (Resend)',
    serp_provider: 'SERP Provider',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Autopilot</h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
            Your weekly control room: proof, next actions, AI answer-readiness scoring, content refresh briefs, crawl-budget logs, and digest previews.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {sites.length > 0 && (
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select
                value={selectedSite}
                onChange={(event) => setSelectedSite(event.target.value)}
                className="h-9 min-w-[220px] rounded-lg border border-border bg-background pl-9 pr-3 text-sm text-foreground focus:outline-none"
              >
                {sites.map((site: any) => <option key={site.id} value={site.id}>{site.name}</option>)}
              </select>
            </div>
          )}
          <button
            onClick={() => runAutopilot.mutate()}
            disabled={!siteId || runAutopilot.isPending}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${runAutopilot.isPending ? 'animate-spin' : ''}`} />
            Run Autopilot
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-xs text-muted-foreground">SEO score</p>
          <p className={`mt-2 text-3xl font-bold ${proofCurrent?.seo_score >= 80 ? 'text-green-400' : proofCurrent?.seo_score >= 60 ? 'text-amber-400' : 'text-foreground'}`}>{proofCurrent?.seo_score ?? '-'}</p>
          {proofCurrent?.latest_crawl_completed_at && (
            <p className="text-[10px] text-muted-foreground/60 mt-1">{new Date(proofCurrent.latest_crawl_completed_at).toLocaleDateString()}</p>
          )}
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-xs text-muted-foreground">Open issues</p>
          <p className="mt-2 text-3xl font-bold text-foreground">{proofCurrent?.open_issue_count ?? 0}</p>
          {proofCurrent?.grouped_issue_count != null && proofCurrent.grouped_issue_count !== proofCurrent.open_issue_count && (
            <p className="text-[10px] text-muted-foreground/60 mt-1">{proofCurrent.grouped_issue_count} root cause groups · {proofCurrent.pages_crawled ?? 0} pages</p>
          )}
          {proofCurrent?.open_prs?.length > 0 && (
            <p className="text-[10px] text-amber-400 mt-1">{proofCurrent.open_prs.length} PR{proofCurrent.open_prs.length !== 1 ? 's' : ''} open</p>
          )}
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-xs text-muted-foreground">GSC impressions</p>
          <p className="mt-2 text-3xl font-bold text-foreground">{Math.round(proofCurrent?.gsc?.impressions ?? 0).toLocaleString()}</p>
          <div className="mt-1 flex gap-2 text-[10px] text-muted-foreground/70">
            {proofCurrent?.gsc?.clicks != null && <span>{Math.round(proofCurrent.gsc.clicks)} clicks</span>}
            {proofCurrent?.gsc?.ctr != null && proofCurrent.gsc.ctr > 0 && <span>{(proofCurrent.gsc.ctr * 100).toFixed(1)}% CTR</span>}
            {proofCurrent?.gsc?.position != null && proofCurrent.gsc.position > 0 && <span>pos {proofCurrent.gsc.position.toFixed(1)}</span>}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-xs text-muted-foreground">GA4 revenue</p>
          <p className="mt-2 text-3xl font-bold text-foreground">${Number(proofCurrent?.ga4?.revenue ?? 0).toFixed(2)}</p>
          <div className="mt-1 flex gap-2 text-[10px] text-muted-foreground/70">
            {proofCurrent?.ga4?.sessions != null && proofCurrent.ga4.sessions > 0 && <span>{Math.round(proofCurrent.ga4.sessions)} sessions</span>}
            {proofCurrent?.ga4?.key_events != null && proofCurrent.ga4.key_events > 0 && <span>{Math.round(proofCurrent.ga4.key_events)} key events</span>}
            {proofCurrent?.pagespeed?.avg_performance_score != null && <span>Perf {Math.round(proofCurrent.pagespeed.avg_performance_score)}</span>}
          </div>
        </div>
      </div>

      {(proofStatus || proofMessage || displaySnapshots.length > 0) && (
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold text-foreground">Proof History</h2>
              {proofStatus && (
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-semibold ${
                  proofStatus === 'ready' ? 'bg-green-500/10 text-green-400 border-green-500/20'
                  : proofStatus === 'waiting_for_deploy_recrawl' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  : 'bg-muted/50 text-muted-foreground border-border'
                }`}>
                  {proofStatus === 'ready' ? <CheckCircle2 className="h-2.5 w-2.5" /> : <Clock className="h-2.5 w-2.5" />}
                  {proofStatus.replace(/_/g, ' ')}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              {proof.data?.generated_at && (
                <span className="text-[10px] text-muted-foreground/60">refreshed {new Date(proof.data.generated_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
              )}
              <span className="text-xs text-muted-foreground">{displaySnapshots.length} snapshot{displaySnapshots.length !== 1 ? 's' : ''}</span>
            </div>
          </div>
          {proofMessage && (
            <p className="text-xs text-muted-foreground mb-4 leading-relaxed border-b border-border pb-3">{proofMessage}</p>
          )}
          {displaySnapshots.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left pb-2 pr-3 text-muted-foreground font-medium">Date</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium">Score</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium">Issues</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium hidden sm:table-cell">Groups</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium">Impressions</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium">Clicks</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium hidden md:table-cell">Sessions</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium hidden md:table-cell">Key Events</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium hidden lg:table-cell">Revenue</th>
                    <th className="text-right pb-2 pr-3 text-muted-foreground font-medium hidden sm:table-cell">Perf</th>
                    <th className="text-right pb-2 text-muted-foreground font-medium">Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {displaySnapshots.slice(0, 10).map((snap: any) => (
                    <tr key={snap.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-2.5 pr-3 text-muted-foreground whitespace-nowrap">
                        {snap.created_at ? new Date(snap.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                      <td className="py-2.5 pr-3 text-right">
                        <span className={`font-bold ${snap.seo_score >= 70 ? 'text-green-400' : snap.seo_score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                          {snap.seo_score ?? '—'}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-right text-foreground">{snap.open_issue_count ?? '—'}</td>
                      <td className="py-2.5 pr-3 text-right text-muted-foreground hidden sm:table-cell">{snap.grouped_issue_count ?? '—'}</td>
                      <td className="py-2.5 pr-3 text-right text-foreground">{snap.gsc_impressions != null ? Math.round(snap.gsc_impressions).toLocaleString() : '—'}</td>
                      <td className="py-2.5 pr-3 text-right text-foreground">{snap.gsc_clicks != null ? Math.round(snap.gsc_clicks).toLocaleString() : '—'}</td>
                      <td className="py-2.5 pr-3 text-right text-foreground hidden md:table-cell">{snap.ga_sessions != null ? Math.round(snap.ga_sessions).toLocaleString() : '—'}</td>
                      <td className="py-2.5 pr-3 text-right text-foreground hidden md:table-cell">{snap.ga_key_events != null ? Math.round(snap.ga_key_events).toLocaleString() : '—'}</td>
                      <td className="py-2.5 pr-3 text-right text-foreground hidden lg:table-cell">{snap.ga_revenue != null && snap.ga_revenue > 0 ? `$${Number(snap.ga_revenue).toFixed(2)}` : '—'}</td>
                      <td className="py-2.5 pr-3 text-right text-muted-foreground hidden sm:table-cell">{snap.pagespeed_score != null ? Math.round(snap.pagespeed_score) : '—'}</td>
                      <td className="py-2.5 text-right">
                        <div className="flex flex-col items-end gap-0.5">
                          <span className="text-muted-foreground capitalize">{snap.snapshot_type?.replace(/_/g, ' ') ?? snap.evidence?.trigger?.replace(/_/g, ' ') ?? '—'}</span>
                          {snap.issue_type && <span className="text-[9px] text-muted-foreground/70 capitalize">{snap.issue_type.replace(/_/g, ' ')}</span>}
                          {snap.evidence?.run_type && <span className="text-[9px] text-primary/60 capitalize">{snap.evidence.run_type.replace(/_/g, ' ')}</span>}
                          {snap.pr_url && <a href={snap.pr_url} target="_blank" rel="noreferrer" className="text-[9px] text-primary hover:underline">PR</a>}
                          {snap.branch && <span className="text-[9px] text-muted-foreground/60 font-mono">{snap.branch}</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground text-center py-4">No snapshots yet. Run Autopilot to capture the first proof snapshot.</p>
          )}
          {proofPairs.some((p: any) => p.before || p.after_recrawl) && (
            <div className="mt-4 pt-4 border-t border-border space-y-3">
              <p className="text-xs font-semibold text-foreground">Before / After comparisons</p>
              {proofPairs.filter((p: any) => p.before || p.after_recrawl).slice(0, 3).map((pair: any, i: number) => (
                <div key={i} className="rounded-lg bg-muted/20 px-3 py-2.5 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[11px] font-semibold text-foreground capitalize">{(pair.issue_type ?? 'fix').replace(/_/g, ' ')}</span>
                    {pair.proof_status && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${pair.proof_status === 'verified' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                        {pair.proof_status.replace(/_/g, ' ')}
                      </span>
                    )}
                    {pair.pr_url && <a href={pair.pr_url} target="_blank" rel="noreferrer" className="text-[10px] text-primary hover:underline">View PR</a>}
                    {pair.branch && <span className="text-[10px] font-mono text-muted-foreground/60">{pair.branch}</span>}
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                    {['before', 'after_recrawl', 'after_7_days', 'after_28_days'].map((key) => {
                      const snap = pair[key]
                      if (!snap) return null
                      return (
                        <div key={key} className="rounded bg-background border border-border px-2 py-1.5">
                          <p className="text-muted-foreground mb-1 capitalize">{key.replace(/_/g, ' ')}</p>
                          {snap.seo_score != null && <p className="font-bold text-foreground">{snap.seo_score} score</p>}
                          {snap.open_issue_count != null && <p className="text-muted-foreground">{snap.open_issue_count} issues{snap.grouped_issue_count != null && snap.grouped_issue_count !== snap.open_issue_count ? ` (${snap.grouped_issue_count} groups)` : ''}</p>}
                          {snap.gsc_impressions != null && <p className="text-muted-foreground">{Math.round(snap.gsc_impressions).toLocaleString()} impr{snap.gsc_clicks != null ? ` · ${Math.round(snap.gsc_clicks)} clicks` : ''}</p>}
                          {snap.ga_sessions != null && snap.ga_sessions > 0 && <p className="text-muted-foreground">{Math.round(snap.ga_sessions)} sessions</p>}
                          {snap.pagespeed_score != null && <p className="text-muted-foreground">Perf {Math.round(snap.pagespeed_score)}</p>}
                        </div>
                      )
                    })}
                  </div>
                  {pair.delta && (
                    <div className="flex flex-wrap gap-2 text-[10px]">
                      {pair.delta.seo_score_delta != null && pair.delta.seo_score_delta !== 0 && (
                        <span className={`px-1.5 py-0.5 rounded-full border font-semibold ${pair.delta.seo_score_delta > 0 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                          Score {pair.delta.seo_score_delta > 0 ? '+' : ''}{pair.delta.seo_score_delta}
                        </span>
                      )}
                      {pair.delta.issue_count_delta != null && pair.delta.issue_count_delta !== 0 && (
                        <span className={`px-1.5 py-0.5 rounded-full border font-semibold ${pair.delta.issue_count_delta < 0 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                          Issues {pair.delta.issue_count_delta > 0 ? '+' : ''}{pair.delta.issue_count_delta}
                        </span>
                      )}
                      {pair.delta.gsc_impressions_delta != null && pair.delta.gsc_impressions_delta !== 0 && (
                        <span className={`px-1.5 py-0.5 rounded-full border font-semibold ${pair.delta.gsc_impressions_delta > 0 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}`}>
                          {pair.delta.gsc_impressions_delta > 0 ? '+' : ''}{Math.round(pair.delta.gsc_impressions_delta).toLocaleString()} impr
                        </span>
                      )}
                    </div>
                  )}
                  {pair.manual_snapshots?.length > 0 && (
                    <div className="pt-2 border-t border-border/50">
                      <p className="text-[10px] text-muted-foreground/60 mb-1.5">Manual snapshots ({pair.manual_snapshots.length})</p>
                      <div className="flex flex-wrap gap-1.5">
                        {pair.manual_snapshots.map((ms: any) => (
                          <div key={ms.id} className="rounded bg-background border border-border px-2 py-1 text-[10px] space-y-0.5">
                            <p className="text-muted-foreground/70">{ms.created_at ? new Date(ms.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}{ms.evidence?.run_type ? ` · ${ms.evidence.run_type.replace(/_/g, ' ')}` : ''}</p>
                            {ms.seo_score != null && <p className="font-semibold text-foreground">{ms.seo_score} score</p>}
                            {ms.open_issue_count != null && <p className="text-muted-foreground">{ms.open_issue_count} issues{ms.grouped_issue_count != null && ms.grouped_issue_count !== ms.open_issue_count ? ` (${ms.grouped_issue_count} groups)` : ''}</p>}
                            {ms.gsc_impressions != null && ms.gsc_impressions > 0 && <p className="text-muted-foreground">{Math.round(ms.gsc_impressions).toLocaleString()} impr</p>}
                            {ms.pagespeed_score != null && <p className="text-muted-foreground">Perf {Math.round(ms.pagespeed_score)}</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {Object.keys(providerHealth).length > 0 && (
        <div className="rounded-xl border border-border bg-card px-5 py-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Provider Health</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(providerHealth).map(([key, info]) => (
              <div key={key}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium ${
                  info.configured
                    ? 'bg-green-500/10 text-green-400 border-green-500/20'
                    : 'bg-muted/50 text-muted-foreground border-border'
                }`}
                title={info.status ? `${info.role} · ${info.status.replace(/_/g, ' ')}` : info.role}>
                <span className={`w-1.5 h-1.5 rounded-full ${info.configured ? 'bg-green-400' : 'bg-muted-foreground/50'}`} />
                {PROVIDER_LABELS[key] ?? key}
                {info.status && !info.configured && (
                  <span className="text-[9px] opacity-60">({info.status.replace(/_/g, ' ')})</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Next best actions</h2>
              <p className="text-xs text-muted-foreground mt-1">Ranked by crawl severity, GSC demand, GA4 value, PageSpeed risk, proof state, and fix readiness.</p>
            </div>
            <Pill>{actions.length} actions</Pill>
          </div>
          <div className="space-y-3">
            {nextActions.data?.message && actions.length === 0 && (
              <p className="text-xs text-muted-foreground italic">{nextActions.data.message}</p>
            )}
            {actions.length === 0 && !nextActions.data?.message ? (
              <p className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">Run a crawl and connect GSC/GA4/PageSpeed to generate prioritized actions.</p>
            ) : actions.slice(0, 8).map((action: any) => (
              <article key={`${action.site_id}-${action.source}-${action.type}-${action.affected_url}`} className="rounded-xl border border-border bg-background p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground">{action.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{action.description}</p>
                    <p className="mt-2 text-[11px] text-cyan-200">{action.recommended_next_step}</p>
                  </div>
                  <Pill tone="good">{action.priority_score}</Pill>
                </div>
                {action.affected_url && <p className="mt-2 truncate text-[11px] text-muted-foreground font-mono">{action.affected_url}</p>}
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {action.source && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground capitalize">{action.source}</span>}
                  {action.impact_label && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">{action.impact_label}</span>}
                  {action.proof_status && action.proof_status !== 'none' && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${action.proof_status === 'verified' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                      Proof: {action.proof_status}
                    </span>
                  )}
                  {action.site_name && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">{action.site_name}</span>}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-3 flex items-center gap-2">
              <Mail className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Weekly digest</h2>
            </div>
            <p className="text-xs text-muted-foreground">Preview always works. Email sending works only when Resend is configured.</p>
            <div className="mt-4 flex gap-2">
              <button onClick={() => digestPreview.mutate()} disabled={!siteId || digestPreview.isPending} className="h-8 rounded-lg border border-border px-3 text-xs text-foreground hover:bg-muted disabled:opacity-50">Preview</button>
              <button onClick={() => digestSend.mutate()} disabled={!siteId || digestSend.isPending} className="h-8 rounded-lg border border-border px-3 text-xs text-foreground hover:bg-muted disabled:opacity-50">Send</button>
            </div>
            {digest?.message && (
              <div className="mt-4 rounded-lg bg-muted/30 p-3">
                {digest.site_name && <p className="text-[10px] font-semibold text-foreground mb-0.5">{digest.site_name}</p>}
                <p className="text-[11px] text-muted-foreground">{digest.message}</p>
                {digest.delivery_state && (
                  <span className="mt-1.5 inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold border bg-muted text-muted-foreground border-border">{String(digest.delivery_state).replace(/_/g, ' ')}</span>
                )}
                {digest.generated_at && (
                  <p className="text-[9px] text-muted-foreground/60 mt-0.5">{new Date(digest.generated_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</p>
                )}
              </div>
            )}
            {digest?.sections && (
              <div className="mt-3 space-y-1.5">
                {(['broke', 'changed', 'improved'] as const).map((key) => {
                  const val = digest.sections[key]
                  if (!val) return null
                  const color = key === 'broke' ? 'text-red-400' : key === 'improved' ? 'text-green-400' : 'text-amber-400'
                  return (
                    <div key={key} className="rounded-lg bg-background border border-border px-3 py-2">
                      <p className={`text-[9px] font-semibold uppercase tracking-wider mb-0.5 ${color}`}>{key}</p>
                      <p className="text-[11px] text-muted-foreground">{typeof val === 'string' ? val : JSON.stringify(val)}</p>
                    </div>
                  )
                })}
                {Array.isArray(digest.sections.waiting) && digest.sections.waiting.length > 0 && (
                  <div className="rounded-lg bg-background border border-border px-3 py-2">
                    <p className="text-[9px] font-semibold uppercase tracking-wider mb-1 text-muted-foreground">Waiting for deploy/recrawl</p>
                    {(digest.sections.waiting as any[]).slice(0, 3).map((item: any, i: number) => (
                      <p key={i} className="text-[10px] text-muted-foreground truncate">• {typeof item === 'string' ? item : item.title ?? JSON.stringify(item)}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
            {(digest?.top_actions ?? []).length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-xs font-semibold text-foreground">Top actions in this digest</p>
                {(digest.top_actions as any[]).slice(0, 3).map((action: any) => (
                  <div key={`${action.type}-${action.affected_url}`} className="rounded-lg bg-background border border-border px-3 py-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[11px] font-semibold text-foreground">{action.title}</p>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 flex-shrink-0">{action.impact_label}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{action.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-3 flex items-center gap-2">
              <Lock className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Trust rule</h2>
            </div>
            <p className="text-xs text-muted-foreground">AutoSEO should create PRs and proof snapshots, not silently touch production. Fixes are only “proven” after deploy and recrawl evidence.</p>
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Radar className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">{aiRuns.data?.label ?? 'AI answer-readiness'}</h2>
            </div>
            {aiRuns.data?.total != null && aiRuns.data.total > 0 && (
              <span className="text-[10px] text-muted-foreground">{aiRuns.data.total} run{aiRuns.data.total !== 1 ? 's' : ''}</span>
            )}
          </div>
          {aiRuns.data?.message ? (
            <p className="mb-3 text-xs text-muted-foreground">{aiRuns.data.message}</p>
          ) : (
            <p className="mb-3 text-xs text-muted-foreground">
              This scores whether crawled pages are structured for AI/search answers. It does not query ChatGPT, Perplexity, Gemini, or Google AI Overviews yet.
            </p>
          )}
          {aiRuns.data?.readiness && (
            <div className="mb-3">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold ${aiRuns.data.readiness === 'ready' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-muted text-muted-foreground border-border'}`}>
                {String(aiRuns.data.readiness).replace(/_/g, ' ')}
              </span>
            </div>
          )}
          <div className="space-y-3">
            <input value={aiPrompt} onChange={(event) => setAiPrompt(event.target.value)} className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
            <div className="grid gap-3 md:grid-cols-2">
              <input value={targetEntity} onChange={(event) => setTargetEntity(event.target.value)} placeholder="Target entity, e.g. AutoSEO" className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
              <input value={competitors} onChange={(event) => setCompetitors(event.target.value)} placeholder="competitor.com, other.com" className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
            </div>
            <button onClick={() => runAiVisibility.mutate()} disabled={!siteId || !aiPrompt.trim() || runAiVisibility.isPending} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-4 text-sm text-foreground hover:bg-muted disabled:opacity-50">
              <Search className="h-4 w-4" />
              Run visibility check
            </button>
          </div>
          {latestAiRun && (
            <div className="mt-4 rounded-xl border border-border bg-background p-4 space-y-3">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                  <Pill tone="good">Score {latestAiRun.visibility_score}</Pill>
                  <Pill>Entity {latestAiRun.entity_score}</Pill>
                  <Pill>Citation {latestAiRun.citation_score}</Pill>
                  {latestAiRun.status && latestAiRun.status !== 'completed' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 capitalize">{latestAiRun.status.replace(/_/g, ' ')}</span>
                  )}
                </div>
                {latestAiRun.created_at && (
                  <span className="text-[10px] text-muted-foreground/60 flex-shrink-0">{new Date(latestAiRun.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                )}
              </div>
              {latestAiRun.prompt && (
                <p className="text-[10px] text-muted-foreground/70 italic border-l-2 border-primary/30 pl-2">{latestAiRun.prompt}</p>
              )}
              {(latestAiRun.missing_context ?? []).length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Missing Context</p>
                  <ul className="space-y-1">
                    {(latestAiRun.missing_context as string[]).slice(0, 4).map((item, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                        <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(latestAiRun.competitor_mentions ?? []).length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Tracked Competitors</p>
                  <div className="flex flex-wrap gap-1.5">
                    {(latestAiRun.competitor_mentions as any[]).map((c) => (
                      <span key={c.domain} title={c.note || undefined} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-border bg-muted/30 text-[10px] text-muted-foreground">
                        {c.domain}
                        {c.status && c.status !== 'tracked_for_prompt' && (
                          <span className="opacity-60">· {c.status.replace(/_/g, ' ')}</span>
                        )}
                        <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${c.status === 'found' ? 'bg-red-400' : 'bg-muted-foreground/40'}`} />
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {(latestAiRun.recommendations ?? []).length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Recommendations</p>
                  <div className="space-y-1">
                    {(latestAiRun.recommendations as string[]).slice(0, 3).map((item, i) => (
                      <p key={i} className="text-xs text-muted-foreground">{item}</p>
                    ))}
                  </div>
                </div>
              )}
              {latestAiRun.evidence && (
                <div className="border-t border-border pt-3">
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Evidence</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="rounded-lg bg-muted/40 px-2 py-1.5 text-center">
                      <p className="text-sm font-bold text-foreground">{latestAiRun.evidence.pages_scored ?? 0}</p>
                      <p className="text-[9px] text-muted-foreground">Pages scored</p>
                    </div>
                    <div className="rounded-lg bg-muted/40 px-2 py-1.5 text-center">
                      <p className="text-sm font-bold text-foreground">{latestAiRun.evidence.schema_rich_pages ?? 0}</p>
                      <p className="text-[9px] text-muted-foreground">Schema-rich</p>
                    </div>
                    <div className="rounded-lg bg-muted/40 px-2 py-1.5 text-center">
                      <p className="text-sm font-bold text-foreground">{latestAiRun.evidence.faq_or_howto_pages ?? 0}</p>
                      <p className="text-[9px] text-muted-foreground">FAQ/HowTo</p>
                    </div>
                    <div className="rounded-lg bg-muted/40 px-2 py-1.5 text-center">
                      <p className="text-sm font-bold text-foreground">{latestAiRun.evidence.entity_overlap != null ? latestAiRun.evidence.entity_overlap.toFixed(2) : '—'}</p>
                      <p className="text-[9px] text-muted-foreground">Entity overlap</p>
                    </div>
                    {latestAiRun.evidence.prompt_overlap != null && (
                      <div className="rounded-lg bg-muted/40 px-2 py-1.5 text-center">
                        <p className="text-sm font-bold text-foreground">{latestAiRun.evidence.prompt_overlap.toFixed(2)}</p>
                        <p className="text-[9px] text-muted-foreground">Prompt overlap</p>
                      </div>
                    )}
                  </div>
                  {(latestAiRun.evidence.provider_note || latestAiRun.evidence.provider_status) && (
                    <p className="text-[10px] text-muted-foreground/70 italic mt-2">
                      {latestAiRun.evidence.provider_status && (
                        <span className="font-mono mr-1 text-muted-foreground/50">[{latestAiRun.evidence.provider_status.replace(/_/g, ' ')}]</span>
                      )}
                      {latestAiRun.evidence.provider_note}
                    </p>
                  )}
                  {latestAiRun.evidence.pending_issue_counts && Object.keys(latestAiRun.evidence.pending_issue_counts).length > 0 && (
                    <div className="mt-2">
                      <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Pending issues blocking AI visibility</p>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(latestAiRun.evidence.pending_issue_counts as Record<string, number>).map(([type, count]) => (
                          <span key={type} className="text-[9px] px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                            {type.replace(/_/g, ' ')}: {count}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Content refresh brief</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <input value={briefForm.page_url} onChange={(event) => setBriefForm(f => ({ ...f, page_url: event.target.value }))} placeholder="Crawled page URL" className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
            <input value={briefForm.target_keyword} onChange={(event) => setBriefForm(f => ({ ...f, target_keyword: event.target.value }))} placeholder="Target keyword" className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none" />
          </div>
          <button onClick={() => createBrief.mutate()} disabled={!siteId || !briefForm.page_url || createBrief.isPending} className="mt-3 inline-flex h-9 items-center gap-2 rounded-lg border border-border px-4 text-sm text-foreground hover:bg-muted disabled:opacity-50">
            <Sparkles className="h-4 w-4" />
            Create brief
          </button>
          <div className="mt-4 space-y-3">
            {briefRows.slice(0, 3).map((brief: any) => (
              <div key={brief.id} className="rounded-lg border border-border bg-background p-3 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-foreground">{brief.title}</p>
                    <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{brief.page_url}</p>
                    {brief.target_keyword && (
                      <p className="mt-0.5 text-[10px] text-cyan-300">Keyword: {brief.target_keyword}</p>
                    )}
                    {brief.updated_at && (
                      <p className="mt-0.5 text-[9px] text-muted-foreground/60">Updated {new Date(brief.updated_at).toLocaleDateString()}</p>
                    )}
                  </div>
                  <Pill tone={brief.github_pr_url ? 'good' : 'warn'}>{brief.status}</Pill>
                </div>
                {brief.brief?.metadata_variants?.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">Title variants</p>
                    {(brief.brief.metadata_variants as any[]).slice(0, 2).map((v: any, i: number) => (
                      <div key={i} className="rounded bg-muted/30 px-2 py-1.5">
                        <p className="text-[10px] font-semibold text-foreground">{v.title}</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">{v.meta_description}</p>
                      </div>
                    ))}
                  </div>
                )}
                {brief.brief?.recommended_sections?.length > 0 && (
                  <div>
                    <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Sections to add</p>
                    {(brief.brief.recommended_sections as string[]).slice(0, 3).map((s: string, i: number) => (
                      <p key={i} className="text-[10px] text-muted-foreground">• {s}</p>
                    ))}
                  </div>
                )}
                {brief.brief?.impact && (
                  <div className="flex gap-2 flex-wrap">
                    {brief.brief.impact.gsc_impressions > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">{Math.round(brief.brief.impact.gsc_impressions).toLocaleString()} impr</span>}
                    {brief.brief.impact.gsc_clicks > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">{brief.brief.impact.gsc_clicks} clicks</span>}
                    {brief.brief.impact.ga_sessions > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">{brief.brief.impact.ga_sessions} sessions</span>}
                    {brief.brief.impact.ga_key_events > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">{brief.brief.impact.ga_key_events} key events</span>}
                    {brief.brief.impact.ga_revenue > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">${brief.brief.impact.ga_revenue.toFixed(2)}</span>}
                    {brief.brief.impact.gsc_ctr > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">{(brief.brief.impact.gsc_ctr * 100).toFixed(1)}% CTR</span>}
                  </div>
                )}
                {brief.brief?.current_state && (brief.brief.current_state.word_count != null || brief.brief.current_state.title || brief.brief.current_state.meta_description) && (
                  <div className="rounded bg-muted/20 px-2.5 py-1.5 space-y-0.5">
                    <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Current page state</p>
                    {brief.brief.current_state.title && <p className="text-[10px] text-foreground truncate"><span className="text-muted-foreground mr-1">Title:</span>{brief.brief.current_state.title}</p>}
                    {brief.brief.current_state.meta_description && <p className="text-[10px] text-muted-foreground truncate"><span className="text-foreground/60 mr-1">Meta:</span>{brief.brief.current_state.meta_description}</p>}
                    {brief.brief.current_state.word_count != null && <p className="text-[10px] text-muted-foreground"><span className="text-foreground/60 mr-1">Words:</span>{brief.brief.current_state.word_count ?? '—'}</p>}
                    {brief.brief.current_state.schema_types?.length > 0 && <p className="text-[10px] text-muted-foreground"><span className="text-foreground/60 mr-1">Schema:</span>{(brief.brief.current_state.schema_types as string[]).join(', ')}</p>}
                  </div>
                )}
                {brief.brief?.schema_suggestions?.length > 0 && (
                  <div>
                    <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Schema to add</p>
                    {(brief.brief.schema_suggestions as string[]).slice(0, 2).map((s: string, i: number) => (
                      <p key={i} className="text-[10px] text-muted-foreground">• {s}</p>
                    ))}
                  </div>
                )}
                {brief.brief?.risk_notes?.length > 0 && (
                  <div className="rounded bg-red-500/5 border border-red-500/20 px-2.5 py-1.5">
                    <p className="text-[9px] font-semibold text-red-400 uppercase tracking-wider mb-1">Risk notes</p>
                    {(brief.brief.risk_notes as string[]).slice(0, 2).map((r: string, i: number) => (
                      <p key={i} className="text-[10px] text-red-300/80">• {r}</p>
                    ))}
                  </div>
                )}
                {brief.brief?.github_pr_steps?.length > 0 && (
                  <div className="rounded bg-muted/20 border border-border px-2.5 py-1.5">
                    <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">PR implementation steps</p>
                    {(brief.brief.github_pr_steps as string[]).map((step: string, i: number) => (
                      <p key={i} className="text-[10px] text-muted-foreground flex items-start gap-1.5"><span className="flex-shrink-0 text-primary/60 font-mono">{i + 1}.</span>{step}</p>
                    ))}
                  </div>
                )}
                {brief.brief?.generation?.mode && (
                  <p className="text-[9px] text-muted-foreground/60">
                    Generated: <span className="text-muted-foreground capitalize">{brief.brief.generation.mode.replace(/_/g, ' ')}</span>
                    {brief.brief.generation.tone && <span className="ml-1">· tone: {brief.brief.generation.tone}</span>}
                    {brief.brief.generation.ai_model && <span className="ml-1">· {brief.brief.generation.ai_model}</span>}
                    {brief.brief.generation.fallback_used && <span className="ml-1 text-amber-400/70">(deterministic fallback)</span>}
                    {brief.brief.generation.ai_error && <span className="ml-1 text-red-400/70">⚠ {brief.brief.generation.ai_error}</span>}
                  </p>
                )}
                <div className="flex items-center gap-3">
                  {brief.github_pr_url ? (
                    <a href={brief.github_pr_url} target="_blank" rel="noreferrer" className="text-[11px] text-primary hover:underline">Open PR</a>
                  ) : (
                    <button onClick={() => createBriefPr.mutate(brief.id)} disabled={createBriefPr.isPending} className="text-[11px] text-primary hover:underline disabled:opacity-50">Create GitHub PR plan</button>
                  )}
                  {brief.github_branch && (
                    <span className="text-[10px] font-mono text-muted-foreground/60">{brief.github_branch}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-border bg-card p-5">
        <div className="mb-4 flex items-center gap-2">
          <Server className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Log file / crawl budget intelligence</h2>
        </div>
        <p className="text-xs text-muted-foreground mb-3">Paste a small nginx/apache/Cloudflare-style access log sample. AutoSEO compares Googlebot hits with crawl and GSC coverage.</p>
        <textarea value={rawLog} onChange={(event) => setRawLog(event.target.value)} placeholder={'127.0.0.1 - - [26/Apr/2026:12:00:00 +0000] "GET /pricing HTTP/1.1" 200 1234 "-" "Googlebot/2.1"'} className="min-h-[92px] w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs text-foreground focus:outline-none" />
        <button onClick={() => importLogs.mutate()} disabled={!siteId || !rawLog.trim() || importLogs.isPending} className="mt-3 inline-flex h-9 items-center gap-2 rounded-lg border border-border px-4 text-sm text-foreground hover:bg-muted disabled:opacity-50">
          <Bot className="h-4 w-4" />
          Import log sample
        </button>
        {crawlBudget.data?.recommendations && (
          <div className="mt-4 space-y-3">
            <div className="grid gap-3 lg:grid-cols-3">
              <div className="rounded-lg bg-muted/30 p-3"><p className="text-xs text-muted-foreground">Googlebot hits</p><p className="text-xl font-bold text-foreground">{crawlBudget.data.by_bot?.googlebot ?? 0}</p></div>
              <div className="rounded-lg bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">Googlebot URLs outside crawl</p>
                <p className="text-xl font-bold text-foreground">{crawlBudget.data.googlebot_not_crawled_by_autoseo?.length ?? 0}</p>
                {(crawlBudget.data.googlebot_not_crawled_by_autoseo as string[])?.slice(0, 3).map((url: string, i: number) => (
                  <p key={i} className="text-[10px] text-muted-foreground/70 mt-0.5 truncate font-mono">{url}</p>
                ))}
              </div>
              <div className="rounded-lg bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">High-value URLs unseen by Googlebot</p>
                <p className="text-xl font-bold text-foreground">{crawlBudget.data.high_value_not_seen_by_googlebot?.length ?? 0}</p>
                {(crawlBudget.data.high_value_not_seen_by_googlebot as string[])?.slice(0, 3).map((url: string, i: number) => (
                  <p key={i} className="text-[10px] text-muted-foreground/70 mt-0.5 truncate font-mono">{url}</p>
                ))}
              </div>
            </div>
            {crawlBudget.data.by_status && Object.keys(crawlBudget.data.by_status).length > 0 && (
              <div className="flex flex-wrap gap-2">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider self-center mr-1">Status codes:</p>
                {Object.entries(crawlBudget.data.by_status as Record<string, number>).map(([code, count]) => (
                  <span key={code} className={`text-[10px] px-2 py-0.5 rounded-full border font-mono ${code.startsWith('2') ? 'bg-green-500/10 text-green-400 border-green-500/20' : code.startsWith('4') || code.startsWith('5') ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-muted text-muted-foreground border-border'}`}>
                    {code}: {count}
                  </span>
                ))}
              </div>
            )}
            {crawlBudget.data.message && (
              <p className="text-xs text-muted-foreground leading-relaxed">{crawlBudget.data.message}</p>
            )}
            {(crawlBudget.data.recommendations as string[]).length > 0 && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-1.5">
                <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">Budget Recommendations</p>
                {(crawlBudget.data.recommendations as string[]).map((rec: string, i: number) => (
                  <p key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                    <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                    {rec}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
