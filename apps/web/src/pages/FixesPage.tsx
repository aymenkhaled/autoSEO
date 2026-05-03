import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Wrench, Clock, CheckCircle2, RotateCcw, ArrowRight, Sparkles, Zap, Loader2, AlertTriangle, Globe, ChevronDown, History } from 'lucide-react'
import { Link } from 'react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, fixVersionsApi, systemApi } from '@/lib/api-client'
import { toast } from 'sonner'
import { useSites } from '@/hooks/use-data'
import { readinessMeta } from '@/lib/readiness'

function useFixableIssues(fixStatus: string, siteId?: string | null) {
  const searchParams: Record<string, string> = {
    fix_type: 'auto',
    fix_status: fixStatus,
    per_page: '50',
  }
  if (siteId) searchParams.site_id = siteId
  return useQuery({
    queryKey: ['fixes', fixStatus, siteId ?? 'all'],
    queryFn: () => apiClient.get('issues', { searchParams }).json<any>(),
  })
}

function useApplyFix() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (issue_id: string) =>
      apiClient.post('fixes/apply', { json: { issue_id } }).json<any>(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fixes'] })
      qc.invalidateQueries({ queryKey: ['issues'] })
      toast.success('Fix applied successfully')
    },
    onError: (e: any) => toast.error(e?.message || 'Failed to apply fix'),
  })
}

function useRollbackFix() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (issue_id: string) =>
      apiClient.post('fixes/rollback', { json: { issue_id } }).json<any>(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fixes'] })
      qc.invalidateQueries({ queryKey: ['issues'] })
      toast.success('Fix rolled back')
    },
    onError: () => toast.error('Failed to rollback fix'),
  })
}

const ISSUE_TYPE_LABELS: Record<string, string> = {
  spa_no_prerender: 'SPA Not Prerendered',
  duplicate_title: 'Duplicate Page Title',
  keyword_cannibalization: 'Keyword Cannibalization',
  stale_schema_date: 'Expired Schema Date',
  unverified_review_schema: 'Review Schema Needs Proof',
  missing_sitemap: 'Missing Sitemap',
  missing_robots: 'Missing Robots',
  missing_offer_schema: 'Missing Offer Schema',
  broken_og_image: 'Broken OG Image',
  missing_title: 'Missing Page Title',
  title_too_short: 'Title Too Short',
  title_too_long: 'Title Too Long',
  missing_meta_description: 'Missing Meta Description',
  meta_description_too_long: 'Meta Description Too Long',
  missing_h1: 'Missing H1 Tag',
  multiple_h1: 'Multiple H1 Tags',
  images_missing_alt_text: 'Images Missing Alt Text',
  missing_schema: 'Missing Structured Data',
  missing_canonical: 'Missing Canonical URL',
  missing_charset: 'Missing Charset Declaration',
  thin_content: 'Thin Content',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-500 bg-red-500/10 border-red-500/20',
  high: 'text-orange-500 bg-orange-500/10 border-orange-500/20',
  medium: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
  low: 'text-blue-500 bg-blue-500/10 border-blue-500/20',
}

function FixVersionHistory({ issueId }: { issueId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['fix-versions', issueId],
    queryFn: () => fixVersionsApi.list(issueId),
  })
  const versions: any[] = data?.versions ?? []
  if (isLoading) return <p className="text-xs text-muted-foreground py-2">Loading history…</p>
  if (versions.length === 0) return <p className="text-xs text-muted-foreground py-2">No version history recorded yet.</p>
  return (
    <div className="mt-3 space-y-2 pl-1">
      {versions.map((v: any) => (
        <div key={v.id} className="rounded-lg border border-border bg-muted/20 px-3 py-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">v{v.version_number} · {v.action?.replace(/_/g, ' ')}</span>
            <span className="text-[10px] text-muted-foreground">{v.created_at ? new Date(v.created_at).toLocaleDateString() : ''}</span>
          </div>
          {v.captured_value && (
            <p className="text-[11px] text-muted-foreground font-mono mt-1 line-through truncate">{v.captured_value}</p>
          )}
          {v.applied_value && (
            <p className="text-[11px] text-green-400 font-mono mt-0.5 truncate">{v.applied_value}</p>
          )}
        </div>
      ))}
    </div>
  )
}

export default function FixesPage() {
  const { data: sitesData } = useSites()
  const { data: readiness } = useQuery({
    queryKey: ['system-readiness-fixes'],
    queryFn: () => systemApi.readiness(),
  })
  const sites: any[] = sitesData?.sites ?? []
  const [siteId, setSiteId] = useState<string | null>(null)
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null)

  const { data: pendingData, isLoading: pendingLoading } = useFixableIssues('pending', siteId)
  const { data: appliedData } = useFixableIssues('deployed', siteId)
  const { data: rolledBackData } = useFixableIssues('rolled_back', siteId)
  const applyFix = useApplyFix()
  const rollback = useRollbackFix()

  const pending: any[] = pendingData?.issues ?? []
  const applied: any[] = appliedData?.issues ?? []
  const rolledBack: any[] = rolledBackData?.issues ?? []

  const pendingCount = pendingData?.total ?? 0
  const appliedCount = appliedData?.total ?? 0
  const rolledBackCount = rolledBackData?.total ?? 0
  const aiReadiness = readiness?.features?.ai_fixes
  const aiReadinessMeta = readinessMeta(aiReadiness?.state)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Fixes</h1>
          <p className="text-sm text-muted-foreground mt-0.5">AI-generated fixes ready for your review and deployment</p>
        </div>
        <div className="relative min-w-[220px]">
          <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <select value={siteId ?? ''} onChange={(e) => setSiteId(e.target.value || null)}
            className="w-full h-9 bg-card border border-border rounded-lg pl-9 pr-8 text-sm text-foreground appearance-none focus:outline-none focus:ring-2 focus:ring-primary/30">
            <option value="">All sites</option>
            {sites.map((s: any) => <option key={s.id} value={s.id}>{s.domain || s.name}</option>)}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>
      </div>

      {aiReadiness && aiReadiness.state !== 'working' && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-4 w-4 text-amber-300 mt-0.5" />
            <div className="space-y-2">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold ${aiReadinessMeta.className}`}>
                {aiReadiness.label}
              </span>
              <p className="text-xs text-amber-100 leading-relaxed">{aiReadiness.description}</p>
            </div>
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: Clock,        label: 'Pending Review', value: pendingCount,    color: 'bg-amber-500/10 text-amber-500' },
          { icon: CheckCircle2, label: 'Deployed',       value: appliedCount,    color: 'bg-green-500/10 text-green-500' },
          { icon: RotateCcw,    label: 'Reverted',       value: rolledBackCount, color: 'bg-slate-500/10 text-slate-500' },
        ].map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="bg-card border border-border rounded-xl p-4">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${s.color}`}>
              <s.icon className="h-4 w-4" />
            </div>
            <p className="text-xl font-bold text-foreground">{s.value}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{s.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Pending fixes */}
      {pendingLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
      ) : pending.length === 0 ? (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 bg-card border border-dashed border-border rounded-xl text-center">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
            <Sparkles className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-base font-semibold text-foreground mb-1">No fixes pending</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-sm">
            Once AutoSEO detects auto-fixable issues, it generates AI-powered fixes ready for your one-click approval.
          </p>
          <Link to="/dashboard/sites"
            className="inline-flex items-center gap-2 h-9 px-5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
            <Zap className="h-4 w-4" /> Add a Site to Start
          </Link>
        </motion.div>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Pending Fixes</h2>
            <span className="text-xs text-muted-foreground">{pendingCount} ready</span>
          </div>
          <div className="divide-y divide-border">
            {pending.map((issue: any, i: number) => {
              const title = ISSUE_TYPE_LABELS[issue.type] || issue.type.replace(/_/g, ' ')
              const sev = SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.low
              return (
                <motion.div key={issue.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-muted/50 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Wrench className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="text-sm font-medium text-foreground truncate capitalize">{title}</p>
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold border ${sev}`}>
                        {issue.severity}
                      </span>
                    </div>
                    {issue.current_value && (
                      <p className="text-xs text-muted-foreground font-mono truncate max-w-sm">
                        Current: {issue.current_value}
                      </p>
                    )}
                    {issue.proposed_fix && (
                      <p className="text-xs text-green-600 dark:text-green-400 font-mono truncate max-w-sm mt-0.5">
                        Fix: {issue.proposed_fix}
                      </p>
                    )}
                    {issue.proposed_fix_metadata?.description && (
                      <p className="text-[11px] text-muted-foreground/70 mt-0.5 truncate max-w-sm">{issue.proposed_fix_metadata.description}</p>
                    )}
                    <div className="mt-1 flex flex-wrap gap-1">
                      {issue.category && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-muted text-muted-foreground border-border capitalize">
                          {issue.category}
                        </span>
                      )}
                      {issue.impact_score != null && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-violet-500/10 text-violet-400 border-violet-500/20">
                          Impact: {issue.impact_score}
                        </span>
                      )}
                      {issue.ai_confidence != null && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${issue.ai_confidence >= 0.8 ? 'bg-green-500/10 text-green-400 border-green-500/20' : issue.ai_confidence >= 0.5 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                          AI conf: {Math.round(issue.ai_confidence * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => applyFix.mutate(issue.id)}
                      disabled={applyFix.isPending}
                      className="h-8 px-3 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-xs font-semibold shadow-sm shadow-cyan-500/25 transition-all flex items-center gap-1 disabled:opacity-50">
                      Apply <ArrowRight className="h-3 w-3" />
                    </button>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}

      {/* Deployed fixes history */}
      {applied.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Deployed Fixes</h2>
            <span className="text-xs text-muted-foreground">{appliedCount} deployed</span>
          </div>
          <div className="divide-y divide-border">
            {applied.map((issue: any, i: number) => {
              const title = ISSUE_TYPE_LABELS[issue.type] || issue.type.replace(/_/g, ' ')
              const historyOpen = expandedHistoryId === issue.id
              return (
                <motion.div key={issue.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03 }}
                  className="px-5 py-4 hover:bg-muted/50 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center flex-shrink-0">
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <p className="text-sm font-medium text-foreground capitalize">{title}</p>
                        {issue.severity && (
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold border ${SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.low}`}>
                            {issue.severity}
                          </span>
                        )}
                      </div>
                      {issue.current_value && (
                        <p className="text-xs text-muted-foreground font-mono truncate max-w-sm">
                          Before: {issue.current_value}
                        </p>
                      )}
                      {issue.applied_at && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Deployed {new Date(issue.applied_at).toLocaleDateString()}
                          {issue.verified_at && ` · Verified ${new Date(issue.verified_at).toLocaleDateString()}`}
                        </p>
                      )}
                      {issue.proposed_fix && (
                        <p className="text-xs text-green-600 dark:text-green-400 font-mono truncate max-w-sm mt-0.5">
                          Applied: {issue.proposed_fix}
                        </p>
                      )}
                      <div className="mt-1 flex flex-wrap gap-1">
                        {issue.verified_score != null && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
                            Score after: {issue.verified_score}
                          </span>
                        )}
                        {issue.category && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-muted text-muted-foreground border-border capitalize">
                            {issue.category}
                          </span>
                        )}
                        {issue.impact_score != null && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-violet-500/10 text-violet-400 border-violet-500/20">
                            Impact: {issue.impact_score}
                          </span>
                        )}
                        {issue.ai_confidence != null && (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${issue.ai_confidence >= 0.8 ? 'bg-green-500/10 text-green-400 border-green-500/20' : issue.ai_confidence >= 0.5 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                            AI {Math.round(issue.ai_confidence * 100)}%
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => setExpandedHistoryId(historyOpen ? null : issue.id)}
                      className="h-7 px-3 rounded-lg border border-border text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors flex items-center gap-1">
                      <History className="h-3 w-3" />
                      {historyOpen ? 'Hide' : 'History'}
                    </button>
                    <button onClick={() => rollback.mutate(issue.id)} disabled={rollback.isPending}
                      className="h-7 px-3 rounded-lg border border-border text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50 flex items-center gap-1">
                      <RotateCcw className="h-3 w-3" /> Rollback
                    </button>
                  </div>
                  <AnimatePresence>
                    {historyOpen && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden"
                      >
                        <FixVersionHistory issueId={issue.id} />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      )}

      {/* Reverted fixes */}
      {rolledBack.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Reverted Fixes</h2>
            <span className="text-xs text-muted-foreground">{rolledBackCount} reverted</span>
          </div>
          <div className="divide-y divide-border">
            {rolledBack.map((issue: any, i: number) => {
              const title = ISSUE_TYPE_LABELS[issue.type] || issue.type.replace(/_/g, ' ')
              return (
                <motion.div key={issue.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-muted/50 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-slate-500/10 flex items-center justify-center flex-shrink-0">
                    <RotateCcw className="h-4 w-4 text-slate-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <p className="text-sm font-medium text-foreground capitalize">{title}</p>
                      {issue.severity && (
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold border ${SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.low}`}>
                          {issue.severity}
                        </span>
                      )}
                    </div>
                    {(issue.rolled_back_at || issue.applied_at) && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Reverted {new Date(issue.rolled_back_at || issue.applied_at).toLocaleDateString()}
                      </p>
                    )}
                    {issue.proposed_fix && (
                      <p className="text-xs text-amber-400/80 font-mono truncate max-w-sm mt-0.5">
                        Was: {issue.proposed_fix}
                      </p>
                    )}
                    {issue.current_value && (
                      <p className="text-xs text-muted-foreground font-mono truncate max-w-sm mt-0.5">
                        Restored: {issue.current_value}
                      </p>
                    )}
                    <div className="mt-1 flex flex-wrap gap-1">
                      {issue.category && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-muted text-muted-foreground border-border capitalize">
                          {issue.category}
                        </span>
                      )}
                      {issue.impact_score != null && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-violet-500/10 text-violet-400 border-violet-500/20">
                          Impact: {issue.impact_score}
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold bg-slate-500/10 text-slate-400 border-slate-500/20">
                    rolled back
                  </span>
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      )}

      {/* How it works */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: AlertTriangle, title: 'Issue Detected', desc: 'AutoSEO crawls your site and detects SEO problems, scored by impact on rankings.' },
          { icon: Wrench, title: 'AI Generates Fix', desc: 'Claude analyzes each issue and writes the exact change — meta title, description, alt text, canonical, or schema.' },
          { icon: CheckCircle2, title: 'You Approve & Deploy', desc: 'Preview every change before it goes live. Approved fixes are pushed directly to your CMS with one click.' },
        ].map((step, i) => (
          <div key={step.title} className="bg-card border border-border rounded-xl p-5">
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
              <step.icon className="h-4 w-4 text-primary" />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-1">{step.title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{step.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
