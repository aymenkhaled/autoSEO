import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Globe, BarChart3, Bug, FileText, Target, Swords,
  Link2, Settings, RefreshCw, ExternalLink, CheckCircle2,
  AlertTriangle, XCircle, Info, TrendingUp, TrendingDown,
  Clock, Shield, Zap, ChevronUp, ChevronDown, Minus,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

const TABS = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'issues', label: 'Issues', icon: Bug },
  { id: 'pages', label: 'Pages', icon: FileText },
  { id: 'keywords', label: 'Keywords', icon: Target },
  { id: 'competitors', label: 'Competitors', icon: Swords },
  { id: 'backlinks', label: 'Backlinks', icon: Link2 },
  { id: 'settings', label: 'Settings', icon: Settings },
]

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? 'text-green-500 bg-green-500/10 border-green-500/20'
    : score >= 60 ? 'text-amber-500 bg-amber-500/10 border-amber-500/20'
    : 'text-red-500 bg-red-500/10 border-red-500/20'
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-sm font-bold border ${color}`}>
      {score}
    </span>
  )
}

function StatCard({ label, value, change, icon: Icon, color = 'cyan' }: {
  label: string; value: string | number; change?: number; icon: any; color?: string
}) {
  const colorMap: Record<string, string> = {
    cyan: 'bg-cyan-500/10 text-cyan-500',
    red: 'bg-red-500/10 text-red-500',
    green: 'bg-green-500/10 text-green-500',
    amber: 'bg-amber-500/10 text-amber-500',
    blue: 'bg-blue-500/10 text-blue-500',
  }
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${colorMap[color]}`}>
          <Icon className="h-4 w-4" />
        </div>
        {change !== undefined && (
          <span className={`text-xs font-medium flex items-center gap-0.5 ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {change >= 0 ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {Math.abs(change)}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground mt-1">{label}</p>
    </div>
  )
}

function IssueSeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    critical: 'bg-red-500/10 text-red-500 border-red-500/20',
    high: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    medium: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    low: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    info: 'bg-slate-500/10 text-slate-500 border-slate-500/20',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border capitalize ${map[severity] ?? map.info}`}>
      {severity}
    </span>
  )
}

// ─── Overview Tab ────────────────────────────────────────────────────────────
function OverviewTab({ site }: { site: any }) {
  const stats = [
    { label: 'SEO Score', value: site?.seo_score ?? '—', icon: Shield, color: 'cyan', change: 4 },
    { label: 'Open Issues', value: site?.issues_count ?? 0, icon: Bug, color: 'red', change: -12 },
    { label: 'Pages Crawled', value: site?.pages_count ?? 0, icon: FileText, color: 'blue' },
    { label: 'Fixes Applied', value: site?.fixes_applied ?? 0, icon: CheckCircle2, color: 'green', change: 8 },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      {/* Score breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-card p-6">
          <h3 className="text-sm font-semibold text-foreground mb-4">Score Breakdown</h3>
          <div className="space-y-3">
            {[
              { label: 'On-Page SEO', score: 82 },
              { label: 'Technical SEO', score: 67 },
              { label: 'Performance', score: 74 },
              { label: 'Content Quality', score: 91 },
              { label: 'Link Profile', score: 55 },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-28 flex-shrink-0">{item.label}</span>
                <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${item.score >= 80 ? 'bg-green-500' : item.score >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${item.score}%` }}
                  />
                </div>
                <span className="text-xs font-semibold text-foreground w-6 text-right">{item.score}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-6">
          <h3 className="text-sm font-semibold text-foreground mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {[
              { action: 'Crawl completed', detail: '247 pages analyzed', time: '2h ago', icon: RefreshCw, color: 'text-cyan-500' },
              { action: 'Fix applied', detail: 'Meta description updated', time: '5h ago', icon: CheckCircle2, color: 'text-green-500' },
              { action: 'New issue found', detail: 'Missing alt text (12 images)', time: '2h ago', icon: AlertTriangle, color: 'text-amber-500' },
              { action: 'Fix applied', detail: 'Title tag optimized', time: '1d ago', icon: CheckCircle2, color: 'text-green-500' },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`mt-0.5 flex-shrink-0 ${item.color}`}>
                  <item.icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{item.action}</p>
                  <p className="text-xs text-muted-foreground">{item.detail}</p>
                </div>
                <span className="text-xs text-muted-foreground flex-shrink-0">{item.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Issues by category */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4">Issues by Category</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Meta Tags', count: 14, icon: FileText, color: 'text-blue-500 bg-blue-500/10' },
            { label: 'Headings', count: 8, icon: Bug, color: 'text-amber-500 bg-amber-500/10' },
            { label: 'Images', count: 23, icon: AlertTriangle, color: 'text-red-500 bg-red-500/10' },
            { label: 'Performance', count: 5, icon: Zap, color: 'text-cyan-500 bg-cyan-500/10' },
          ].map((cat) => (
            <div key={cat.label} className="flex items-center gap-3 p-3 rounded-lg bg-muted/40">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${cat.color}`}>
                <cat.icon className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">{cat.count}</p>
                <p className="text-xs text-muted-foreground">{cat.label}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Issues Tab ───────────────────────────────────────────────────────────────
function IssuesTab({ siteId }: { siteId: string }) {
  const [filter, setFilter] = useState('all')
  const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low']
  const MOCK_ISSUES = [
    { id: '1', type: 'Missing meta description', category: 'meta', severity: 'high', page: '/about', fix_status: 'pending', fix_type: 'ai_auto' },
    { id: '2', type: 'Title tag too long', category: 'meta', severity: 'medium', page: '/blog/post-1', fix_status: 'pending', fix_type: 'ai_auto' },
    { id: '3', type: 'Missing alt text', category: 'images', severity: 'high', page: '/products', fix_status: 'pending', fix_type: 'ai_auto' },
    { id: '4', type: 'Broken internal link', category: 'links', severity: 'critical', page: '/services', fix_status: 'pending', fix_type: 'manual' },
    { id: '5', type: 'Missing H1 tag', category: 'headings', severity: 'critical', page: '/contact', fix_status: 'applied', fix_type: 'ai_auto' },
    { id: '6', type: 'Slow page load (LCP > 4s)', category: 'performance', severity: 'high', page: '/home', fix_status: 'pending', fix_type: 'manual' },
    { id: '7', type: 'Duplicate title tag', category: 'meta', severity: 'medium', page: '/products/item-2', fix_status: 'pending', fix_type: 'ai_auto' },
  ]
  const filtered = filter === 'all' ? MOCK_ISSUES : MOCK_ISSUES.filter(i => i.severity === filter)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {SEVERITIES.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all capitalize ${filter === s ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}>
            {s}
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Issue</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Page</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Severity</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Fix Type</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filtered.map((issue) => (
              <tr key={issue.id} className="hover:bg-muted/20 transition-colors">
                <td className="px-4 py-3 font-medium text-foreground">{issue.type}</td>
                <td className="px-4 py-3 text-muted-foreground font-mono text-xs">{issue.page}</td>
                <td className="px-4 py-3"><IssueSeverityBadge severity={issue.severity} /></td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${issue.fix_type === 'ai_auto' ? 'bg-cyan-500/10 text-cyan-500' : 'bg-muted text-muted-foreground'}`}>
                    {issue.fix_type === 'ai_auto' ? '⚡ AI Auto' : 'Manual'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${issue.fix_status === 'applied' ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'}`}>
                    {issue.fix_status === 'applied' ? '✓ Fixed' : 'Open'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <CheckCircle2 className="h-10 w-10 text-green-500 mb-3" />
            <p className="text-sm font-semibold text-foreground">No {filter} issues</p>
            <p className="text-xs text-muted-foreground mt-1">Great work keeping this severity clean!</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Pages Tab ────────────────────────────────────────────────────────────────
function PagesTab() {
  const MOCK_PAGES = [
    { url: '/', title: 'Home', status: 200, issues: 2, score: 84, word_count: 1240 },
    { url: '/about', title: 'About Us', status: 200, issues: 5, score: 71, word_count: 890 },
    { url: '/blog', title: 'Blog', status: 200, issues: 1, score: 92, word_count: 2100 },
    { url: '/contact', title: 'Contact', status: 200, issues: 3, score: 63, word_count: 450 },
    { url: '/products', title: 'Products', status: 200, issues: 8, score: 58, word_count: 3200 },
    { url: '/services', title: 'Services', status: 301, issues: 0, score: 0, word_count: 0 },
  ]

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Page</th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">SEO Score</th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Issues</th>
            <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Words</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {MOCK_PAGES.map((page) => (
            <tr key={page.url} className="hover:bg-muted/20 transition-colors">
              <td className="px-4 py-3">
                <div>
                  <p className="font-medium text-foreground">{page.title}</p>
                  <p className="text-xs text-muted-foreground font-mono">{page.url}</p>
                </div>
              </td>
              <td className="px-4 py-3">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${page.status === 200 ? 'bg-green-500/10 text-green-500' : 'bg-amber-500/10 text-amber-500'}`}>
                  {page.status}
                </span>
              </td>
              <td className="px-4 py-3">
                {page.score > 0 ? <ScoreBadge score={page.score} /> : <span className="text-xs text-muted-foreground">—</span>}
              </td>
              <td className="px-4 py-3">
                {page.issues > 0 ? (
                  <span className="text-xs font-medium text-red-500">{page.issues} issues</span>
                ) : (
                  <span className="text-xs font-medium text-green-500">Clean</span>
                )}
              </td>
              <td className="px-4 py-3 text-muted-foreground">{page.word_count > 0 ? page.word_count.toLocaleString() : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Keywords Tab ─────────────────────────────────────────────────────────────
function KeywordsTab({ siteId }: { siteId: string }) {
  const MOCK_KEYWORDS = [
    { keyword: 'seo automation', position: 7, prev: 11, volume: 2400, difficulty: 62 },
    { keyword: 'auto seo tool', position: 3, prev: 5, volume: 880, difficulty: 45 },
    { keyword: 'website seo checker', position: 14, prev: 18, volume: 5400, difficulty: 71 },
    { keyword: 'seo issue fixer', position: 22, prev: 19, volume: 320, difficulty: 38 },
    { keyword: 'automated meta tags', position: 1, prev: 1, volume: 1200, difficulty: 29 },
  ]

  const PositionChange = ({ pos, prev }: { pos: number; prev: number }) => {
    const diff = prev - pos
    if (diff > 0) return <span className="text-xs text-green-500 flex items-center gap-0.5"><TrendingUp className="h-3 w-3" />+{diff}</span>
    if (diff < 0) return <span className="text-xs text-red-500 flex items-center gap-0.5"><TrendingDown className="h-3 w-3" />{diff}</span>
    return <span className="text-xs text-muted-foreground flex items-center gap-0.5"><Minus className="h-3 w-3" />0</span>
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex items-start gap-3">
        <Info className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-foreground">DataForSEO API not connected</p>
          <p className="text-xs text-muted-foreground mt-0.5">Connect your DataForSEO account to enable live keyword rank tracking. Showing sample data below.</p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Keyword</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Position</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Change</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Volume</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Difficulty</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {MOCK_KEYWORDS.map((kw) => (
              <tr key={kw.keyword} className="hover:bg-muted/20 transition-colors">
                <td className="px-4 py-3 font-medium text-foreground">{kw.keyword}</td>
                <td className="px-4 py-3">
                  <span className={`text-sm font-bold ${kw.position <= 3 ? 'text-green-500' : kw.position <= 10 ? 'text-amber-500' : 'text-muted-foreground'}`}>
                    #{kw.position}
                  </span>
                </td>
                <td className="px-4 py-3"><PositionChange pos={kw.position} prev={kw.prev} /></td>
                <td className="px-4 py-3 text-muted-foreground">{kw.volume.toLocaleString()}/mo</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div className={`h-full rounded-full ${kw.difficulty >= 70 ? 'bg-red-500' : kw.difficulty >= 50 ? 'bg-amber-500' : 'bg-green-500'}`}
                        style={{ width: `${kw.difficulty}%` }} />
                    </div>
                    <span className="text-xs text-muted-foreground">{kw.difficulty}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Competitors Tab ──────────────────────────────────────────────────────────
function CompetitorsTab({ siteId }: { siteId: string }) {
  const MOCK = [
    { domain: 'ahrefs.com', score: 94, keywords: 89200, backlinks: 1820000 },
    { domain: 'semrush.com', score: 91, keywords: 134000, backlinks: 2100000 },
    { domain: 'moz.com', score: 88, keywords: 67000, backlinks: 980000 },
  ]

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex items-start gap-3">
        <Info className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-muted-foreground">
          Competitor analysis requires Ahrefs or Majestic API. Showing sample data.
        </p>
      </div>
      <div className="grid gap-4">
        {MOCK.map((c) => (
          <div key={c.domain} className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
            <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center text-xs font-bold text-foreground uppercase flex-shrink-0">
              {c.domain[0]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground">{c.domain}</p>
              <div className="flex items-center gap-4 mt-1">
                <span className="text-xs text-muted-foreground">{c.keywords.toLocaleString()} keywords</span>
                <span className="text-xs text-muted-foreground">{(c.backlinks / 1000).toFixed(0)}K backlinks</span>
              </div>
            </div>
            <ScoreBadge score={c.score} />
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Backlinks Tab ────────────────────────────────────────────────────────────
function BacklinksTab() {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex items-start gap-3">
        <Info className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-muted-foreground">
          Backlink monitoring requires Ahrefs or Majestic API key. Configure it in Settings → Integrations.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Backlinks', value: '—', icon: Link2, color: 'cyan' },
          { label: 'Referring Domains', value: '—', icon: Globe, color: 'blue' },
          { label: 'Domain Rating', value: '—', icon: Shield, color: 'green' },
        ].map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <div className="rounded-xl border border-border bg-card p-6 text-center">
        <Link2 className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
        <p className="text-sm font-semibold text-foreground mb-1">No backlink data yet</p>
        <p className="text-xs text-muted-foreground">Connect an API key in Integrations to start tracking backlinks</p>
      </div>
    </div>
  )
}

// ─── Settings Tab ─────────────────────────────────────────────────────────────
function SettingsTab({ site }: { site: any }) {
  return (
    <div className="space-y-6 max-w-2xl">
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <h3 className="text-sm font-semibold text-foreground">Crawl Settings</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Crawl Frequency</label>
            <select className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50">
              <option value="manual">Manual only</option>
              <option value="weekly">Weekly</option>
              <option value="daily">Daily</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1.5">Max Pages</label>
            <input type="number" defaultValue={500} className="w-full h-10 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
        </div>
        <div className="flex items-center justify-between py-3 border-t border-border">
          <div>
            <p className="text-sm font-medium text-foreground">Respect robots.txt</p>
            <p className="text-xs text-muted-foreground">Skip pages disallowed by robots.txt</p>
          </div>
          <div className="w-10 h-5 rounded-full bg-primary relative cursor-pointer">
            <div className="absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow-sm" />
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 space-y-3">
        <h3 className="text-sm font-semibold text-red-500">Danger Zone</h3>
        <p className="text-xs text-muted-foreground">Permanently delete this site and all its data. This action cannot be undone.</p>
        <button className="px-4 py-2 rounded-lg border border-red-500/30 text-red-500 text-sm font-medium hover:bg-red-500/10 transition-colors">
          Delete Site
        </button>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [crawling, setCrawling] = useState(false)

  const { data: site, isLoading } = useQuery({
    queryKey: ['site', id],
    queryFn: async () => {
      try {
        const res = await api.get(`sites/${id}`).json<any>()
        return res
      } catch {
        return null
      }
    },
    enabled: !!id,
  })

  const handleCrawl = async () => {
    setCrawling(true)
    try {
      await api.post(`sites/${id}/crawl`)
    } catch {}
    setTimeout(() => setCrawling(false), 3000)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 bg-muted animate-pulse rounded-lg" />
        <div className="h-32 bg-muted animate-pulse rounded-xl" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-28 bg-muted animate-pulse rounded-xl" />)}
        </div>
      </div>
    )
  }

  const displaySite = site || {
    domain: 'example.com',
    name: 'Example Site',
    status: 'active',
    seo_score: 76,
    issues_count: 23,
    pages_count: 247,
    fixes_applied: 18,
    last_crawled_at: new Date().toISOString(),
    connection_type: 'crawler',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <button onClick={() => navigate('/dashboard/sites')}
            className="mt-1 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-foreground">{displaySite.name || displaySite.domain}</h1>
              <ScoreBadge score={displaySite.seo_score ?? 76} />
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${displaySite.status === 'active' ? 'bg-green-500/10 text-green-500' : 'bg-muted text-muted-foreground'}`}>
                {displaySite.status ?? 'active'}
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <a href={`https://${displaySite.domain}`} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-primary transition-colors">
                <Globe className="h-3.5 w-3.5" />
                {displaySite.domain}
                <ExternalLink className="h-3 w-3" />
              </a>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                Last crawled {displaySite.last_crawled_at ? new Date(displaySite.last_crawled_at).toLocaleDateString() : 'Never'}
              </span>
            </div>
          </div>
        </div>

        <button onClick={handleCrawl} disabled={crawling}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-semibold hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-60">
          <RefreshCw className={`h-4 w-4 ${crawling ? 'animate-spin' : ''}`} />
          {crawling ? 'Crawling…' : 'Run Crawl'}
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-0.5 -mb-px overflow-x-auto">
          {TABS.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}>
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <motion.div key={activeTab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
        {activeTab === 'overview' && <OverviewTab site={displaySite} />}
        {activeTab === 'issues' && <IssuesTab siteId={id!} />}
        {activeTab === 'pages' && <PagesTab />}
        {activeTab === 'keywords' && <KeywordsTab siteId={id!} />}
        {activeTab === 'competitors' && <CompetitorsTab siteId={id!} />}
        {activeTab === 'backlinks' && <BacklinksTab />}
        {activeTab === 'settings' && <SettingsTab site={displaySite} />}
      </motion.div>
    </div>
  )
}
