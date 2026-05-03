import { useState } from 'react'
import { useParams, Link } from 'react-router'
import { motion } from 'framer-motion'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  AlertTriangle, ArrowLeft, ArrowUpDown, BarChart2, Brain, CheckCircle2,
  ChevronsRight, Copy, ExternalLink, FileText, GitPullRequest, Globe, Info,
  Link2, Loader2, Plus, Search, SendHorizontal, TrendingDown, TrendingUp, XCircle,
} from 'lucide-react'
import { aiVisibilityApi, contentBriefsApi, crawlBudgetApi, crawlsApi, siteIntelligenceApi } from '@/lib/api-client'

function ScoreDelta({ delta }: { delta: number | null }) {
  if (delta === null) return null
  if (delta > 0) return <span className="text-green-500 text-xs font-medium flex items-center gap-0.5"><TrendingUp className="h-3 w-3" />+{delta}</span>
  if (delta < 0) return <span className="text-red-500 text-xs font-medium flex items-center gap-0.5"><TrendingDown className="h-3 w-3" />{delta}</span>
  return <span className="text-muted-foreground text-xs">±0</span>
}

function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-muted-foreground text-sm">—</span>
  const cls = score >= 80 ? 'text-green-500 bg-green-500/10 border-green-500/20'
    : score >= 60 ? 'text-amber-500 bg-amber-500/10 border-amber-500/20'
    : 'text-red-500 bg-red-500/10 border-red-500/20'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border ${cls}`}>
      {score}
    </span>
  )
}

const TABS = [
  { id: 'score-history', label: 'Score History' },
  { id: 'health-trends', label: 'Health Trends' },
  { id: 'orphan-pages', label: 'Orphan Pages' },
  { id: 'duplicates', label: 'Duplicate Analysis' },
  { id: 'redirect-chains', label: 'Redirect Chains' },
  { id: 'internal-linking', label: 'Internal Linking' },
  { id: 'coverage-gaps', label: 'Coverage Gaps' },
  { id: 'pagespeed-trend', label: 'PageSpeed Trend' },
  { id: 'crawl-budget', label: 'Crawl Budget' },
  { id: 'ai-visibility', label: 'AI Visibility' },
  { id: 'content-briefs', label: 'Content Briefs' },
] as const

type TabId = typeof TABS[number]['id']

export default function SiteIntelligencePage() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState<TabId>('score-history')
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)

  const historyQuery = useQuery({
    queryKey: ['seo-score-history', id],
    queryFn: () => siteIntelligenceApi.seoScoreHistory(id!, 30),
    enabled: !!id && tab === 'score-history',
  })

  const orphanQuery = useQuery({
    queryKey: ['orphan-pages', id],
    queryFn: () => siteIntelligenceApi.orphanPages(id!),
    enabled: !!id && tab === 'orphan-pages',
  })

  const duplicateQuery = useQuery({
    queryKey: ['duplicate-analysis', id],
    queryFn: () => siteIntelligenceApi.duplicateAnalysis(id!),
    enabled: !!id && tab === 'duplicates',
  })

  const redirectQuery = useQuery({
    queryKey: ['redirect-chains', id],
    queryFn: () => siteIntelligenceApi.redirectChains(id!),
    enabled: !!id && tab === 'redirect-chains',
  })

  const linkingQuery = useQuery({
    queryKey: ['internal-linking', id],
    queryFn: () => siteIntelligenceApi.internalLinking(id!),
    enabled: !!id && tab === 'internal-linking',
  })

  const coverageQuery = useQuery({
    queryKey: ['coverage-gaps', id],
    queryFn: () => siteIntelligenceApi.coverageGaps(id!),
    enabled: !!id && tab === 'coverage-gaps',
  })

  const healthTrendsQuery = useQuery({
    queryKey: ['health-trends', id],
    queryFn: () => siteIntelligenceApi.healthTrends(id!),
    enabled: !!id && tab === 'health-trends',
  })

  const latestCrawlId = healthTrendsQuery.data?.crawls?.[0]?.crawl_id ?? null

  const crawlDiffQuery = useQuery({
    queryKey: ['crawl-diff', latestCrawlId],
    queryFn: () => crawlsApi.diff(latestCrawlId!),
    enabled: !!latestCrawlId && tab === 'health-trends',
  })

  const pagespeedTrendQuery = useQuery({
    queryKey: ['pagespeed-trend', id],
    queryFn: () => siteIntelligenceApi.pagespeedTrend(id!, 'mobile'),
    enabled: !!id && tab === 'pagespeed-trend',
  })

  const crawlBudgetQuery = useQuery({
    queryKey: ['crawl-budget', id],
    queryFn: () => crawlBudgetApi.summary(id!),
    enabled: !!id && tab === 'crawl-budget',
  })

  const queryClient = useQueryClient()
  const [aiPrompt, setAiPrompt] = useState('')
  const [briefPageUrl, setBriefPageUrl] = useState('')
  const [briefKeyword, setBriefKeyword] = useState('')
  const [expandedBriefId, setExpandedBriefId] = useState<string | null>(null)
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null)

  const aiVisibilityQuery = useQuery({
    queryKey: ['ai-visibility', id],
    queryFn: () => aiVisibilityApi.list(id!),
    enabled: !!id && tab === 'ai-visibility',
  })

  const contentBriefsQuery = useQuery({
    queryKey: ['content-briefs', id],
    queryFn: () => contentBriefsApi.list(id!),
    enabled: !!id && tab === 'content-briefs',
  })

  const runAiVisibility = useMutation({
    mutationFn: (data: any) => aiVisibilityApi.run(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-visibility', id] })
      setAiPrompt('')
      toast.success('AI visibility analysis complete')
    },
    onError: () => toast.error('Failed to run AI visibility analysis'),
  })

  const createBrief = useMutation({
    mutationFn: (data: any) => contentBriefsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-briefs', id] })
      setBriefPageUrl('')
      setBriefKeyword('')
      toast.success('Content brief created')
    },
    onError: () => toast.error('Failed to create content brief'),
  })

  const copyUrl = (url: string) => {
    navigator.clipboard.writeText(url).then(() => {
      setCopiedUrl(url)
      setTimeout(() => setCopiedUrl(null), 2000)
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to={`/dashboard/sites/${id}`}
          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Site Intelligence</h1>
          <p className="text-sm text-muted-foreground">Advanced SEO diagnostics and structural analysis</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
                tab === t.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}>
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}>

        {/* ── Score History ── */}
        {tab === 'score-history' && (
          <div className="space-y-4">
            {historyQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {historyQuery.data && (() => {
              const { history, summary } = historyQuery.data
              return (
                <div className="space-y-4">
                  {/* Summary cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: 'Latest Score', value: summary.latest_score ?? '—', color: summary.latest_score >= 80 ? 'text-green-500' : summary.latest_score >= 60 ? 'text-amber-500' : 'text-red-500' },
                      { label: 'Earliest Score', value: summary.earliest_score ?? '—', color: 'text-foreground' },
                      { label: 'Total Change', value: summary.total_delta != null ? (summary.total_delta > 0 ? `+${summary.total_delta}` : `${summary.total_delta}`) : '—', color: summary.total_delta > 0 ? 'text-green-500' : summary.total_delta < 0 ? 'text-red-500' : 'text-muted-foreground' },
                      { label: 'Trend', value: summary.trend ?? '—', color: summary.trend === 'improving' ? 'text-green-500' : summary.trend === 'declining' ? 'text-red-500' : 'text-muted-foreground' },
                    ].map((card) => (
                      <div key={card.label} className="bg-card border border-border rounded-xl p-4">
                        <p className="text-xs text-muted-foreground mb-1">{card.label}</p>
                        <p className={`text-2xl font-bold capitalize ${card.color}`}>{card.value}</p>
                      </div>
                    ))}
                  </div>
                  {/* History table */}
                  {history.length === 0 ? (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                      <BarChart2 className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">No completed crawls with SEO scores yet. Run a crawl to start tracking history.</p>
                    </div>
                  ) : (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/40">
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">#</th>
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Date</th>
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">SEO Score</th>
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Delta</th>
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Pages</th>
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Issues</th>
                            </tr>
                          </thead>
                          <tbody>
                            {[...history].reverse().map((row: any, i: number) => (
                              <tr key={row.crawl_id} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                                <td className="px-4 py-3 text-muted-foreground">{history.length - i}</td>
                                <td className="px-4 py-3 text-foreground">
                                  {row.completed_at ? new Date(row.completed_at).toLocaleDateString() : '—'}
                                </td>
                                <td className="px-4 py-3"><ScoreBadge score={row.seo_score} /></td>
                                <td className="px-4 py-3"><ScoreDelta delta={row.delta} /></td>
                                <td className="px-4 py-3 text-foreground">{row.pages_crawled ?? '—'}</td>
                                <td className="px-4 py-3 text-foreground">{row.issues_found ?? '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}

        {/* ── Orphan Pages ── */}
        {tab === 'orphan-pages' && (
          <div className="space-y-4">
            {orphanQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {orphanQuery.data && (
              <>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex gap-3">
                  <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-amber-500">{orphanQuery.data.total} orphan page{orphanQuery.data.total !== 1 ? 's' : ''} found</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{orphanQuery.data.note}</p>
                  </div>
                </div>
                {orphanQuery.data.total === 0 ? (
                  <div className="bg-card border border-border rounded-xl p-8 text-center">
                    <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                    <p className="text-sm font-medium text-foreground">No orphan pages found</p>
                    <p className="text-xs text-muted-foreground mt-1">All crawled pages have at least one internal link pointing to them.</p>
                  </div>
                ) : (
                  <div className="bg-card border border-border rounded-xl overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-border bg-muted/40">
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">URL</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Title</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Score</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Words</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Status</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Issues</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground hidden md:table-cell">Response</th>
                            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground hidden lg:table-cell">Source</th>
                          </tr>
                        </thead>
                        <tbody>
                          {orphanQuery.data.pages.map((page: any) => (
                            <tr key={page.id} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                              <td className="px-4 py-3 max-w-xs">
                                <div className="flex items-center gap-2">
                                  <a href={page.url} target="_blank" rel="noopener noreferrer"
                                    className="text-primary hover:underline truncate text-xs font-mono">
                                    {page.url}
                                  </a>
                                  <button onClick={() => copyUrl(page.url)} className="text-muted-foreground hover:text-foreground flex-shrink-0">
                                    {copiedUrl === page.url ? <CheckCircle2 className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
                                  </button>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-muted-foreground max-w-xs">
                                <span className="truncate block">{page.title || '—'}</span>
                              </td>
                              <td className="px-4 py-3"><ScoreBadge score={page.seo_score} /></td>
                              <td className="px-4 py-3 text-foreground">{page.word_count ?? '—'}</td>
                              <td className="px-4 py-3">
                                {page.status_code != null ? (
                                  <span className={`text-xs font-mono px-1.5 py-0.5 rounded border ${page.status_code >= 500 ? 'bg-red-500/10 text-red-400 border-red-500/20' : page.status_code >= 400 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-green-500/10 text-green-400 border-green-500/20'}`}>
                                    {page.status_code}
                                  </span>
                                ) : '—'}
                              </td>
                              <td className="px-4 py-3 text-foreground">{page.issue_count ?? '—'}</td>
                              <td className="px-4 py-3 text-muted-foreground hidden md:table-cell">{page.response_time_ms != null ? `${page.response_time_ms}ms` : '—'}</td>
                              <td className="px-4 py-3 hidden lg:table-cell">
                                {page.source && typeof page.source === 'object' ? (
                                  <div className="space-y-0.5">
                                    {page.source.connection_type && (
                                      <span className="inline-block text-[10px] px-1.5 py-0.5 rounded bg-muted border border-border text-muted-foreground capitalize">{page.source.connection_type}</span>
                                    )}
                                    {page.source.source_url && (
                                      <a href={page.source.source_url} target="_blank" rel="noopener noreferrer"
                                        className="block text-[10px] text-primary hover:underline font-mono truncate max-w-[160px]"
                                        title={page.source.source_url}>
                                        {page.source.source_path || page.source.source_url}
                                      </a>
                                    )}
                                    {!page.source.source_url && page.source.source_path && (
                                      <span className="block text-[10px] text-muted-foreground font-mono truncate max-w-[160px]">{page.source.source_path}</span>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-xs text-muted-foreground">—</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Duplicate Analysis ── */}
        {tab === 'duplicates' && (
          <div className="space-y-6">
            {duplicateQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {duplicateQuery.data && (() => {
              const { duplicates, summary, total_pages_analyzed, note } = duplicateQuery.data
              return (
                <div className="space-y-6">
                  {note && (
                    <div className="rounded-xl border border-border bg-muted/30 p-4 flex items-start gap-3">
                      <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-muted-foreground">{note}</p>
                    </div>
                  )}
                  {/* Summary */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: 'Pages Analyzed', value: total_pages_analyzed, sub: 'total crawled' },
                      { label: 'Duplicate Title Groups', value: summary.duplicate_title_groups, sub: `${summary.duplicate_title_pages} pages affected` },
                      { label: 'Duplicate Meta Groups', value: summary.duplicate_meta_groups, sub: `${summary.duplicate_meta_pages} pages affected` },
                      { label: 'Duplicate Content Groups', value: summary.duplicate_content_groups ?? 0, sub: `${summary.duplicate_content_pages ?? 0} pages affected` },
                    ].map((c) => (
                      <div key={c.label} className="bg-card border border-border rounded-xl p-4">
                        <p className="text-xs text-muted-foreground mb-1">{c.label}</p>
                        <p className={`text-2xl font-bold ${(c.value as number) > 0 && c.label !== 'Pages Analyzed' ? 'text-amber-500' : 'text-foreground'}`}>{c.value}</p>
                        <p className="text-xs text-muted-foreground mt-1">{c.sub}</p>
                      </div>
                    ))}
                  </div>

                  {/* Duplicate Titles */}
                  {duplicates.titles.length > 0 && (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="px-4 py-3 border-b border-border bg-muted/30">
                        <h3 className="text-sm font-semibold text-foreground">Duplicate Page Titles ({duplicates.titles.length} groups)</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">Multiple pages share the same title tag — they compete for the same search intent.</p>
                      </div>
                      <div className="divide-y divide-border">
                        {duplicates.titles.slice(0, 15).map((group: any, i: number) => (
                          <div key={i} className="px-4 py-3">
                            <p className="text-sm font-medium text-foreground mb-2">"{group.title}" — {group.count} pages</p>
                            <div className="space-y-1">
                              {group.urls.map((url: string) => (
                                <a key={url} href={url} target="_blank" rel="noopener noreferrer"
                                  className="flex items-center gap-1.5 text-xs text-primary hover:underline font-mono">
                                  <ExternalLink className="h-3 w-3 flex-shrink-0" />{url}
                                </a>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Duplicate Meta Descriptions */}
                  {duplicates.meta_descriptions.length > 0 && (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="px-4 py-3 border-b border-border bg-muted/30">
                        <h3 className="text-sm font-semibold text-foreground">Duplicate Meta Descriptions ({duplicates.meta_descriptions.length} groups)</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">Identical meta descriptions reduce CTR differentiation in search results.</p>
                      </div>
                      <div className="divide-y divide-border">
                        {duplicates.meta_descriptions.slice(0, 10).map((group: any, i: number) => (
                          <div key={i} className="px-4 py-3">
                            <p className="text-xs text-muted-foreground mb-2 italic">"{group.meta_description}" — {group.count} pages</p>
                            <div className="space-y-1">
                              {group.urls.map((url: string) => (
                                <a key={url} href={url} target="_blank" rel="noopener noreferrer"
                                  className="flex items-center gap-1.5 text-xs text-primary hover:underline font-mono">
                                  <ExternalLink className="h-3 w-3 flex-shrink-0" />{url}
                                </a>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Duplicate Content */}
                  {duplicates.content?.length > 0 && (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="px-4 py-3 border-b border-border bg-muted/30">
                        <h3 className="text-sm font-semibold text-foreground">Duplicate Content ({duplicates.content.length} groups)</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">Pages with near-identical body content — these dilute link equity and confuse search engines.</p>
                      </div>
                      <div className="divide-y divide-border">
                        {duplicates.content.slice(0, 10).map((group: any, i: number) => (
                          <div key={i} className="px-4 py-3">
                            <p className="text-xs text-muted-foreground mb-2 font-medium">{group.count} pages share similar content</p>
                            <div className="space-y-1">
                              {group.urls.map((url: string) => (
                                <a key={url} href={url} target="_blank" rel="noopener noreferrer"
                                  className="flex items-center gap-1.5 text-xs text-primary hover:underline font-mono">
                                  <ExternalLink className="h-3 w-3 flex-shrink-0" />{url}
                                </a>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {summary.duplicate_title_groups === 0 && summary.duplicate_meta_groups === 0 && !duplicates.content?.length && (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                      <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                      <p className="text-sm font-medium text-foreground">No duplicate titles, meta descriptions, or content found</p>
                      <p className="text-xs text-muted-foreground mt-1">All analyzed pages have unique title tags, meta descriptions, and content.</p>
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}

        {/* ── Redirect Chains ── */}
        {tab === 'redirect-chains' && (
          <div className="space-y-4">
            {redirectQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {redirectQuery.isError && (
              <div className="bg-card border border-border rounded-xl p-8 text-center">
                <XCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">Could not load redirect chain data. Run a crawl first.</p>
              </div>
            )}
            {redirectQuery.data && (() => {
              const { chains, summary } = redirectQuery.data
              return (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="bg-card border border-border rounded-xl p-4">
                      <p className="text-xs text-muted-foreground mb-1">Chain Pages</p>
                      <p className={`text-2xl font-bold ${summary.total_chain_pages > 0 ? 'text-amber-500' : 'text-foreground'}`}>{summary.total_chain_pages}</p>
                    </div>
                    <div className="bg-card border border-border rounded-xl p-4">
                      <p className="text-xs text-muted-foreground mb-1">Max Hops</p>
                      <p className="text-2xl font-bold text-foreground">{summary.max_hops}</p>
                    </div>
                    <div className="bg-card border border-border rounded-xl p-4">
                      <p className="text-xs text-muted-foreground mb-1">Avg Hops</p>
                      <p className="text-2xl font-bold text-foreground">{summary.avg_hops}</p>
                    </div>
                  </div>
                  {redirectQuery.data.note && (
                    <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 px-4 py-3">
                      <Info className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-muted-foreground leading-relaxed">{redirectQuery.data.note}</p>
                    </div>
                  )}
                  {chains.length === 0 ? (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                      <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                      <p className="text-sm font-medium text-foreground">No redirect chains found</p>
                      <p className="text-xs text-muted-foreground mt-1">All redirects are single-hop or pages return 200 directly.</p>
                    </div>
                  ) : (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/40">
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Source URL</th>
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Final URL</th>
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Hops</th>
                              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {chains.map((chain: any, i: number) => (
                              <tr key={i} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                                <td className="px-4 py-3 max-w-xs">
                                  <a href={chain.url} target="_blank" rel="noopener noreferrer"
                                    className="text-primary hover:underline text-xs font-mono truncate block">
                                    {chain.url}
                                  </a>
                                </td>
                                <td className="px-4 py-3 max-w-xs">
                                  {chain.final_url ? (
                                    <a href={chain.final_url} target="_blank" rel="noopener noreferrer"
                                      className="text-primary hover:underline text-xs font-mono truncate block">
                                      {chain.final_url}
                                    </a>
                                  ) : '—'}
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border ${chain.hops >= 3 ? 'bg-red-500/10 text-red-500 border-red-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                                    {chain.hops} hops
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-muted-foreground">{chain.status_code}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}

        {/* ── Internal Linking ── */}
        {tab === 'internal-linking' && (
          <div className="space-y-4">
            {linkingQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {linkingQuery.isError && (
              <div className="bg-card border border-border rounded-xl p-8 text-center">
                <XCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">Could not load internal linking data. Run a crawl first.</p>
              </div>
            )}
            {linkingQuery.data && (() => {
              const { opportunities, total } = linkingQuery.data
              return (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">{total} linking opportunity{total !== 1 ? 's' : ''}</h3>
                      <p className="text-xs text-muted-foreground mt-0.5">Pages with fewer than 3 incoming internal links that could receive more PageRank.</p>
                    </div>
                  </div>
                  {linkingQuery.data.note && (
                    <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 px-4 py-3">
                      <Info className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-muted-foreground leading-relaxed">{linkingQuery.data.note}</p>
                    </div>
                  )}
                  {total === 0 ? (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                      <Link2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                      <p className="text-sm font-medium text-foreground">No internal linking gaps found</p>
                      <p className="text-xs text-muted-foreground mt-1">All substantial pages have at least 3 incoming internal links.</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {opportunities.map((opp: any, i: number) => (
                        <div key={i} className="bg-card border border-border rounded-xl p-4">
                          <div className="flex items-start justify-between gap-3 mb-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <a href={opp.target_page.url} target="_blank" rel="noopener noreferrer"
                                  className="text-sm text-primary hover:underline font-mono truncate">
                                  {opp.target_page.url}
                                </a>
                              </div>
                              {opp.target_page.title && (
                                <p className="text-xs text-muted-foreground truncate">{opp.target_page.title}</p>
                              )}
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <ScoreBadge score={opp.target_page.seo_score} />
                              <span className="text-xs text-muted-foreground whitespace-nowrap">{opp.target_page.incoming_links} incoming links</span>
                            </div>
                          </div>
                          {opp.suggested_sources.length > 0 && (
                            <div>
                              <p className="text-xs font-semibold text-muted-foreground mb-2">Suggested source pages:</p>
                              <div className="space-y-1">
                                {opp.suggested_sources.slice(0, 3).map((source: any, j: number) => (
                                  <div key={j} className="flex items-center gap-2 text-xs">
                                    <ChevronsRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                                    <a href={source.url} target="_blank" rel="noopener noreferrer"
                                      className="text-primary hover:underline font-mono truncate">
                                      {source.url}
                                    </a>
                                    <span className="text-muted-foreground flex-shrink-0">({source.incoming_links} inbound)</span>
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
              )
            })()}
          </div>
        )}

        {/* ── Coverage Gaps ── */}
        {tab === 'coverage-gaps' && (
          <div className="space-y-6">
            {coverageQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {coverageQuery.isError && (
              <div className="bg-card border border-border rounded-xl p-8 text-center">
                <XCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">Could not load coverage data. Run a crawl first.</p>
              </div>
            )}
            {coverageQuery.data && (() => {
              const { gaps, summary } = coverageQuery.data
              return (
                <div className="space-y-6">
                  {/* Summary */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: 'Crawled URLs', value: summary.total_crawled_urls },
                      { label: 'GSC Pages Not Crawled', value: summary.gsc_urls_not_crawled, warn: summary.gsc_urls_not_crawled > 0 },
                      { label: 'Non-200 Pages', value: summary.non_200_count, warn: summary.non_200_count > 0 },
                      { label: 'Noindex Pages', value: summary.noindex_count, warn: false },
                      { label: 'Broken Pages', value: summary.broken_pages ?? 0, warn: (summary.broken_pages ?? 0) > 0 },
                      { label: 'Server Errors', value: summary.server_errors ?? 0, warn: (summary.server_errors ?? 0) > 0 },
                    ].map((c) => (
                      <div key={c.label} className="bg-card border border-border rounded-xl p-4">
                        <p className="text-xs text-muted-foreground mb-1">{c.label}</p>
                        <p className={`text-2xl font-bold ${c.warn ? 'text-amber-500' : 'text-foreground'}`}>{c.value}</p>
                      </div>
                    ))}
                  </div>

                  {/* GSC not crawled */}
                  {gaps.gsc_not_crawled.length > 0 && (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="px-4 py-3 border-b border-border bg-muted/30">
                        <h3 className="text-sm font-semibold text-foreground">Google Sees These Pages — AutoSEO Didn't Crawl Them</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">High-impression pages not covered by the last crawl. Check sitemap and internal links.</p>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/20">
                              <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">URL</th>
                              <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">Impressions</th>
                              <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">Clicks</th>
                            </tr>
                          </thead>
                          <tbody>
                            {gaps.gsc_not_crawled.slice(0, 20).map((row: any, i: number) => (
                              <tr key={i} className="border-b border-border/50 hover:bg-muted/20">
                                <td className="px-4 py-2.5">
                                  <a href={row.url} target="_blank" rel="noopener noreferrer"
                                    className="text-xs text-primary hover:underline font-mono">
                                    {row.url}
                                  </a>
                                </td>
                                <td className="px-4 py-2.5 text-foreground">{row.impressions.toLocaleString()}</td>
                                <td className="px-4 py-2.5 text-foreground">{row.clicks.toLocaleString()}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Non-200 pages */}
                  {gaps.non_200_pages.length > 0 && (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="px-4 py-3 border-b border-border bg-muted/30">
                        <h3 className="text-sm font-semibold text-foreground">Non-200 Pages ({gaps.non_200_pages.length})</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">Pages returning error or redirect status codes that may need attention.</p>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/20">
                              <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">URL</th>
                              <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">Status</th>
                              <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">Redirect</th>
                            </tr>
                          </thead>
                          <tbody>
                            {gaps.non_200_pages.slice(0, 20).map((row: any, i: number) => (
                              <tr key={i} className="border-b border-border/50 hover:bg-muted/20">
                                <td className="px-4 py-2.5">
                                  <a href={row.url} target="_blank" rel="noopener noreferrer"
                                    className="text-xs text-primary hover:underline font-mono">
                                    {row.url}
                                  </a>
                                </td>
                                <td className="px-4 py-2.5">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border ${
                                    row.status_code >= 500 ? 'bg-red-500/10 text-red-500 border-red-500/20'
                                    : row.status_code >= 400 ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                                    : 'bg-blue-500/10 text-blue-500 border-blue-500/20'
                                  }`}>
                                    {row.status_code}
                                  </span>
                                </td>
                                <td className="px-4 py-2.5 text-xs text-muted-foreground font-mono truncate max-w-xs">
                                  {row.redirect_url || '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Noindex pages */}
                  {(gaps.noindex_pages ?? []).length > 0 && (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="px-4 py-3 border-b border-border bg-muted/30">
                        <h3 className="text-sm font-semibold text-foreground">Noindex Pages ({gaps.noindex_pages.length})</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">Pages intentionally or accidentally excluded from Google's index.</p>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/20">
                              <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">URL</th>
                              <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">Source</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(gaps.noindex_pages as any[]).slice(0, 20).map((row: any, i: number) => (
                              <tr key={i} className="border-b border-border/50 hover:bg-muted/20">
                                <td className="px-4 py-2.5">
                                  <a href={row.url ?? row} target="_blank" rel="noopener noreferrer"
                                    className="text-xs text-primary hover:underline font-mono">
                                    {row.url ?? row}
                                  </a>
                                </td>
                                <td className="px-4 py-2.5 text-xs text-muted-foreground">{row.source ?? '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  {/* By status code breakdown */}
                  {summary.by_status_code && Object.keys(summary.by_status_code).length > 0 && (
                    <div className="bg-card border border-border rounded-xl p-4">
                      <h3 className="text-sm font-semibold text-foreground mb-3">Pages by Status Code</h3>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(summary.by_status_code as Record<string, number>).map(([code, count]) => (
                          <span key={code} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${
                            Number(code) >= 500 ? 'bg-red-500/10 text-red-500 border-red-500/20'
                            : Number(code) >= 400 ? 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                            : Number(code) >= 300 ? 'bg-blue-500/10 text-blue-500 border-blue-500/20'
                            : 'bg-green-500/10 text-green-500 border-green-500/20'
                          }`}>
                            <span>{code}</span><span className="opacity-70">·</span><span>{count}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {coverageQuery.data.note && (
                    <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 px-4 py-3">
                      <Info className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-muted-foreground leading-relaxed">{coverageQuery.data.note}</p>
                    </div>
                  )}
                  {gaps.gsc_not_crawled.length === 0 && gaps.non_200_pages.length === 0 && (
                    <div className="bg-card border border-border rounded-xl p-8 text-center">
                      <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
                      <p className="text-sm font-medium text-foreground">No coverage gaps found</p>
                      <p className="text-xs text-muted-foreground mt-1">All pages AutoSEO crawled return 200, and Search Console data aligns with the crawl.</p>
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}

        {/* ── Health Trends ── */}
        {tab === 'health-trends' && (
          <div className="space-y-4">
            {healthTrendsQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {healthTrendsQuery.data && (() => {
              const crawls: any[] = healthTrendsQuery.data.crawls ?? []
              const summary = healthTrendsQuery.data.summary ?? {}
              return (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="rounded-xl border border-border bg-card p-4 text-center">
                      <p className="text-2xl font-bold text-foreground">{summary.total_crawls ?? '—'}</p>
                      <p className="text-xs text-muted-foreground mt-1">Total crawls</p>
                    </div>
                    <div className="rounded-xl border border-border bg-card p-4 text-center">
                      <p className="text-2xl font-bold text-foreground">{summary.completed_crawls ?? '—'}</p>
                      <p className="text-xs text-muted-foreground mt-1">Completed</p>
                    </div>
                    <div className="rounded-xl border border-border bg-card p-4 text-center">
                      <p className={`text-2xl font-bold ${summary.avg_seo_score >= 80 ? 'text-green-500' : summary.avg_seo_score >= 60 ? 'text-amber-500' : 'text-red-500'}`}>{summary.avg_seo_score != null ? Math.round(summary.avg_seo_score) : '—'}</p>
                      <p className="text-xs text-muted-foreground mt-1">Avg SEO score</p>
                    </div>
                  </div>
                  {crawls.length > 0 && (
                    <div className="rounded-xl border border-border bg-card overflow-hidden">
                      <div className="px-5 py-3 border-b border-border">
                        <h3 className="text-sm font-semibold text-foreground">Crawl history</h3>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-border bg-muted/20">
                              <th className="text-left px-4 py-2.5 text-muted-foreground font-medium">Date</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">SEO Score</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">Pages</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">URLs found</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">Issues</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">Duration</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {crawls.map((c: any) => (
                              <tr key={c.crawl_id} className="hover:bg-muted/20 transition-colors">
                                <td className="px-4 py-2.5 text-muted-foreground">{new Date(c.completed_at || c.created_at).toLocaleDateString()}</td>
                                <td className="px-4 py-2.5 text-center"><ScoreBadge score={c.seo_score} /></td>
                                <td className="px-4 py-2.5 text-center text-foreground">{c.pages_crawled}</td>
                                <td className="px-4 py-2.5 text-center text-foreground">{c.urls_discovered}</td>
                                <td className="px-4 py-2.5 text-center text-foreground">{c.issues_found}</td>
                                <td className="px-4 py-2.5 text-center text-muted-foreground">{c.duration_ms != null ? `${(c.duration_ms / 1000).toFixed(1)}s` : '—'}</td>
                                <td className="px-4 py-2.5 text-center">
                                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${c.status === 'completed' ? 'bg-green-500/10 text-green-500 border-green-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                                    {c.status}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  {crawls.length === 0 && (
                    <div className="bg-card border border-dashed border-border rounded-xl p-8 text-center">
                      <BarChart2 className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">No crawl history yet. Run your first crawl to populate health trends.</p>
                    </div>
                  )}
                  {/* Crawl diff panel */}
                  {crawlDiffQuery.data && (() => {
                    const diff = crawlDiffQuery.data
                    const s = diff.summary ?? {}
                    return (
                      <div className="rounded-xl border border-border bg-card overflow-hidden">
                        <div className="px-5 py-3 border-b border-border flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <ArrowUpDown className="h-4 w-4 text-primary" />
                            <h3 className="text-sm font-semibold text-foreground">Latest Crawl Diff</h3>
                          </div>
                          {diff.current_started_at && diff.previous_started_at && (
                            <p className="text-[10px] text-muted-foreground">
                              {new Date(diff.previous_started_at).toLocaleDateString()} → {new Date(diff.current_started_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                        <div className="p-4 grid grid-cols-3 md:grid-cols-6 gap-3">
                          <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-3 text-center">
                            <p className="text-lg font-bold text-green-400">{s.new_pages_count ?? 0}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">New pages</p>
                          </div>
                          <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-center">
                            <p className="text-lg font-bold text-red-400">{s.removed_pages_count ?? 0}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Removed</p>
                          </div>
                          <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-3 text-center">
                            <p className="text-lg font-bold text-green-400">{s.score_improved_count ?? 0}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Score ↑</p>
                          </div>
                          <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-center">
                            <p className="text-lg font-bold text-red-400">{s.score_declined_count ?? 0}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Score ↓</p>
                          </div>
                          <div className="rounded-lg bg-muted/30 p-3 text-center">
                            <p className="text-lg font-bold text-foreground">{s.title_changed_count ?? 0}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Title changes</p>
                          </div>
                          <div className={`rounded-lg p-3 text-center ${(s.site_score_delta ?? 0) > 0 ? 'bg-green-500/10 border border-green-500/20' : (s.site_score_delta ?? 0) < 0 ? 'bg-red-500/10 border border-red-500/20' : 'bg-muted/30'}`}>
                            <p className={`text-lg font-bold ${(s.site_score_delta ?? 0) > 0 ? 'text-green-400' : (s.site_score_delta ?? 0) < 0 ? 'text-red-400' : 'text-foreground'}`}>
                              {(s.site_score_delta ?? 0) > 0 ? '+' : ''}{s.site_score_delta ?? 0}
                            </p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">Score delta</p>
                          </div>
                        </div>
                        {(diff.new_pages?.length > 0 || diff.removed_pages?.length > 0 || diff.score_improved?.length > 0 || diff.score_declined?.length > 0 || diff.title_changed?.length > 0) && (
                          <div className="px-5 pb-4 grid md:grid-cols-2 gap-3">
                            {diff.new_pages?.length > 0 && (
                              <div>
                                <p className="text-[10px] font-semibold text-green-400 uppercase tracking-wider mb-1">New pages ({diff.new_pages.length})</p>
                                {(diff.new_pages as string[]).slice(0, 3).map((url: string, i: number) => (
                                  <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-primary hover:underline truncate block font-mono">{url}</a>
                                ))}
                              </div>
                            )}
                            {diff.removed_pages?.length > 0 && (
                              <div>
                                <p className="text-[10px] font-semibold text-red-400 uppercase tracking-wider mb-1">Removed pages ({diff.removed_pages.length})</p>
                                {(diff.removed_pages as string[]).slice(0, 3).map((url: string, i: number) => (
                                  <p key={i} className="text-[10px] text-muted-foreground/60 line-through truncate font-mono">{url}</p>
                                ))}
                              </div>
                            )}
                            {diff.score_improved?.length > 0 && (
                              <div>
                                <p className="text-[10px] font-semibold text-green-400 uppercase tracking-wider mb-1">Score improved ({diff.score_improved.length})</p>
                                {(diff.score_improved as any[]).slice(0, 3).map((p: any, i: number) => (
                                  <div key={i} className="mb-1">
                                    <span className="text-[10px] text-muted-foreground font-mono truncate block">{p.url || p}</span>
                                    {p.from != null && p.to != null && (
                                      <span className="text-[9px] text-muted-foreground/70">
                                        <span className="text-red-400/70">{p.from}</span>
                                        <span className="mx-0.5">→</span>
                                        <span className="text-green-400">{p.to}</span>
                                        {p.delta != null && <span className="ml-1 text-green-400 font-semibold">+{p.delta}</span>}
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                            {diff.score_declined?.length > 0 && (
                              <div>
                                <p className="text-[10px] font-semibold text-red-400 uppercase tracking-wider mb-1">Score declined ({diff.score_declined.length})</p>
                                {(diff.score_declined as any[]).slice(0, 3).map((p: any, i: number) => (
                                  <div key={i} className="mb-1">
                                    <span className="text-[10px] text-muted-foreground font-mono truncate block">{p.url || p}</span>
                                    {p.from != null && p.to != null && (
                                      <span className="text-[9px] text-muted-foreground/70">
                                        <span className="text-green-400/70">{p.from}</span>
                                        <span className="mx-0.5">→</span>
                                        <span className="text-red-400">{p.to}</span>
                                        {p.delta != null && <span className="ml-1 text-red-400 font-semibold">{p.delta}</span>}
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                            {diff.title_changed?.length > 0 && (
                              <div className="md:col-span-2">
                                <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-1">Title changes ({diff.title_changed.length})</p>
                                {(diff.title_changed as any[]).slice(0, 3).map((t: any, i: number) => (
                                  <div key={i} className="text-[10px] text-muted-foreground mb-1">
                                    <span className="font-mono text-foreground/60 truncate block">{t.url}</span>
                                    <span className="line-through text-red-400/60">{t.from}</span>
                                    <span className="mx-1">→</span>
                                    <span className="text-green-400/70">{t.to}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })()}
                </div>
              )
            })()}
          </div>
        )}

        {/* ── PageSpeed Trend ── */}
        {tab === 'pagespeed-trend' && (
          <div className="space-y-4">
            {pagespeedTrendQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {pagespeedTrendQuery.data && (() => {
              const data = pagespeedTrendQuery.data
              const trend: any[] = data.trend ?? []
              const latest = data.latest ?? {}
              const thresholds = data.thresholds ?? {}
              return (
                <div className="space-y-4">
                  {data.note && (
                    <div className="flex items-start gap-2 rounded-lg border border-blue-500/20 bg-blue-500/10 px-4 py-3">
                      <Info className="h-3.5 w-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-blue-200 leading-relaxed">{data.note}</p>
                    </div>
                  )}
                  <div className="flex items-center gap-2 flex-wrap">
                    {data.strategy && (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full border border-border bg-muted/40 text-[11px] font-semibold text-foreground capitalize">
                        Strategy: {data.strategy}
                      </span>
                    )}
                    {data.total_days != null && (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full border border-border bg-muted/40 text-[11px] text-muted-foreground">
                        {data.total_days > 0 ? `${data.total_days} days of history` : 'No history yet'}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {data.cwv_pass != null && (
                      <div className="rounded-xl border border-border bg-card p-4 text-center">
                        <p className={`text-2xl font-bold ${data.cwv_pass ? 'text-green-500' : 'text-red-500'}`}>{data.cwv_pass ? '✓ Pass' : '✗ Fail'}</p>
                        <p className="text-xs text-muted-foreground mt-1">Core Web Vitals</p>
                      </div>
                    )}
                    {latest.lcp_ms != null && (
                      <div className="rounded-xl border border-border bg-card p-4 text-center">
                        <p className={`text-2xl font-bold ${latest.lcp_ms <= thresholds.lcp_good_ms ? 'text-green-500' : latest.lcp_ms <= thresholds.lcp_needs_improvement_ms ? 'text-amber-500' : 'text-red-500'}`}>{latest.lcp_ms}ms</p>
                        <p className="text-xs text-muted-foreground mt-1">Latest LCP</p>
                      </div>
                    )}
                    {latest.performance_score != null && (
                      <div className="rounded-xl border border-border bg-card p-4 text-center">
                        <p className={`text-2xl font-bold ${latest.performance_score >= 90 ? 'text-green-500' : latest.performance_score >= 50 ? 'text-amber-500' : 'text-red-500'}`}>{Math.round(latest.performance_score)}</p>
                        <p className="text-xs text-muted-foreground mt-1">Perf score</p>
                      </div>
                    )}
                    {data.total_days != null && (
                      <div className="rounded-xl border border-border bg-card p-4 text-center">
                        <p className="text-2xl font-bold text-foreground">{data.total_days}</p>
                        <p className="text-xs text-muted-foreground mt-1">Days tracked</p>
                      </div>
                    )}
                  </div>
                  <div className="rounded-xl border border-border bg-card p-4">
                    <h3 className="text-sm font-semibold text-foreground mb-3">CWV Thresholds</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      <div className="space-y-1">
                        <p className="font-semibold text-foreground">LCP</p>
                        <p className="text-muted-foreground">Good: ≤ {thresholds.lcp_good_ms}ms</p>
                        <p className="text-muted-foreground">Needs improvement: ≤ {thresholds.lcp_needs_improvement_ms}ms</p>
                      </div>
                      <div className="space-y-1">
                        <p className="font-semibold text-foreground">INP</p>
                        <p className="text-muted-foreground">Good: ≤ {thresholds.inp_good_ms}ms</p>
                        <p className="text-muted-foreground">Needs improvement: ≤ {thresholds.inp_needs_improvement_ms}ms</p>
                      </div>
                      <div className="space-y-1">
                        <p className="font-semibold text-foreground">CLS</p>
                        <p className="text-muted-foreground">Good: ≤ {thresholds.cls_good}</p>
                        <p className="text-muted-foreground">Needs improvement: ≤ {thresholds.cls_needs_improvement}</p>
                      </div>
                    </div>
                  </div>
                  {trend.length > 0 && (
                    <div className="rounded-xl border border-border bg-card overflow-hidden">
                      <div className="px-5 py-3 border-b border-border">
                        <h3 className="text-sm font-semibold text-foreground">Core Web Vitals over time</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">Daily averages across all tested pages — most recent last.</p>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-border bg-muted/20">
                              <th className="text-left px-4 py-2.5 text-muted-foreground font-medium">Date</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">Perf</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">LCP</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">INP</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium">CLS</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium hidden md:table-cell">TTFB</th>
                              <th className="text-center px-4 py-2.5 text-muted-foreground font-medium hidden lg:table-cell">Pages</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {trend.map((row: any, i: number) => {
                              const lcpGood = row.avg_lcp_ms != null && row.avg_lcp_ms <= thresholds.lcp_good_ms
                              const lcpWarn = row.avg_lcp_ms != null && row.avg_lcp_ms <= thresholds.lcp_needs_improvement_ms
                              const inpGood = row.avg_inp_ms != null && row.avg_inp_ms <= thresholds.inp_good_ms
                              const inpWarn = row.avg_inp_ms != null && row.avg_inp_ms <= thresholds.inp_needs_improvement_ms
                              const clsGood = row.avg_cls_score != null && row.avg_cls_score <= thresholds.cls_good
                              const clsWarn = row.avg_cls_score != null && row.avg_cls_score <= thresholds.cls_needs_improvement
                              const perfScore = row.avg_performance_score
                              return (
                                <tr key={i} className="hover:bg-muted/20 transition-colors">
                                  <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">{row.day ?? '—'}</td>
                                  <td className="px-4 py-2.5 text-center">
                                    {perfScore != null ? (
                                      <span className={`font-bold ${perfScore >= 90 ? 'text-green-400' : perfScore >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                                        {perfScore}
                                      </span>
                                    ) : '—'}
                                  </td>
                                  <td className="px-4 py-2.5 text-center">
                                    {row.avg_lcp_ms != null ? (
                                      <span className={lcpGood ? 'text-green-400' : lcpWarn ? 'text-amber-400' : 'text-red-400'}>
                                        {row.avg_lcp_ms}ms
                                      </span>
                                    ) : '—'}
                                  </td>
                                  <td className="px-4 py-2.5 text-center">
                                    {row.avg_inp_ms != null ? (
                                      <span className={inpGood ? 'text-green-400' : inpWarn ? 'text-amber-400' : 'text-red-400'}>
                                        {row.avg_inp_ms}ms
                                      </span>
                                    ) : '—'}
                                  </td>
                                  <td className="px-4 py-2.5 text-center">
                                    {row.avg_cls_score != null ? (
                                      <span className={clsGood ? 'text-green-400' : clsWarn ? 'text-amber-400' : 'text-red-400'}>
                                        {row.avg_cls_score.toFixed(3)}
                                      </span>
                                    ) : '—'}
                                  </td>
                                  <td className="px-4 py-2.5 text-center text-muted-foreground hidden md:table-cell">
                                    {row.avg_ttfb_ms != null ? `${row.avg_ttfb_ms}ms` : '—'}
                                  </td>
                                  <td className="px-4 py-2.5 text-center text-muted-foreground hidden lg:table-cell">
                                    {row.pages_tested ?? '—'}
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  {trend.length === 0 && (
                    <div className="bg-card border border-dashed border-border rounded-xl p-8 text-center">
                      <BarChart2 className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">No PageSpeed trend data yet. Run PageSpeed checks to populate this view.</p>
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}

        {/* ── Crawl Budget ── */}
        {tab === 'crawl-budget' && (
          <div className="space-y-4">
            {crawlBudgetQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
            {crawlBudgetQuery.data && (() => {
              const cb = crawlBudgetQuery.data
              const byBot = cb.by_bot ?? {}
              const byStatus = cb.by_status ?? {}
              const notCrawledByAutoseo: string[] = cb.googlebot_not_crawled_by_autoseo ?? []
              const notSeenByGooglebot: string[] = cb.high_value_not_seen_by_googlebot ?? []
              const recommendations: string[] = cb.recommendations ?? []
              return (
                <div className="space-y-4">
                  {cb.message && (
                    <div className="rounded-xl border border-border bg-muted/30 p-4 flex items-start gap-3">
                      <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-muted-foreground">{cb.message}</p>
                    </div>
                  )}

                  <div className="grid sm:grid-cols-2 gap-4">
                    {Object.keys(byBot).length > 0 && (
                      <div className="bg-card border border-border rounded-xl p-5">
                        <h3 className="text-sm font-semibold text-foreground mb-3">Crawls by Bot</h3>
                        <div className="space-y-2">
                          {Object.entries(byBot as Record<string, number>).map(([bot, count]) => (
                            <div key={bot} className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground capitalize">{bot.replace(/_/g, ' ')}</span>
                              <span className="font-semibold text-foreground">{count.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {Object.keys(byStatus).length > 0 && (
                      <div className="bg-card border border-border rounded-xl p-5">
                        <h3 className="text-sm font-semibold text-foreground mb-3">Crawls by Status Code</h3>
                        <div className="space-y-2">
                          {Object.entries(byStatus as Record<string, number>).map(([code, count]) => (
                            <div key={code} className="flex items-center justify-between text-sm">
                              <span className={`font-mono px-1.5 py-0.5 rounded text-xs ${
                                code.startsWith('2') ? 'bg-green-500/10 text-green-400' :
                                code.startsWith('3') ? 'bg-blue-500/10 text-blue-400' :
                                code.startsWith('4') ? 'bg-amber-500/10 text-amber-400' :
                                'bg-red-500/10 text-red-400'
                              }`}>{code}</span>
                              <span className="font-semibold text-foreground">{count.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {recommendations.length > 0 && (
                    <div className="bg-card border border-amber-500/20 rounded-xl p-5">
                      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-500" />
                        Recommendations
                      </h3>
                      <ul className="space-y-2">
                        {recommendations.map((rec, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                            <ChevronsRight className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {notCrawledByAutoseo.length > 0 && (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-foreground">Googlebot URLs not in AutoSEO crawl</h3>
                        <span className="text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full">{notCrawledByAutoseo.length}</span>
                      </div>
                      <div className="divide-y divide-border max-h-64 overflow-y-auto">
                        {notCrawledByAutoseo.map((url, i) => (
                          <div key={i} className="flex items-center gap-2 px-5 py-2.5">
                            <Globe className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                            <a href={url} target="_blank" rel="noopener noreferrer"
                              className="text-xs text-muted-foreground hover:text-primary truncate flex-1 transition-colors">{url}</a>
                            <button onClick={() => copyUrl(url)} className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors flex-shrink-0">
                              {copiedUrl === url ? <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {notSeenByGooglebot.length > 0 && (
                    <div className="bg-card border border-border rounded-xl overflow-hidden">
                      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-foreground">High-value pages not seen by Googlebot</h3>
                        <span className="text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded-full">{notSeenByGooglebot.length}</span>
                      </div>
                      <div className="divide-y divide-border max-h-64 overflow-y-auto">
                        {notSeenByGooglebot.map((url, i) => (
                          <div key={i} className="flex items-center gap-2 px-5 py-2.5">
                            <Globe className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                            <a href={url} target="_blank" rel="noopener noreferrer"
                              className="text-xs text-muted-foreground hover:text-primary truncate flex-1 transition-colors">{url}</a>
                            <button onClick={() => copyUrl(url)} className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors flex-shrink-0">
                              {copiedUrl === url ? <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {notCrawledByAutoseo.length === 0 && notSeenByGooglebot.length === 0 && recommendations.length === 0 && Object.keys(byBot).length === 0 && (
                    <div className="bg-card border border-dashed border-border rounded-xl p-10 text-center">
                      <BarChart2 className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">No crawl budget data yet. Import server logs or connect Google Search Console to populate this view.</p>
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}

        {/* ── AI Visibility ── */}
        {tab === 'ai-visibility' && (
          <div className="space-y-4">
            {/* Info banner */}
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 flex items-start gap-3">
              <Brain className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                {aiVisibilityQuery.data?.label && (
                  <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-1">{aiVisibilityQuery.data.label}</p>
                )}
                <p className="text-sm text-muted-foreground">
                  {aiVisibilityQuery.data?.message ?? 'Scores how well your crawled pages are structured for AI answer retrieval — no external LLM queries are made.'}
                </p>
                {aiVisibilityQuery.data?.readiness && (
                  <span className="inline-flex items-center mt-1.5 px-2 py-0.5 rounded text-[10px] font-semibold border bg-blue-500/10 text-blue-400 border-blue-500/20">
                    {aiVisibilityQuery.data.readiness.replace(/_/g, ' ')}
                  </span>
                )}
              </div>
            </div>

            {/* Run new analysis */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <SendHorizontal className="h-4 w-4 text-primary" />
                Run New AI Visibility Analysis
              </h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  placeholder="e.g. Which SEO tools help with technical fixes?"
                  className="flex-1 h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
                <button
                  onClick={() => aiPrompt.trim().length >= 5 && runAiVisibility.mutate({ prompt: aiPrompt.trim() })}
                  disabled={runAiVisibility.isPending || aiPrompt.trim().length < 5}
                  className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-50 hover:opacity-90 transition-opacity flex items-center gap-2">
                  {runAiVisibility.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                  Analyze
                </button>
              </div>
            </div>

            {aiVisibilityQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}

            {/* Runs list */}
            {aiVisibilityQuery.data && (() => {
              const runs: any[] = aiVisibilityQuery.data.runs ?? []
              if (runs.length === 0) return (
                <div className="bg-card border border-dashed border-border rounded-xl p-10 text-center">
                  <Brain className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No AI visibility analyses yet. Enter a prompt above to run the first one.</p>
                </div>
              )
              return (
                <div className="bg-card border border-border rounded-xl overflow-hidden">
                  <div className="px-5 py-3 border-b border-border">
                    <h3 className="text-sm font-semibold text-foreground">Analysis Runs</h3>
                  </div>
                  <div className="divide-y divide-border">
                    {runs.map((run: any) => {
                      const open = expandedRunId === run.id
                      const vis = run.visibility_score ?? 0
                      const ent = run.entity_score ?? 0
                      const cit = run.citation_score ?? 0
                      const scoreClass = (s: number) => s >= 0.7 ? 'text-green-500 bg-green-500/10 border-green-500/20' : s >= 0.4 ? 'text-amber-500 bg-amber-500/10 border-amber-500/20' : 'text-red-500 bg-red-500/10 border-red-500/20'
                      return (
                        <div key={run.id}>
                          <button
                            onClick={() => setExpandedRunId(open ? null : run.id)}
                            className="w-full flex items-start gap-4 px-5 py-4 hover:bg-muted/40 transition-colors text-left">
                            <Brain className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-foreground truncate">{run.prompt}</p>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {run.created_at ? new Date(run.created_at).toLocaleDateString() : ''} · {run.status}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold border ${scoreClass(vis)}`}>V {Math.round(vis * 100)}</span>
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold border ${scoreClass(ent)}`}>E {Math.round(ent * 100)}</span>
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold border ${scoreClass(cit)}`}>C {Math.round(cit * 100)}</span>
                              <span className="text-muted-foreground text-xs">{open ? '▲' : '▶'}</span>
                            </div>
                          </button>
                          {open && (
                            <div className="px-5 pb-5 space-y-4 border-t border-border/50 bg-muted/20">
                              <div className="grid sm:grid-cols-3 gap-3 pt-4">
                                {[
                                  { label: 'Visibility Score', value: vis, desc: 'Overall AI answer-readiness' },
                                  { label: 'Entity Score', value: ent, desc: 'Entity presence in content' },
                                  { label: 'Citation Score', value: cit, desc: 'Structured data citation signals' },
                                ].map(({ label, value, desc }) => (
                                  <div key={label} className="bg-card border border-border rounded-lg p-3 text-center">
                                    <p className="text-2xl font-bold text-foreground">{Math.round(value * 100)}</p>
                                    <p className="text-xs font-semibold text-foreground mt-0.5">{label}</p>
                                    <p className="text-[10px] text-muted-foreground mt-0.5">{desc}</p>
                                  </div>
                                ))}
                              </div>
                              {run.missing_context?.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2 flex items-center gap-1.5">
                                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" /> Missing Context
                                  </p>
                                  <ul className="space-y-1.5">
                                    {run.missing_context.map((item: string, i: number) => (
                                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                        <ChevronsRight className="h-3.5 w-3.5 text-amber-500 flex-shrink-0 mt-0.5" />{item}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {run.recommendations?.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2 flex items-center gap-1.5">
                                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> Recommendations
                                  </p>
                                  <ul className="space-y-1.5">
                                    {run.recommendations.map((rec: string, i: number) => (
                                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                        <ChevronsRight className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />{rec}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {run.competitor_mentions?.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2">Competitor Mentions</p>
                                  <div className="space-y-1.5">
                                    {run.competitor_mentions.map((m: any, i: number) => (
                                      <div key={i} className="flex items-start gap-2 flex-wrap">
                                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border border-border bg-muted text-xs text-muted-foreground flex-shrink-0">
                                          {m.domain ?? m}
                                          {m.status && <span className="text-[9px] opacity-60">{m.status.replace(/_/g, ' ')}</span>}
                                        </span>
                                        {m.note && <span className="text-[10px] text-muted-foreground/70 italic self-center">{m.note}</span>}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {run.evidence && (
                                <div className="rounded-lg bg-muted/30 border border-border/50 p-3 space-y-2">
                                  <p className="text-xs font-semibold text-foreground">Analysis Evidence</p>
                                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                    {run.evidence.pages_scored != null && (
                                      <div className="text-center"><p className="text-lg font-bold text-foreground">{run.evidence.pages_scored}</p><p className="text-[9px] text-muted-foreground">Pages scored</p></div>
                                    )}
                                    {run.evidence.schema_rich_pages != null && (
                                      <div className="text-center"><p className="text-lg font-bold text-foreground">{run.evidence.schema_rich_pages}</p><p className="text-[9px] text-muted-foreground">Schema-rich pages</p></div>
                                    )}
                                    {run.evidence.faq_or_howto_pages != null && (
                                      <div className="text-center"><p className="text-lg font-bold text-foreground">{run.evidence.faq_or_howto_pages}</p><p className="text-[9px] text-muted-foreground">FAQ/HowTo pages</p></div>
                                    )}
                                    {run.evidence.entity_overlap != null && (
                                      <div className="text-center"><p className="text-lg font-bold text-foreground">{(run.evidence.entity_overlap * 100).toFixed(0)}%</p><p className="text-[9px] text-muted-foreground">Entity overlap</p></div>
                                    )}
                                    {run.evidence.prompt_overlap != null && (
                                      <div className="text-center"><p className="text-lg font-bold text-foreground">{(run.evidence.prompt_overlap * 100).toFixed(0)}%</p><p className="text-[9px] text-muted-foreground">Prompt overlap</p></div>
                                    )}
                                  </div>
                                  {(run.evidence.provider_status || run.evidence.provider_note) && (
                                    <div className="border-t border-border/30 pt-2 space-y-1">
                                      {run.evidence.provider_status && (
                                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold border ${run.evidence.provider_status === 'live' ? 'bg-green-500/10 text-green-400 border-green-500/20' : run.evidence.provider_status === 'stub' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-muted border-border text-muted-foreground'}`}>
                                          {run.evidence.provider_status.replace(/_/g, ' ')}
                                        </span>
                                      )}
                                      {run.evidence.provider_note && (
                                        <p className="text-[10px] text-muted-foreground/70 italic">{run.evidence.provider_note}</p>
                                      )}
                                    </div>
                                  )}
                                  {run.evidence.pending_issue_counts && Object.keys(run.evidence.pending_issue_counts).some((k) => run.evidence.pending_issue_counts[k] > 0) && (
                                    <div className="border-t border-border/30 pt-2">
                                      <p className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">Pending issues affecting score</p>
                                      <div className="flex flex-wrap gap-1.5">
                                        {Object.entries(run.evidence.pending_issue_counts as Record<string, number>).filter(([, v]) => v > 0).map(([k, v]) => (
                                          <span key={k} className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                            {k.replace(/_/g, ' ')}: {v}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })()}
          </div>
        )}

        {/* ── Content Briefs ── */}
        {tab === 'content-briefs' && (
          <div className="space-y-4">
            {/* Create brief form */}
            <div className="bg-card border border-border rounded-xl p-5 space-y-3">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                Generate Content Refresh Brief
              </h3>
              <div className="grid sm:grid-cols-2 gap-2">
                <input
                  type="url"
                  value={briefPageUrl}
                  onChange={(e) => setBriefPageUrl(e.target.value)}
                  placeholder="https://example.com/page-to-refresh"
                  className="h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
                <input
                  type="text"
                  value={briefKeyword}
                  onChange={(e) => setBriefKeyword(e.target.value)}
                  placeholder="Target keyword (optional)"
                  className="h-9 rounded-lg border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>
              <button
                onClick={() => briefPageUrl.trim().length >= 8 && createBrief.mutate({ site_id: id, page_url: briefPageUrl.trim(), target_keyword: briefKeyword.trim() || undefined })}
                disabled={createBrief.isPending || briefPageUrl.trim().length < 8}
                className="h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-50 hover:opacity-90 transition-opacity flex items-center gap-2">
                {createBrief.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                Generate Brief
              </button>
            </div>

            {contentBriefsQuery.isLoading && <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}

            {contentBriefsQuery.data && (() => {
              const briefs: any[] = contentBriefsQuery.data.briefs ?? []
              if (briefs.length === 0) return (
                <div className="bg-card border border-dashed border-border rounded-xl p-10 text-center">
                  <FileText className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No content briefs yet. Enter a page URL above to generate the first brief.</p>
                </div>
              )
              const STATUS_STYLE: Record<string, string> = {
                brief_ready: 'bg-green-500/10 text-green-400 border-green-500/20',
                generating: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
                pr_open: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
                failed: 'bg-red-500/10 text-red-400 border-red-500/20',
              }
              return (
                <div className="bg-card border border-border rounded-xl overflow-hidden">
                  <div className="px-5 py-3 border-b border-border flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">Content Briefs</h3>
                    <span className="text-xs text-muted-foreground">{contentBriefsQuery.data.total} brief{contentBriefsQuery.data.total !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="divide-y divide-border">
                    {briefs.map((brief: any) => {
                      const open = expandedBriefId === brief.id
                      const statusCls = STATUS_STYLE[brief.status] ?? 'bg-muted text-muted-foreground border-border'
                      const b = brief.brief ?? {}
                      return (
                        <div key={brief.id}>
                          <button
                            onClick={() => setExpandedBriefId(open ? null : brief.id)}
                            className="w-full flex items-start gap-4 px-5 py-4 hover:bg-muted/40 transition-colors text-left">
                            <FileText className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-foreground truncate">{brief.title || brief.page_url}</p>
                              <p className="text-xs text-muted-foreground mt-0.5 truncate">{brief.page_url}</p>
                              {brief.target_keyword && (
                                <span className="inline-flex items-center mt-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary/10 text-primary border border-primary/20">
                                  {brief.target_keyword}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold ${statusCls}`}>
                                {brief.status?.replace(/_/g, ' ')}
                              </span>
                              <span className="text-muted-foreground text-xs">{open ? '▲' : '▶'}</span>
                            </div>
                          </button>
                          {open && (
                            <div className="px-5 pb-5 border-t border-border/50 bg-muted/20 space-y-4 pt-4">
                              {brief.github_pr_url && (
                                <a href={brief.github_pr_url} target="_blank" rel="noopener noreferrer"
                                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-violet-500/20 bg-violet-500/10 text-xs font-medium text-violet-400 hover:opacity-80 transition-opacity">
                                  <GitPullRequest className="h-3.5 w-3.5" />
                                  View GitHub PR
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              )}
                              {b.current_state && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2">Current State</p>
                                  <div className="grid sm:grid-cols-2 gap-2 text-xs">
                                    {b.current_state.title && <div className="bg-card border border-border rounded-lg p-2"><span className="text-muted-foreground">Title: </span><span className="text-foreground">{b.current_state.title}</span></div>}
                                    {b.current_state.word_count != null && <div className="bg-card border border-border rounded-lg p-2"><span className="text-muted-foreground">Word count: </span><span className="text-foreground font-semibold">{b.current_state.word_count?.toLocaleString()}</span></div>}
                                    {b.current_state.meta_description && <div className="bg-card border border-border rounded-lg p-2 col-span-2"><span className="text-muted-foreground">Meta: </span><span className="text-foreground">{b.current_state.meta_description}</span></div>}
                                    {b.current_state.schema_types?.length > 0 && <div className="bg-card border border-border rounded-lg p-2"><span className="text-muted-foreground">Schema: </span><span className="text-foreground">{(b.current_state.schema_types as string[]).join(', ')}</span></div>}
                                  </div>
                                </div>
                              )}
                              {b.impact && Object.values(b.impact as Record<string, number>).some(v => v > 0) && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2">Page Impact Signals</p>
                                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                    {[
                                      { key: 'gsc_clicks', label: 'GSC Clicks' },
                                      { key: 'gsc_impressions', label: 'Impressions' },
                                      { key: 'ga_sessions', label: 'GA Sessions' },
                                      { key: 'gsc_position', label: 'Avg Position' },
                                      { key: 'gsc_ctr', label: 'GSC CTR', pct: true },
                                      { key: 'ga_revenue', label: 'GA Revenue', dollar: true },
                                      { key: 'ga_key_events', label: 'Key Events' },
                                    ].map(({ key, label, pct, dollar }: any) => b.impact[key] != null && b.impact[key] > 0 ? (
                                      <div key={key} className="bg-card border border-border rounded-lg p-2 text-center">
                                        <p className="text-sm font-bold text-foreground">
                                          {pct ? `${(b.impact[key] * 100).toFixed(1)}%` : dollar ? `$${Number(b.impact[key]).toFixed(2)}` : Number(b.impact[key]).toLocaleString(undefined, { maximumFractionDigits: 1 })}
                                        </p>
                                        <p className="text-[10px] text-muted-foreground">{label}</p>
                                      </div>
                                    ) : null)}
                                  </div>
                                </div>
                              )}
                              {b.metadata_variants && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2">Suggested Metadata Variants</p>
                                  <div className="space-y-2">
                                    {(b.metadata_variants as any[]).map((v: any, i: number) => (
                                      <div key={i} className="bg-card border border-border rounded-lg p-3 text-xs space-y-1">
                                        {v.title && <p><span className="text-muted-foreground">Title: </span><span className="text-foreground">{v.title}</span></p>}
                                        {v.meta_description && <p><span className="text-muted-foreground">Meta: </span><span className="text-foreground">{v.meta_description}</span></p>}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {b.recommended_sections && (b.recommended_sections as any[]).length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2">Recommended Sections</p>
                                  <ul className="space-y-1.5">
                                    {(b.recommended_sections as any[]).map((s: any, i: number) => (
                                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                        <ChevronsRight className="h-3.5 w-3.5 text-primary flex-shrink-0 mt-0.5" />
                                        {typeof s === 'string' ? s : s.heading || s.title || JSON.stringify(s)}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {b.schema_suggestions && (b.schema_suggestions as any[]).length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2">Schema Suggestions</p>
                                  <ul className="space-y-1.5">
                                    {(b.schema_suggestions as any[]).map((s: any, i: number) => (
                                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                        <ChevronsRight className="h-3.5 w-3.5 text-violet-500 flex-shrink-0 mt-0.5" />
                                        {typeof s === 'string' ? s : JSON.stringify(s)}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {!brief.github_pr_url && b.github_pr_steps && (b.github_pr_steps as any[]).length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2 flex items-center gap-1.5">
                                    <GitPullRequest className="h-3.5 w-3.5 text-violet-500" /> GitHub PR Steps
                                  </p>
                                  <ol className="space-y-1.5 list-decimal list-inside">
                                    {(b.github_pr_steps as any[]).map((step: any, i: number) => (
                                      <li key={i} className="text-xs text-muted-foreground">
                                        {typeof step === 'string' ? step : JSON.stringify(step)}
                                      </li>
                                    ))}
                                  </ol>
                                </div>
                              )}
                              {b.generation && (
                                <p className="text-[10px] text-muted-foreground/60 flex flex-wrap items-center gap-1.5">
                                  Generation: {b.generation.mode?.replace(/_/g, ' ')}
                                  {b.generation.tone && ` · tone: ${b.generation.tone}`}
                                  {b.generation.ai_model && ` · ${b.generation.ai_model}`}
                                  {b.generation.ai_configured && !b.generation.fallback_used && ' · AI-powered'}
                                  {b.generation.fallback_used && ' · deterministic fallback'}
                                  {b.generation.suggested_word_count && ` · ~${b.generation.suggested_word_count} words suggested`}
                                  {b.generation.ai_error && <span className="text-red-400/70 ml-1">⚠ {b.generation.ai_error}</span>}
                                </p>
                              )}
                              {b.risk_notes && (b.risk_notes as any[]).length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-foreground mb-2 flex items-center gap-1.5">
                                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" /> Risk Notes
                                  </p>
                                  <ul className="space-y-1.5">
                                    {(b.risk_notes as any[]).map((note: any, i: number) => (
                                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                        <ChevronsRight className="h-3.5 w-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                                        {typeof note === 'string' ? note : JSON.stringify(note)}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              <p className="text-[10px] text-muted-foreground">
                                Created {brief.created_at ? new Date(brief.created_at).toLocaleDateString() : '—'}
                                {brief.updated_at && brief.updated_at !== brief.created_at && ` · Updated ${new Date(brief.updated_at).toLocaleDateString()}`}
                              </p>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })()}
          </div>
        )}

      </motion.div>
    </div>
  )
}
