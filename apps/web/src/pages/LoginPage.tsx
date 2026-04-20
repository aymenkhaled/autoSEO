import { useState } from 'react'
import { useNavigate, Link } from 'react-router'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, Mail, Lock, ArrowRight, Eye, EyeOff, Sun, Moon } from 'lucide-react'
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

function friendlyError(msg: string): string {
  const m = msg.toLowerCase()
  if (m.includes('email not confirmed')) {
    return 'Please confirm your email address. Check your inbox for a confirmation link from AutoSEO.'
  }
  if (m.includes('invalid login credentials') || m.includes('invalid credentials')) {
    return 'Incorrect email or password. Please try again.'
  }
  if (m.includes('too many requests')) {
    return 'Too many attempts. Please wait a moment and try again.'
  }
  if (m.includes('user not found')) {
    return 'No account found with that email. Would you like to sign up?'
  }
  return msg
}

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { signIn, signInWithGoogle } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await signIn(email, password)
      navigate('/dashboard', { replace: true })
    } catch (err: any) {
      setError(friendlyError(err.message || 'Failed to sign in'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left — branding panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-cyan-950 to-slate-900 relative overflow-hidden flex-col justify-between p-12">
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 30% 50%, rgba(6,182,212,0.15), transparent)' }} />
        <div className="absolute top-1/3 right-1/4 w-72 h-72 bg-blue-600/10 rounded-full blur-3xl" />

        <div className="relative z-10">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/30">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-base font-bold text-white tracking-tight">AutoSEO</span>
          </Link>
        </div>

        <div className="relative z-10">
          <h2 className="text-4xl font-bold text-white mb-4 tracking-tight leading-tight">
            Welcome back.<br />
            <span className="text-cyan-400">Your SEO never sleeps.</span>
          </h2>
          <p className="text-white/60 text-base leading-relaxed">
            AutoSEO crawls, analyzes, and fixes your site automatically while you focus on what matters.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-3 relative z-10">
          {[{ v: '847', l: 'Sites' }, { v: '98%', l: 'Fix Rate' }, { v: '12K+', l: 'Fixed' }].map((s) => (
            <div key={s.l} className="rounded-xl p-3 text-center bg-white/5 border border-white/10 backdrop-blur-sm">
              <p className="text-base font-bold text-white">{s.v}</p>
              <p className="text-xs text-white/40 mt-0.5">{s.l}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right — form panel */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background relative">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md space-y-6">

          <Link to="/" className="flex lg:hidden items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-600">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold text-foreground">AutoSEO</span>
          </Link>

          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground mb-1">Welcome back</h1>
            <p className="text-sm text-muted-foreground">Sign in to your account to continue</p>
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
              <label htmlFor="email" className="text-sm font-medium text-foreground">Email</label>
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
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-sm font-medium text-foreground">Password</label>
                <a href="#" className="text-xs text-muted-foreground hover:text-primary transition-colors">Forgot password?</a>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <input
                  id="password" type={showPw ? 'text' : 'password'} value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••" required autoComplete="current-password"
                  className="w-full h-11 bg-background border border-border rounded-lg pl-10 pr-11 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-muted-foreground hover:text-foreground transition-colors">
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="w-full h-11 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed">
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : <>Sign In <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            No account?{' '}
            <Link to="/signup" className="font-semibold text-primary hover:underline">Sign up free</Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
