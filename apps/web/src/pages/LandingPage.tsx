import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { motion, useInView } from 'framer-motion'
import { useTheme } from 'next-themes'
import {
  Zap, Globe, Bug, Wrench, BarChart3, ArrowRight,
  CheckCircle2, TrendingUp, Shield, Code2, Cpu,
  Star, Activity, ChevronRight, Sparkles,
  Play, Search, Sun, Moon, Menu, X,
} from 'lucide-react'

function Counter({ to, suffix = '' }: { to: number; suffix?: string }) {
  const [n, setN] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })
  useEffect(() => {
    if (!inView) return
    const duration = 1800
    const step = (to / duration) * 16
    let cur = 0
    const t = setInterval(() => {
      cur += step
      if (cur >= to) { setN(to); clearInterval(t) }
      else setN(Math.floor(cur))
    }, 16)
    return () => clearInterval(t)
  }, [inView, to])
  return <div ref={ref}>{n.toLocaleString()}{suffix}</div>
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="h-9 w-9 rounded-lg flex items-center justify-center border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
      aria-label="Toggle theme"
    >
      <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
    </button>
  )
}

function HeroOrb() {
  return (
    <div className="relative w-[420px] h-[420px] flex-shrink-0 select-none" style={{ perspective: '1200px' }}>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-64 h-64 rounded-full opacity-30" style={{
          background: 'radial-gradient(circle, hsl(var(--primary)) 0%, transparent 70%)',
          filter: 'blur(50px)',
          animation: 'glow-pulse 4s ease-in-out infinite',
        }} />
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-32 h-32 rounded-full" style={{
          background: 'radial-gradient(circle at 38% 32%, hsl(199 89% 70%) 0%, hsl(var(--primary)) 40%, hsl(217 91% 35%) 100%)',
          boxShadow: '0 0 60px hsl(var(--primary) / 0.4), inset 0 -16px 32px rgba(0,0,0,0.3)',
        }}>
          <div className="absolute inset-0 rounded-full flex items-center justify-center">
            <Zap className="w-10 h-10 text-white" style={{ filter: 'drop-shadow(0 0 8px rgba(255,255,255,0.7))' }} />
          </div>
        </div>
      </div>
      <div className="absolute inset-0 flex items-center justify-center animate-spin-slow">
        <div className="w-56 h-56 rounded-full border border-primary/30 relative" style={{ transform: 'rotateX(68deg)' }}>
          <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 w-5 h-5 rounded-full bg-primary" style={{ boxShadow: '0 0 16px hsl(var(--primary) / 0.9)' }} />
        </div>
      </div>
      <div className="absolute inset-0 flex items-center justify-center animate-spin-rev">
        <div className="w-[320px] h-[320px] rounded-full border border-blue-500/20 relative" style={{ transform: 'rotateX(58deg) rotateZ(28deg)' }}>
          <div className="absolute top-1/2 -right-3 -translate-y-1/2 w-5 h-5 rounded-full bg-blue-500" style={{ boxShadow: '0 0 16px rgba(59,130,246,0.9)' }} />
          <div className="absolute -bottom-2 left-1/3 w-3 h-3 rounded-full bg-cyan-400" style={{ boxShadow: '0 0 12px rgba(34,211,238,0.9)' }} />
        </div>
      </div>
      {[
        { label: 'Meta Fixed', icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', x: -180, y: -60, delay: 0 },
        { label: 'Score +18', icon: TrendingUp, color: 'text-primary', bg: 'bg-primary/10 border-primary/20', x: 160, y: -45, delay: 0.5 },
        { label: '247 Issues', icon: Bug, color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/20', x: -165, y: 85, delay: 1 },
        { label: 'AI Fixed', icon: Cpu, color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/20', x: 150, y: 95, delay: 1.4 },
      ].map((p) => (
        <motion.div key={p.label}
          className={`absolute flex items-center gap-2 px-3 py-1.5 rounded-xl border backdrop-blur-sm ${p.bg}`}
          style={{ left: '50%', top: '50%', x: p.x, y: p.y }}
          animate={{ y: [p.y, p.y - 8, p.y] }}
          transition={{ duration: 3.5 + p.delay * 0.5, delay: p.delay, repeat: Infinity, ease: 'easeInOut' }}>
          <p.icon className={`w-3.5 h-3.5 ${p.color}`} />
          <span className={`text-xs font-semibold ${p.color}`}>{p.label}</span>
        </motion.div>
      ))}
    </div>
  )
}

function FeatureCard({ icon: Icon, title, description, color }: { icon: any; title: string; description: string; color: string }) {
  return (
    <div className="group relative bg-card border border-border rounded-xl p-6 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${color}`}>
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="text-base font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
    </div>
  )
}

function PricingCard({ tier, price, freq, description, features, cta, featured }: {
  tier: string; price: string; freq?: string; description: string; features: string[]; cta: string; featured?: boolean
}) {
  return (
    <div className={`relative flex flex-col rounded-2xl p-8 border ${featured
      ? 'border-primary/50 shadow-lg shadow-primary/10 bg-card'
      : 'border-border bg-card'
    }`}>
      {featured && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <span className="inline-flex items-center px-3 py-1 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-bold shadow-lg shadow-cyan-500/25">
            Most Popular
          </span>
        </div>
      )}
      <div className="mb-6">
        <p className={`text-xs font-semibold uppercase tracking-wider mb-3 ${featured ? 'text-primary' : 'text-muted-foreground'}`}>{tier}</p>
        <div className="flex items-end gap-1 mb-2">
          <span className="text-4xl font-bold text-foreground tracking-tight">{price}</span>
          {freq && <span className="text-sm text-muted-foreground mb-1">{freq}</span>}
        </div>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="h-px bg-border mb-6" />
      <ul className="space-y-3 flex-1 mb-8">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-3">
            <CheckCircle2 className={`h-4 w-4 mt-0.5 flex-shrink-0 ${featured ? 'text-primary' : 'text-green-500 dark:text-green-400'}`} />
            <span className="text-sm text-muted-foreground">{f}</span>
          </li>
        ))}
      </ul>
      <Link to="/signup"
        className={`w-full flex items-center justify-center gap-2 h-11 rounded-lg text-sm font-semibold transition-all ${featured
          ? 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40'
          : 'bg-secondary text-secondary-foreground hover:bg-muted border border-border'
        }`}>
        {cta} <ChevronRight className="h-4 w-4" />
      </Link>
    </div>
  )
}

export default function LandingPage() {
  const [mobileOpen, setMobileOpen] = useState(false)

  const features = [
    { icon: Globe, title: '4-Layer Intelligent Crawler', color: 'bg-primary/10 text-primary', description: 'Jina AI → Crawl4AI + Camoufox → ScrapFly fallback. Crawls any site reliably, bypasses anti-bot protection automatically.' },
    { icon: Cpu, title: 'Claude AI Analysis', color: 'bg-cyan-500/10 text-cyan-500', description: 'Every page analyzed by Claude. Confidence scores, exact fix instructions, and business impact scoring.' },
    { icon: Wrench, title: 'One-Click Auto-Fix', color: 'bg-green-500/10 text-green-500', description: 'WordPress, Shopify, Webflow, and GitHub integrations. AutoSEO writes the fix directly to your CMS.' },
    { icon: Shield, title: 'Enterprise Security', color: 'bg-violet-500/10 text-violet-500', description: 'AES-256-GCM encrypted credentials, row-level security, append-only audit logs, GDPR compliance.' },
    { icon: BarChart3, title: 'Score Trend Tracking', color: 'bg-amber-500/10 text-amber-500', description: 'Track SEO health across 30, 90, 365 days. Generate client-ready PDF reports in seconds.' },
    { icon: Code2, title: 'JS Snippet Monitor', color: 'bg-rose-500/10 text-rose-500', description: '3KB embed captures real-user Core Web Vitals, live metadata snapshots, and sends instant alerts.' },
  ]

  const steps = [
    { n: '01', icon: Globe, title: 'Connect your site', body: 'Paste your URL and select your CMS. AutoSEO supports WordPress, Shopify, Webflow, and GitHub. Setup takes under 60 seconds.' },
    { n: '02', icon: Cpu, title: 'AI finds every issue', body: 'Our 4-layer crawler maps every page. Claude AI scores each issue by impact and prepares the exact fix code.' },
    { n: '03', icon: Zap, title: 'Apply fixes in one click', body: 'Review AI-drafted fixes in your dashboard. Approve, and AutoSEO pushes the change to your CMS, then re-crawls to verify.' },
  ]

  const plans = [
    { tier: 'Starter', price: 'Free', description: '1 site, full audit — no credit card required.', features: ['1 site', '500 pages per crawl', 'Weekly scheduled crawls', 'Issue detection & scoring', 'Email reports'], cta: 'Start for Free' },
    { tier: 'Pro', price: '$49', freq: '/mo', description: 'Full AI automation for growing teams.', featured: true, features: ['10 sites', '5,000 pages per crawl', 'Daily crawls', 'AI auto-fix (WP, Shopify, Webflow)', 'GitHub PR integration', 'PDF reports', 'Slack & email alerts'], cta: 'Start Pro Trial' },
    { tier: 'Agency', price: '$149', freq: '/mo', description: 'White-glove automation at scale.', features: ['Unlimited sites', '50,000 pages per crawl', 'Hourly crawls', 'All CMS integrations', 'Full API access', 'Priority support', 'Custom branded reports'], cta: 'Contact Sales' },
  ]

  return (
    <div className="min-h-screen bg-background text-foreground">

      {/* ── Navbar ── */}
      <nav className="fixed top-0 left-0 right-0 z-50 h-16 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold tracking-tight text-foreground">AutoSEO</span>
            <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 text-[10px] font-bold uppercase tracking-wider">Beta</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {[['#features', 'Features'], ['#how', 'How it works'], ['#pricing', 'Pricing']].map(([href, label]) => (
              <a key={label} href={href} className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted transition-colors">{label}</a>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link to="/login" className="hidden sm:flex h-9 px-4 items-center text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors">Sign in</Link>
            <Link to="/signup" className="h-9 px-4 flex items-center gap-1.5 text-sm font-semibold rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white shadow-lg shadow-cyan-500/25 transition-all">
              Get started <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <button className="md:hidden h-9 w-9 flex items-center justify-center rounded-lg text-muted-foreground hover:bg-muted" onClick={() => setMobileOpen(!mobileOpen)}>
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div className="md:hidden border-t border-border bg-background px-4 py-3 space-y-1">
            {[['#features', 'Features'], ['#how', 'How it works'], ['#pricing', 'Pricing']].map(([href, label]) => (
              <a key={label} href={href} onClick={() => setMobileOpen(false)} className="block px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg">{label}</a>
            ))}
            <Link to="/login" onClick={() => setMobileOpen(false)} className="block px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg">Sign in</Link>
          </div>
        )}
      </nav>

      {/* ── Hero ── */}
      <section className="relative min-h-[90vh] flex items-center overflow-hidden pt-16">
        <div className="absolute inset-0 hero-grid opacity-50" />
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-600/5" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 z-10">
          <div className="flex flex-col lg:flex-row items-center gap-16">
            <div className="flex-1 lg:max-w-[55%]">
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 mb-8">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500" style={{ boxShadow: '0 0 0 3px rgba(34,197,94,0.2)' }} />
                <span className="text-xs font-semibold text-primary">AI-Powered SEO Automation</span>
              </motion.div>

              <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.08 }}
                className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.05] mb-6">
                <span className="text-foreground">SEO on </span>
                <span className="gradient-text">Autopilot.</span>
                <br />
                <span className="text-foreground">You Stay </span>
                <span className="text-muted-foreground">Focused.</span>
              </motion.h1>

              <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.16 }}
                className="text-lg text-muted-foreground mb-10 max-w-lg leading-relaxed">
                AutoSEO crawls every page with a 4-layer intelligent engine, analyzes issues with Claude AI,
                and writes the fix directly to your CMS — with your approval.
              </motion.p>

              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.24 }}
                className="flex flex-col sm:flex-row gap-3 mb-12">
                <Link to="/signup" className="inline-flex items-center justify-center gap-2 h-12 px-6 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all text-base">
                  Start for Free <ArrowRight className="h-4 w-4" />
                </Link>
                <Link to="/dashboard" className="inline-flex items-center justify-center gap-2 h-12 px-6 rounded-lg border border-border bg-card text-foreground font-semibold hover:bg-muted transition-all text-base">
                  <Activity className="h-4 w-4 text-muted-foreground" /> View Dashboard
                </Link>
              </motion.div>

              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.4 }}
                className="flex items-center gap-4">
                <div className="flex -space-x-2.5">
                  {['A','K','M','J','S'].map((c, i) => (
                    <div key={i} className="w-9 h-9 rounded-full border-2 border-background flex items-center justify-center text-xs font-bold text-white"
                      style={{ background: ['#0ea5e9','#22d3ee','#34d399','#a78bfa','#f59e0b'][i] }}>
                      {c}
                    </div>
                  ))}
                </div>
                <div>
                  <div className="flex items-center gap-0.5 mb-0.5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star key={i} className="h-3.5 w-3.5" style={{ fill: '#f59e0b', color: '#f59e0b' }} />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground font-medium">Loved by 847+ SEO teams</p>
                </div>
              </motion.div>
            </div>

            <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.1, ease: [0.34, 1.56, 0.64, 1] }}
              className="hidden lg:flex flex-shrink-0">
              <HeroOrb />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── Stats ── */}
      <section className="border-y border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { to: 12400, suffix: '+', label: 'Issues auto-fixed' },
              { to: 847, suffix: '', label: 'Sites monitored' },
              { to: 98, suffix: '%', label: 'Fix success rate' },
              { to: 4, suffix: '', label: 'Crawler layers' },
            ].map((s, i) => (
              <motion.div key={s.label} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                className="text-center">
                <div className="text-4xl font-bold gradient-text mb-2 tracking-tight">
                  <Counter to={s.to} suffix={s.suffix} />
                </div>
                <p className="text-sm text-muted-foreground">{s.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Logo bar ── */}
      <section className="py-12 border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs font-medium uppercase tracking-wider text-muted-foreground mb-8">Auto-fix for every major CMS</p>
          <div className="flex items-center justify-center gap-10 flex-wrap">
            {['Shopify', 'WordPress', 'Webflow', 'GitHub', 'Slack', 'Notion'].map((logo) => (
              <span key={logo} className="text-sm font-semibold text-muted-foreground/60">{logo}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-16 max-w-2xl">
            <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
              className="text-xs font-semibold uppercase tracking-wider text-primary mb-4">Platform</motion.p>
            <motion.h2 initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              className="text-3xl md:text-5xl font-bold tracking-tight text-foreground mb-4">
              Autonomous SEO,<br />end to end.
            </motion.h2>
            <motion.p initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              transition={{ delay: 0.08 }}
              className="text-lg text-muted-foreground leading-relaxed">
              From intelligent crawling to AI-crafted fixes applied directly to your CMS — AutoSEO handles the complete loop.
            </motion.p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <motion.div key={f.title} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }} transition={{ delay: i * 0.07, duration: 0.5 }}>
                <FeatureCard {...f} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how" className="py-24 md:py-32 border-y border-border bg-muted/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-20 max-w-xl mx-auto">
            <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
              className="text-xs font-semibold uppercase tracking-wider text-primary mb-4">How it works</motion.p>
            <motion.h2 initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              className="text-3xl md:text-5xl font-bold tracking-tight text-foreground">
              Three steps to zero SEO issues
            </motion.h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {steps.map((s, i) => (
              <motion.div key={s.n} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ delay: i * 0.12, duration: 0.5 }}>
                <div className="bg-card border border-border rounded-xl p-6 h-full">
                  <div className="flex items-center gap-4 mb-5">
                    <div className="w-10 h-10 rounded-full border border-primary/30 flex items-center justify-center bg-primary/5 flex-shrink-0">
                      <span className="text-sm font-bold text-primary">{s.n}</span>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                      <s.icon className="h-5 w-5 text-primary" />
                    </div>
                  </div>
                  <h3 className="text-base font-semibold text-foreground mb-2">{s.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{s.body}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="py-24 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 max-w-xl mx-auto">
            <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
              className="text-xs font-semibold uppercase tracking-wider text-primary mb-4">Pricing</motion.p>
            <motion.h2 initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              className="text-3xl md:text-5xl font-bold tracking-tight text-foreground mb-4">
              Simple, transparent pricing
            </motion.h2>
            <motion.p initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
              className="text-lg text-muted-foreground">
              Start free forever. Upgrade when you need automation.
            </motion.p>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {plans.map((p, i) => (
              <motion.div key={p.tier} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ delay: i * 0.1 }}>
                <PricingCard {...p} />
              </motion.div>
            ))}
          </div>
          <p className="text-center mt-10 text-sm text-muted-foreground">
            All plans include SSL crawling, issue history, API access, and free onboarding.
          </p>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="py-24 md:py-32 border-t border-border relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-600/5" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-primary/5 rounded-full blur-3xl" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            className="max-w-2xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 mb-8">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs font-semibold text-primary">Free forever plan available</span>
            </div>
            <h2 className="text-4xl md:text-6xl font-bold tracking-tight text-foreground mb-6">
              Ready to automate<br />your SEO?
            </h2>
            <p className="text-lg text-muted-foreground mb-10">
              Join 847 teams already using AutoSEO to fix issues faster, rank higher, and reclaim their time.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/signup" className="inline-flex items-center justify-center gap-2 h-12 px-8 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold shadow-lg shadow-cyan-500/25 transition-all text-base">
                Start for Free Today <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/dashboard" className="inline-flex items-center justify-center gap-2 h-12 px-8 rounded-lg border border-border bg-card text-foreground font-semibold hover:bg-muted transition-all text-base">
                <Play className="h-4 w-4 text-muted-foreground" /> See the Dashboard
              </Link>
            </div>
            <p className="mt-6 text-sm text-muted-foreground">No credit card. 1 site free forever.</p>
          </motion.div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-5">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-600">
                <Zap className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="text-sm font-semibold text-foreground">AutoSEO</span>
              <span className="text-sm text-muted-foreground">© 2026</span>
            </div>
            <div className="flex items-center gap-6">
              {['Privacy', 'Terms', 'Docs', 'Status'].map((label) => (
                <a key={label} href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">{label}</a>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
