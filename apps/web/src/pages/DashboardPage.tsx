import { motion } from 'framer-motion'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowUpRight,
  Bug,
  CheckCircle2,
  Globe,
  Loader2,
  TrendingUp,
  Wrench,
  Zap,
} from 'lucide-react'

import { dashboardApi } from '@/lib/api-client'
import { formatRelativeTime } from '@/lib/utils'

function StatCard({ icon: Icon, label, value, sub, color, href }: {
  icon: any
  label: string
  value: string | number
  sub?: string
  color: string
  href?: string
}) {
  const card = (
    <div className="bg-card border border-border rounded-xl p-5 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
        {href && <ArrowUpRight className="h-4 w-4 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors" />}
      </div>
      <p className="text-2xl font-bold text-foreground tracking-tight mb-0.5">{value}</p>
      <p className="text-sm font-medium text-foreground">{label}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  )
  return href ? <Link to={href}>{card}</Link> : card
}

function SeverityBadge({ severity }: { severity: string }) {
  const cfg: Record<string, string> = {
    critical: 'bg-red-500/10 text-red-500 border-red-500/20',
    high: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    medium: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    low: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border capitalize ${cfg[severity] ?? cfg.low}`}>
      {severity}
    </span>
  )
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-overview'],
    queryFn: () => dashboardApi.overview(),
  })

  const metrics = data?.metrics ?? {}
  const recentIssues = data?.recent_issues ?? []
  const recentCrawls = data?.recent_crawls ?? []

  const stats = [
    {
      icon: Globe,
      label: 'Sites Monitored',
      value: metrics.sites ?? 0,
      sub: 'Connected sites',
      color: 'bg-primary/10 text-primary',
      href: '/dashboard/sites',
    },
    {
      icon: Bug,
      label: 'Open Issues',
      value: metrics.open_issues ?? 0,
      sub: 'Needs review',
      color: 'bg-orange-500/10 text-orange-500',
      href: '/dashboard/issues',
    },
    {
      icon: Wrench,
      label: 'Fixes Deployed',
      value: metrics.deployed_fixes ?? 0,
      sub: 'Live changes shipped',
      color: 'bg-green-500/10 text-green-500',
      href: '/dashboard/fixes',
    },
    {
      icon: TrendingUp,
      label: 'Avg SEO Score',
      value: metrics.avg_seo_score ?? '—',
      sub: 'Across completed crawls',
      color: 'bg-violet-500/10 text-violet-500',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Live organization SEO status, recent issues, and crawl activity.</p>
        </div>
        <Link
          to="/dashboard/sites"
          className="hidden sm:inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white text-sm font-semibold shadow-lg shadow-cyan-500/25 transition-all"
        >
          <Zap className="h-4 w-4" /> Add Site
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <motion.div key={stat.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.07 }}>
            <StatCard {...stat} />
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }} className="lg:col-span-2">
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h2 className="text-sm font-semibold text-foreground">Recent Issues</h2>
              <Link to="/dashboard/issues" className="text-xs text-primary hover:underline font-medium flex items-center gap-1">
                View all <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="divide-y divide-border">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-5 w-5 text-primary animate-spin" />
                </div>
              ) : recentIssues.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <CheckCircle2 className="h-10 w-10 text-green-500/50 mb-3" />
                  <p className="text-sm font-medium text-foreground">No recent issues</p>
                  <p className="text-xs text-muted-foreground mt-1">Run a crawl to refresh your issue list.</p>
                </div>
              ) : (
                recentIssues.map((issue: any) => (
                  <div key={issue.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-muted/50 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-orange-500/10 text-orange-500 flex items-center justify-center flex-shrink-0">
                      <AlertTriangle className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {issue.type.replace(/_/g, ' ')}
                      </p>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {issue.site_name}{issue.page_url ? ` · ${issue.page_url}` : ''}
                      </p>
                    </div>
                    <SeverityBadge severity={issue.severity} />
                  </div>
                ))
              )}
            </div>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h2 className="text-sm font-semibold text-foreground">Recent Crawls</h2>
              <Link to="/dashboard/sites" className="text-xs text-primary hover:underline font-medium flex items-center gap-1">
                Sites <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="divide-y divide-border">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-5 w-5 text-primary animate-spin" />
                </div>
              ) : recentCrawls.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center px-4">
                  <Zap className="h-8 w-8 text-muted-foreground/40 mb-2" />
                  <p className="text-sm text-muted-foreground">No crawls yet</p>
                </div>
              ) : (
                recentCrawls.map((crawl: any) => (
                  <div key={crawl.id} className="flex items-center gap-3 px-5 py-3">
                    <div className={`w-2.5 h-2.5 rounded-full ${
                      crawl.status === 'completed' ? 'bg-green-500' :
                      crawl.status === 'running' ? 'bg-cyan-500' :
                      crawl.status === 'failed' ? 'bg-red-500' :
                      'bg-amber-500'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">{crawl.site_name}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {crawl.pages_crawled} pages · {crawl.issues_found} issues
                      </p>
                    </div>
                    <span className="text-[10px] text-muted-foreground">
                      {crawl.created_at ? formatRelativeTime(crawl.created_at) : '—'}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
