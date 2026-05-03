import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp, TrendingDown, Minus, BarChart3, AlertTriangle,
  XCircle, Info, Globe, ChevronDown,
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend, ComposedChart,
} from 'recharts'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { useSites } from '@/hooks/use-data'

function useAnalyticsOverview(siteId?: string) {
  return useQuery({
    queryKey: ['analytics', 'overview', siteId],
    queryFn: () => apiClient.get('analytics/overview', { searchParams: siteId ? { site_id: siteId } : {} }).json<any>(),
  })
}

function useScoreHistory(siteId: string, days: number) {
  return useQuery({
    queryKey: ['analytics', 'score-history', siteId, days],
    queryFn: () =>
      apiClient.get('analytics/score-history', { searchParams: { site_id: siteId, days: String(days) } }).json<any>(),
    enabled: !!siteId,
  })
}

function useIssuesTrend(siteId?: string) {
  return useQuery({
    queryKey: ['analytics', 'issues-trend', siteId],
    queryFn: () =>
      apiClient.get('analytics/issues-trend', {
        searchParams: siteId ? { site_id: siteId } : {},
      }).json<any>(),
  })
}

function useSitePerformance(siteId: string) {
  return useQuery({
    queryKey: ['analytics', 'site-performance', siteId],
    queryFn: () =>
      apiClient.get(`sites/${siteId}/analytics/performance`, {
        searchParams: { days: '30' },
      }).json<any>(),
    enabled: !!siteId,
  })
}

const SEVERITY_COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#3b82f6',
}

function StatCard({ label, value, sub, trend, color }: {
  label: string; value: string | number; sub?: string; trend?: number; color: string
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-3">{label}</p>
      <p className="text-3xl font-bold text-foreground tracking-tight mb-1">{value ?? '—'}</p>
      {sub && <p className="text-sm text-muted-foreground">{sub}</p>}
      {trend !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-sm font-medium ${trend > 0 ? 'text-green-500' : trend < 0 ? 'text-red-500' : 'text-muted-foreground'}`}>
          {trend > 0 ? <TrendingUp className="h-3.5 w-3.5" /> : trend < 0 ? <TrendingDown className="h-3.5 w-3.5" /> : <Minus className="h-3.5 w-3.5" />}
          {Math.abs(trend)}% vs last period
        </div>
      )}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-popover border border-border rounded-lg px-3 py-2 shadow-lg text-sm">
      <p className="text-muted-foreground mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="font-semibold">{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const { data: sitesData } = useSites()
  const sites = sitesData?.sites ?? []
  const [selectedSite, setSelectedSite] = useState<string>('')
  const [days, setDays] = useState(30)

  const siteId = selectedSite || sites[0]?.id || ''

  const { data: overview, isLoading: overviewLoading } = useAnalyticsOverview(siteId || undefined)
  const { data: history, isLoading: historyLoading } = useScoreHistory(siteId, days)
  const { data: trend } = useIssuesTrend(siteId || undefined)
  const { data: sitePerf } = useSitePerformance(siteId)

  const scoreData = history?.data ?? []
  const issuesByCategory = trend?.issues_by_category ?? {}
  const categoryData = Object.entries(issuesByCategory).map(([cat, data]: any) => ({
    name: cat.charAt(0).toUpperCase() + cat.slice(1),
    total: data.total,
    critical: data.critical || 0,
    high: data.high || 0,
    medium: data.medium || 0,
    low: data.low || 0,
  })).sort((a, b) => b.total - a.total)

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-0.5">SEO score trends and issue analysis across your sites</p>
        </div>
        <div className="flex items-center gap-3">
          {sites.length > 0 && (
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <select
                value={selectedSite}
                onChange={e => setSelectedSite(e.target.value)}
                className="h-9 pl-9 pr-8 rounded-lg border border-border bg-background text-sm text-foreground appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30"
              >
                <option value="">All Sites</option>
                {sites.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            </div>
          )}
          <div className="flex rounded-lg border border-border overflow-hidden">
            {[7, 30, 90].map(d => (
              <button key={d}
                onClick={() => setDays(d)}
                className={`h-9 px-3 text-sm font-medium transition-colors ${days === d ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}>
                {d}d
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0 }}>
          <StatCard label="Avg SEO Score" value={overview?.avg_seo_score ? `${overview.avg_seo_score}` : '—'} sub="across all crawls" color="text-primary" />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <StatCard label="Critical Issues" value={overview?.issues_by_severity?.critical ?? '—'} sub="need immediate action" color="text-red-500" />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <StatCard label="Sites Monitored" value={overview?.total_sites ?? '—'} sub="active sites" color="text-blue-500" />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <StatCard label="Crawls (30d)" value={overview?.total_crawls_30d ?? '—'} sub="automated audits" color="text-green-500" />
        </motion.div>
      </div>

      {/* Severity breakdown strip */}
      {overview?.issues_by_severity && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}
          className="bg-card border border-border rounded-xl px-5 py-3 flex flex-wrap gap-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider self-center mr-2">Issues by severity</p>
          {[
            { label: 'Critical', key: 'critical', color: 'text-red-500 bg-red-500/10 border-red-500/20' },
            { label: 'High', key: 'high', color: 'text-orange-500 bg-orange-500/10 border-orange-500/20' },
            { label: 'Medium', key: 'medium', color: 'text-amber-500 bg-amber-500/10 border-amber-500/20' },
            { label: 'Low', key: 'low', color: 'text-blue-500 bg-blue-500/10 border-blue-500/20' },
          ].map(({ label, key, color }) => (
            <div key={key} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${color}`}>
              <span>{label}</span>
              <span>{overview.issues_by_severity[key] ?? 0}</span>
            </div>
          ))}
        </motion.div>
      )}

      {/* Score History Chart */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
        className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-base font-semibold text-foreground">SEO Score History</h2>
            <p className="text-sm text-muted-foreground mt-0.5">Score trend over the last {days} days</p>
          </div>
          <BarChart3 className="h-5 w-5 text-muted-foreground" />
        </div>
        {historyLoading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="w-8 h-8 rounded-full border-2 border-t-transparent border-primary animate-spin" />
          </div>
        ) : scoreData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-center">
            <div>
              <BarChart3 className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No crawl data yet</p>
              <p className="text-xs text-muted-foreground/60 mt-1">Run a crawl on any site to see score trends</p>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={scoreData} margin={{ top: 4, right: 32, left: -24, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis dataKey="date"
                tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
                tickFormatter={(v: string) => v ? new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''}
                axisLine={false} tickLine={false}
              />
              <YAxis yAxisId="score" domain={[0, 100]} tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="issues" orientation="right" tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} width={32} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: 'var(--color-text-muted)' }} />
              <Line yAxisId="score" type="monotone" dataKey="seo_score" name="SEO Score" stroke="#6366f1" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="issues" type="monotone" dataKey="issues_found" name="Issues Found" stroke="#f97316" strokeWidth={1.5} dot={false} strokeDasharray="4 2" activeDot={{ r: 3 }} />
              <Line yAxisId="issues" type="monotone" dataKey="pages_crawled" name="Pages Crawled" stroke="#10b981" strokeWidth={1.5} dot={false} strokeDasharray="2 4" activeDot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </motion.div>

      {/* Site GA4 Performance Panel */}
      {sitePerf && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.23 }}
          className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-start justify-between mb-4 gap-3">
            <div>
              <h2 className="text-base font-semibold text-foreground">GA4 Performance (30d)</h2>
              <p className="text-sm text-muted-foreground mt-0.5">{sitePerf.connected ? 'Live from Google Analytics' : 'GA4 not connected — showing placeholder values'}</p>
            </div>
            <div className="flex flex-wrap gap-1.5 items-center flex-shrink-0">
              {!sitePerf.connected && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">GA4 not connected</span>
              )}
              {sitePerf.property_id && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border font-mono">Property: {sitePerf.property_id}</span>
              )}
              {sitePerf.synced_at && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                  Synced {new Date(sitePerf.synced_at).toLocaleDateString()}
                </span>
              )}
              {sitePerf.generated_at && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted/50 text-muted-foreground/60 border border-border">
                  Generated {new Date(sitePerf.generated_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
            {[
              { label: 'Sessions', value: Math.round(sitePerf.totals?.sessions ?? 0).toLocaleString() },
              { label: 'Views', value: Math.round(sitePerf.totals?.views ?? 0).toLocaleString() },
              { label: 'Active Users', value: Math.round(sitePerf.totals?.active_users ?? 0).toLocaleString() },
              { label: 'Key Events', value: Math.round(sitePerf.totals?.key_events ?? 0).toLocaleString() },
              { label: 'Eng. Rate', value: sitePerf.totals?.engagement_rate ? `${(sitePerf.totals.engagement_rate * 100).toFixed(1)}%` : '—' },
              { label: 'Revenue', value: sitePerf.totals?.total_revenue ? `$${sitePerf.totals.total_revenue.toFixed(2)}` : '—' },
              ...(sitePerf.totals?.transactions != null ? [{ label: 'Transactions', value: Math.round(sitePerf.totals.transactions).toLocaleString() }] : []),
            ].map((stat) => (
              <div key={stat.label} className="rounded-lg bg-muted/30 px-3 py-2 text-center">
                <p className="text-base font-bold text-foreground">{stat.value}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">{stat.label}</p>
              </div>
            ))}
          </div>
          {(sitePerf?.top_pages ?? []).length > 0 && (
            <div className="mt-4">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Top pages by sessions</p>
              <div className="space-y-1.5">
                {(sitePerf.top_pages as any[]).slice(0, 5).map((pg: any, i: number) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-foreground font-mono truncate">{pg.page_path ?? pg.page ?? pg}</span>
                    <span className="text-muted-foreground flex-shrink-0">{pg.sessions ?? pg.active_users ?? 0} sessions</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Issues by Category */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
        className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-base font-semibold text-foreground">Issues by Category</h2>
            <p className="text-sm text-muted-foreground mt-0.5">Distribution of open issues across all sites</p>
          </div>
        </div>
        {categoryData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-center">
            <div>
              <AlertTriangle className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No issues data available</p>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={categoryData} margin={{ top: 4, right: 4, left: -24, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="critical" name="Critical" stackId="a" fill={SEVERITY_COLORS.critical} radius={0} />
              <Bar dataKey="high" name="High" stackId="a" fill={SEVERITY_COLORS.high} />
              <Bar dataKey="medium" name="Medium" stackId="a" fill={SEVERITY_COLORS.medium} />
              <Bar dataKey="low" name="Low" stackId="a" fill={SEVERITY_COLORS.low} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 justify-center">
          {Object.entries(SEVERITY_COLORS).map(([k, color]) => (
            <div key={k} className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
              <span className="text-xs text-muted-foreground capitalize">{k}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
