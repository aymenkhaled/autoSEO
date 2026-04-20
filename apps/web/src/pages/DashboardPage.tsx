import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router'
import {
  Globe, Bug, Wrench, TrendingUp, ArrowUpRight,
  Zap, Play, Clock, CheckCircle2, AlertTriangle,
  XCircle, Loader2, ChevronRight, Sparkles,
} from 'lucide-react'
import { useSites, useCrawls } from '@/hooks/use-data'
import { formatRelativeTime } from '@/lib/utils'

function StatCard({ icon: Icon, label, value, sub, color, href }: {
  icon: any; label: string; value: string | number; sub?: string; color: string; href?: string
}) {
  const card = (
    <div className="bg-card border border-border rounded-xl p-5 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
        {href && <ChevronRight className="h-4 w-4 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors" />}
      </div>
      <p className="text-2xl font-bold text-foreground tracking-tight mb-0.5">{value}</p>
      <p className="text-sm font-medium text-foreground">{label}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  )
  return href ? <Link to={href}>{card}</Link> : card
}

function SeverityBadge({ severity }: { severity: string }) {
  const cfg: Record<string, { label: string; className: string }> = {
    critical: { label: 'Critical', className: 'bg-red-500/10 text-red-500 border-red-500/20' },
    high:     { label: 'High',     className: 'bg-orange-500/10 text-orange-500 border-orange-500/20' },
    medium:   { label: 'Medium',   className: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
    low:      { label: 'Low',      className: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
    info:     { label: 'Info',     className: 'bg-slate-500/10 text-slate-500 border-slate-500/20' },
  }
  const c = cfg[severity] ?? cfg.info
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${c.className}`}>
      {c.label}
    </span>
  )
}

function CrawlStatusIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircle2 className="h-4 w-4 text-green-500" />
  if (status === 'running') return <Loader2 className="h-4 w-4 text-primary animate-spin" />
  if (status === 'failed') return <XCircle className="h-4 w-4 text-red-500" />
  return <Clock className="h-4 w-4 text-muted-foreground" />
}

const mockRecentIssues = [
  { id: '1', title: 'Missing meta description', url: '/blog/seo-tips', severity: 'high', category: 'meta' },
  { id: '2', title: 'Duplicate H1 tags', url: '/products/widget', severity: 'medium', category: 'headings' },
  { id: '3', title: 'Images missing alt text (23)', url: '/gallery', severity: 'high', category: 'images' },
  { id: '4', title: 'Broken canonical link', url: '/landing/offer', severity: 'critical', category: 'technical' },
  { id: '5', title: 'Title tag too long (68 chars)', url: '/about', severity: 'low', category: 'meta' },
]

export default function DashboardPage() {
  const { data: sitesData, isLoading: sitesLoading } = useSites()
  const { data: crawlsData, isLoading: crawlsLoading } = useCrawls()

  const sites = sitesData?.sites ?? []
  const crawls = crawlsData?.crawls ?? []

  const stats = [
    { icon: Globe, label: 'Sites Monitored', value: sites.length || 0, sub: 'Connected sites', color: 'bg-primary/10 text-primary', href: '/dashboard/sites' },
    { icon: Bug, label: 'Open Issues', value: 0, sub: 'Across all sites', color: 'bg-orange-500/10 text-orange-500', href: '/dashboard/issues' },
    { icon: Wrench, label: 'Fixes Applied', value: 0, sub: 'Total auto-fixes', color: 'bg-green-500/10 text-green-500', href: '/dashboard/fixes' },
    { icon: TrendingUp, label: 'Avg SEO Score', value: '—', sub: 'Needs crawl', color: 'bg-violet-500/10 text-violet-500' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Welcome back — here's what's happening across your sites.</p>
        </div>
        <Link to="/dashboard/sites"
          className="hidden sm:inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
          <Zap className="h-4 w-4" /> Add Site
        </Link>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}>
            <StatCard {...s} />
          </motion.div>
        ))}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent activity — wide */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
          className="lg:col-span-2">
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h2 className="text-sm font-semibold text-foreground">Recent Issues</h2>
              <Link to="/dashboard/issues" className="text-xs text-primary hover:underline font-medium flex items-center gap-1">
                View all <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="divide-y divide-border">
              {mockRecentIssues.map((issue) => (
                <div key={issue.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-muted/50 transition-colors">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{issue.title}</p>
                    <p className="text-xs text-muted-foreground truncate mt-0.5 font-mono">{issue.url}</p>
                  </div>
                  <SeverityBadge severity={issue.severity} />
                </div>
              ))}
              {mockRecentIssues.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <CheckCircle2 className="h-10 w-10 text-green-500/50 mb-3" />
                  <p className="text-sm font-medium text-foreground">No issues found</p>
                  <p className="text-xs text-muted-foreground mt-1">Add a site and run a crawl to start</p>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Recent crawls */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                <h2 className="text-sm font-semibold text-foreground">Recent Crawls</h2>
                <Link to="/dashboard/sites" className="text-xs text-primary hover:underline font-medium flex items-center gap-1">
                  Sites <ArrowUpRight className="h-3 w-3" />
                </Link>
              </div>
              <div className="divide-y divide-border">
                {crawlsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 text-primary animate-spin" />
                  </div>
                ) : crawls.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center px-4">
                    <Play className="h-8 w-8 text-muted-foreground/40 mb-2" />
                    <p className="text-sm text-muted-foreground">No crawls yet</p>
                    <p className="text-xs text-muted-foreground/60 mt-0.5">Add a site to get started</p>
                  </div>
                ) : crawls.slice(0, 5).map((crawl: any) => (
                  <div key={crawl.id} className="flex items-center gap-3 px-5 py-3">
                    <CrawlStatusIcon status={crawl.status} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">{crawl.site_id}</p>
                      <p className="text-[10px] text-muted-foreground">{formatRelativeTime(crawl.created_at)}</p>
                    </div>
                    <span className={`text-[10px] font-semibold capitalize ${
                      crawl.status === 'completed' ? 'text-green-500' :
                      crawl.status === 'running' ? 'text-primary' :
                      crawl.status === 'failed' ? 'text-red-500' :
                      'text-muted-foreground'
                    }`}>{crawl.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Upgrade CTA */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <div className="bg-gradient-to-br from-cyan-500/10 via-blue-500/10 to-violet-500/10 border border-primary/20 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-sm font-semibold text-foreground">Pro Plan</span>
              </div>
              <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
                Unlock AI auto-fix, daily crawls, and up to 10 sites. Fixes ship to WordPress, Shopify, and Webflow automatically.
              </p>
              <button className="w-full h-9 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-xs font-semibold shadow-lg shadow-cyan-500/25 transition-all">
                Upgrade to Pro
              </button>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Quick start — only if no sites */}
      {!sitesLoading && sites.length === 0 && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
          <div className="bg-card border border-dashed border-border rounded-xl p-8 text-center">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Zap className="h-7 w-7 text-primary" />
            </div>
            <h2 className="text-base font-semibold text-foreground mb-2">Get started in 60 seconds</h2>
            <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
              Add your first site and AutoSEO will crawl every page, detect issues, and prepare AI-generated fixes.
            </p>
            <Link to="/dashboard/sites"
              className="inline-flex items-center gap-2 h-10 px-6 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all">
              Add Your First Site <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </motion.div>
      )}
    </div>
  )
}
