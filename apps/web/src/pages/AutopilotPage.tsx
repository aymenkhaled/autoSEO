import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Bot, FileText, Globe, Lock, Mail, Radar, RefreshCw, Search, Server, Sparkles } from 'lucide-react'

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
  const proofCurrent = proof.data?.current
  const latestAiRun = aiRuns.data?.runs?.[0]
  const briefRows = briefs.data?.briefs ?? []
  const digest = digestPreview.data as any

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

      <div className="grid gap-4 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-xs text-muted-foreground">SEO score</p>
          <p className="mt-2 text-3xl font-bold text-foreground">{proofCurrent?.seo_score ?? '-'}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-xs text-muted-foreground">Open issues</p>
          <p className="mt-2 text-3xl font-bold text-foreground">{proofCurrent?.open_issue_count ?? 0}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-xs text-muted-foreground">GSC impressions</p>
          <p className="mt-2 text-3xl font-bold text-foreground">{Math.round(proofCurrent?.gsc?.impressions ?? 0).toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-xs text-muted-foreground">GA4 revenue</p>
          <p className="mt-2 text-3xl font-bold text-foreground">${Number(proofCurrent?.ga4?.revenue ?? 0).toFixed(2)}</p>
        </div>
      </div>

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
            {actions.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">Run a crawl and connect GSC/GA4/PageSpeed to generate prioritized actions.</p>
            ) : actions.slice(0, 8).map((action: any) => (
              <article key={`${action.site_id}-${action.source}-${action.type}-${action.affected_url}`} className="rounded-xl border border-border bg-background p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{action.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{action.description}</p>
                    <p className="mt-2 text-[11px] text-cyan-200">{action.recommended_next_step}</p>
                  </div>
                  <Pill tone="good">{action.priority_score}</Pill>
                </div>
                {action.affected_url && <p className="mt-2 truncate text-[11px] text-muted-foreground">{action.affected_url}</p>}
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
            {digest?.sections && (
              <div className="mt-4 rounded-lg bg-muted/30 p-3">
                <p className="text-xs font-semibold text-foreground">Changed</p>
                <p className="mt-1 text-[11px] text-muted-foreground">{digest.sections.changed}</p>
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
          <div className="mb-4 flex items-center gap-2">
            <Radar className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">AI answer-readiness</h2>
          </div>
          <p className="mb-3 text-xs text-muted-foreground">
            This scores whether crawled pages are structured for AI/search answers. It does not query ChatGPT, Perplexity, Gemini, or Google AI Overviews yet.
          </p>
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
            <div className="mt-4 rounded-xl border border-border bg-background p-4">
              <div className="flex items-center gap-2">
                <Pill tone="good">Score {latestAiRun.visibility_score}</Pill>
                <Pill>Entity {latestAiRun.entity_score}</Pill>
                <Pill>Citation {latestAiRun.citation_score}</Pill>
              </div>
              <div className="mt-3 space-y-2">
                {(latestAiRun.recommendations ?? []).slice(0, 3).map((item: string) => <p key={item} className="text-xs text-muted-foreground">{item}</p>)}
              </div>
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
              <div key={brief.id} className="rounded-lg border border-border bg-background p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold text-foreground">{brief.title}</p>
                    <p className="mt-1 truncate text-[11px] text-muted-foreground">{brief.page_url}</p>
                  </div>
                  <Pill tone={brief.github_pr_url ? 'good' : 'warn'}>{brief.status}</Pill>
                </div>
                {brief.github_pr_url ? (
                  <a href={brief.github_pr_url} target="_blank" rel="noreferrer" className="mt-2 block text-[11px] text-primary hover:underline">Open PR</a>
                ) : (
                  <button onClick={() => createBriefPr.mutate(brief.id)} disabled={createBriefPr.isPending} className="mt-2 text-[11px] text-primary hover:underline disabled:opacity-50">Create GitHub PR plan</button>
                )}
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
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            <div className="rounded-lg bg-muted/30 p-3"><p className="text-xs text-muted-foreground">Googlebot hits</p><p className="text-xl font-bold text-foreground">{crawlBudget.data.by_bot?.googlebot ?? 0}</p></div>
            <div className="rounded-lg bg-muted/30 p-3"><p className="text-xs text-muted-foreground">Googlebot URLs outside crawl</p><p className="text-xl font-bold text-foreground">{crawlBudget.data.googlebot_not_crawled_by_autoseo?.length ?? 0}</p></div>
            <div className="rounded-lg bg-muted/30 p-3"><p className="text-xs text-muted-foreground">High-value URLs unseen by Googlebot</p><p className="text-xl font-bold text-foreground">{crawlBudget.data.high_value_not_seen_by_googlebot?.length ?? 0}</p></div>
          </div>
        )}
      </section>
    </div>
  )
}
