import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, Mail, Lock, User, ArrowRight, Eye, EyeOff, CheckCircle2, Sun, Moon, MailCheck } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useAuth } from '@/hooks/use-auth'

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="h-9 w-9 rounded-lg flex items-center justify-center border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-muted transition-all relative"
      aria-label="Toggle theme"
    >
      <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
    </button>
  )
}

export default function SignupPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [agreed, setAgreed] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [emailSent, setEmailSent] = useState(false)
  const { signUp, signInWithGoogle } = useAuth()
  const navigate = useNavigate()

  const pwStrength = password.length === 0 ? 0 : password.length < 6 ? 1 : password.length < 10 ? 2 : 3
  const pwColors = ['', 'bg-red-500', 'bg-amber-500', 'bg-green-500']
  const pwLabels = ['', 'Weak', 'Fair', 'Strong']

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!agreed) { setError('Please agree to the terms to continue'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setError('')
    setLoading(true)
    try {
      const data = await signUp(email, password, name)
      if (data.session) {
        // Email confirmation is disabled — user is immediately logged in
        navigate('/dashboard', { replace: true })
      } else {
        // Email confirmation is required — show check-email state
        setEmailSent(true)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create account')
    } finally {
      setLoading(false)
    }
  }

  if (emailSent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md text-center space-y-6"
        >
          <div className="flex justify-center">
            <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
              <MailCheck className="h-8 w-8 text-cyan-500" />
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground mb-2">Check your email</h1>
            <p className="text-muted-foreground text-sm leading-relaxed">
              We sent a confirmation link to <span className="font-medium text-foreground">{email}</span>.
              Click the link in that email to activate your account and sign in.
            </p>
          </div>
          <div className="rounded-xl border border-border bg-muted/40 p-4 text-left space-y-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Didn't receive it?</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Check your spam or junk folder</li>
              <li>• Make sure <span className="text-foreground font-medium">{email}</span> is correct</li>
              <li>• Allow up to 2 minutes for delivery</li>
            </ul>
          </div>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 text-sm text-primary hover:underline font-medium"
          >
            Back to sign in
          </Link>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left — branding panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-cyan-950 to-slate-900 relative overflow-hidden flex-col justify-between p-12">
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 70% 40%, rgba(6,182,212,0.15), transparent)' }} />
        <div className="absolute bottom-1/4 left-1/4 w-72 h-72 bg-blue-600/10 rounded-full blur-3xl" />

        <div className="relative z-10">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/30">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-base font-bold text-white tracking-tight">AutoSEO</span>
          </Link>
        </div>

        <div className="relative z-10 space-y-6">
          <h2 className="text-4xl font-bold text-white tracking-tight leading-tight">
            Automate your SEO.<br />
            <span className="text-cyan-400">Free forever.</span>
          </h2>
          <ul className="space-y-3">
            {[
              'Crawl up to 500 pages per site',
              'AI-powered issue detection',
              'One-click fixes for any CMS',
              'No credit card required',
            ].map((item) => (
              <li key={item} className="flex items-center gap-3">
                <CheckCircle2 className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                <span className="text-sm text-white/70">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative z-10 rounded-xl p-4 bg-white/5 border border-white/10 backdrop-blur-sm">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">K</div>
            <div>
              <p className="text-sm text-white/80 leading-relaxed">"AutoSEO found 340 issues and fixed 280 automatically in the first week. ROI was immediate."</p>
              <p className="text-xs text-white/40 mt-2">Kate M. — SEO Lead at TechCorp</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right — form panel */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background relative">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md space-y-5">

          <Link to="/" className="flex lg:hidden items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-600">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold text-foreground">AutoSEO</span>
          </Link>

          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground mb-1">Create your account</h1>
            <p className="text-sm text-muted-foreground">Start automating your SEO in under 60 seconds</p>
          </div>

          <AnimatePresence mode="wait">
            {error && (
              <motion.div key="error" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="px-4 py-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400">
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          <button onClick={signInWithGoogle}
            className="w-full h-11 px-4 rounded-lg text-sm font-medium border border-border bg-card text-foreground flex items-center justify-center gap-3 hover:bg-muted transition-colors">
            <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>

          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-border" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="flex-1 h-px bg-border" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium text-foreground">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <input
                  id="name" type="text" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="Jane Smith" required autoComplete="name"
                  className="w-full h-11 bg-background border border-border rounded-lg pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-foreground">Work Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <input
                  id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com" required autoComplete="email"
                  className="w-full h-11 bg-background border border-border rounded-lg pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-foreground">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <input
                  id="password" type={showPw ? 'text' : 'password'} value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 8 characters" required autoComplete="new-password"
                  className="w-full h-11 bg-background border border-border rounded-lg pl-10 pr-11 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-muted-foreground hover:text-foreground transition-colors">
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {password.length > 0 && (
                <div className="flex items-center gap-2 mt-1.5">
                  <div className="flex-1 flex gap-1">
                    {[1,2,3].map((i) => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition-all ${i <= pwStrength ? pwColors[pwStrength] : 'bg-border'}`} />
                    ))}
                  </div>
                  <span className={`text-xs font-medium ${pwStrength === 1 ? 'text-red-500' : pwStrength === 2 ? 'text-amber-500' : 'text-green-500'}`}>
                    {pwLabels[pwStrength]}
                  </span>
                </div>
              )}
            </div>

            <label className="flex items-start gap-3 cursor-pointer">
              <div className={`mt-0.5 w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center transition-all ${agreed ? 'bg-primary border-primary' : 'border-border bg-background'}`}
                onClick={() => setAgreed(!agreed)}>
                {agreed && <CheckCircle2 className="h-3 w-3 text-white" />}
              </div>
              <span className="text-xs text-muted-foreground leading-relaxed">
                I agree to the{' '}
                <Link to="/terms" className="text-primary hover:underline">Terms of Service</Link>{' '}and{' '}
                <Link to="/privacy" className="text-primary hover:underline">Privacy Policy</Link>
              </span>
            </label>

            <button type="submit" disabled={loading}
              className="w-full h-11 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed">
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : <>Create Account <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-primary hover:underline">Sign in</Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
