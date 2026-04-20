import { motion } from 'framer-motion'
import { CreditCard, Zap, Check, ArrowUpRight, TrendingUp } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

function useUsage() {
  return useQuery({
    queryKey: ['usage'],
    queryFn: () => apiClient.get('/usage').json<any>(),
  })
}

const PLANS = [
  {
    name: 'Free',
    price: 0,
    period: 'forever',
    description: 'For personal projects',
    color: 'border-border',
    features: ['1 site', '5 crawls/month', '50 pages/crawl', '10 AI fixes/month'],
  },
  {
    name: 'Starter',
    price: 29,
    period: 'month',
    description: 'For growing businesses',
    color: 'border-primary',
    popular: true,
    features: ['5 sites', '30 crawls/month', '500 pages/crawl', '100 AI fixes/month', 'Email reports', 'API access'],
  },
  {
    name: 'Pro',
    price: 99,
    period: 'month',
    description: 'For serious SEO',
    color: 'border-border',
    features: ['20 sites', '100 crawls/month', '2000 pages/crawl', '500 AI fixes/month', 'PDF reports', 'Slack notifications', 'Priority support'],
  },
  {
    name: 'Agency',
    price: 299,
    period: 'month',
    description: 'For agencies & teams',
    color: 'border-border',
    features: ['100 sites', '500 crawls/month', '5000 pages/crawl', '2000 AI fixes/month', 'White-label reports', 'Team management', 'Dedicated support'],
  },
]

function UsageBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const pct = limit > 0 ? Math.min((used / limit) * 100, 100) : 0
  const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-primary'
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-xs font-medium text-foreground">{used} / {limit}</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function BillingPage() {
  const { data: usage, isLoading } = useUsage()

  const plan = usage?.plan ?? 'free'
  const limits = usage?.limits ?? {}
  const usageData = usage?.usage ?? {}

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Billing</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Manage your subscription and monitor usage</p>
      </div>

      {/* Current usage */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        className="bg-card border border-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Current Plan</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-lg font-bold text-foreground capitalize">{plan}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold border border-primary/20">Active</span>
            </div>
          </div>
          {usage?.billing_period && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Billing period</p>
              <p className="text-xs font-medium text-foreground mt-0.5">
                {new Date(usage.billing_period.start).toLocaleDateString()} – {new Date(usage.billing_period.end).toLocaleDateString()}
              </p>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => <div key={i} className="h-6 bg-muted rounded animate-pulse" />)}
          </div>
        ) : (
          <div className="space-y-4">
            {usageData.sites && <UsageBar used={usageData.sites.used} limit={usageData.sites.limit} label="Sites" />}
            {usageData.crawls && <UsageBar used={usageData.crawls.used} limit={usageData.crawls.limit} label="Crawls this month" />}
            {usageData.ai_fixes && <UsageBar used={usageData.ai_fixes.used} limit={usageData.ai_fixes.limit} label="AI fixes this month" />}
          </div>
        )}

        {usage?.ai_cost && (
          <div className="mt-4 pt-4 border-t border-border flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">
              AI cost this month: <span className="font-semibold text-foreground">${usage.ai_cost.cost_usd.toFixed(4)}</span>
              {' '}({(usage.ai_cost.tokens || 0).toLocaleString()} tokens)
            </p>
          </div>
        )}
      </motion.div>

      {/* Plans */}
      <div>
        <h2 className="text-sm font-semibold text-foreground mb-3">Upgrade Your Plan</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {PLANS.map((p, i) => {
            const isCurrent = plan.toLowerCase() === p.name.toLowerCase()
            return (
              <motion.div key={p.name} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                className={`relative bg-card border rounded-xl p-5 flex flex-col ${p.popular ? 'border-primary shadow-md shadow-primary/10' : 'border-border'}`}>
                {p.popular && (
                  <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
                    <span className="text-[10px] font-bold text-primary-foreground bg-primary px-2.5 py-0.5 rounded-full">POPULAR</span>
                  </div>
                )}
                <div className="mb-4">
                  <p className="text-sm font-semibold text-foreground">{p.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{p.description}</p>
                  <div className="mt-3 flex items-baseline gap-1">
                    <span className="text-2xl font-bold text-foreground">${p.price}</span>
                    <span className="text-xs text-muted-foreground">/{p.period}</span>
                  </div>
                </div>
                <ul className="space-y-2 flex-1 mb-4">
                  {p.features.map(f => (
                    <li key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Check className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => {}}
                  disabled={isCurrent}
                  className={`w-full h-8 rounded-lg text-xs font-semibold transition-colors ${
                    isCurrent
                      ? 'bg-muted text-muted-foreground cursor-default'
                      : p.popular
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                      : 'border border-border text-foreground hover:bg-muted'
                  }`}>
                  {isCurrent ? 'Current plan' : `Upgrade to ${p.name}`}
                </button>
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* Payment method placeholder */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
        className="bg-card border border-border rounded-xl p-5">
        <div className="flex items-center gap-3 mb-3">
          <CreditCard className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">Payment Method</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Payment is handled securely via Stripe. No card required on the free plan.
        </p>
        <button onClick={() => {}}
          className="inline-flex items-center gap-2 mt-3 h-8 px-3 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-muted transition-colors">
          Manage billing <ArrowUpRight className="h-3 w-3" />
        </button>
      </motion.div>
    </div>
  )
}
