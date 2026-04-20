import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme } from 'next-themes'
import {
  LayoutDashboard, Globe, Bug, Wrench, BarChart3,
  Settings, Zap, ChevronLeft, ChevronRight,
  Sun, Moon, LogOut, Menu, X, Target, Swords,
  Users, Key, FileText, CreditCard, Puzzle,
} from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { useAppStore } from '@/stores/app-store'
import NotificationBell from '@/components/ui/NotificationBell'

const NAV_GROUPS = [
  {
    label: 'Overview',
    items: [
      { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
      { href: '/dashboard/analytics', icon: BarChart3, label: 'Analytics' },
    ],
  },
  {
    label: 'SEO',
    items: [
      { href: '/dashboard/sites', icon: Globe, label: 'Sites' },
      { href: '/dashboard/issues', icon: Bug, label: 'Issues' },
      { href: '/dashboard/fixes', icon: Wrench, label: 'Fixes' },
      { href: '/dashboard/keywords', icon: Target, label: 'Keywords' },
      { href: '/dashboard/competitors', icon: Swords, label: 'Competitors' },
    ],
  },
  {
    label: 'Reports',
    items: [
      { href: '/dashboard/reports', icon: FileText, label: 'Reports' },
    ],
  },
  {
    label: 'Account',
    items: [
      { href: '/dashboard/team', icon: Users, label: 'Team' },
      { href: '/dashboard/integrations', icon: Puzzle, label: 'Integrations' },
      { href: '/dashboard/api-keys', icon: Key, label: 'API Keys' },
      { href: '/dashboard/billing', icon: CreditCard, label: 'Billing' },
      { href: '/dashboard/settings', icon: Settings, label: 'Settings' },
    ],
  },
]

const NAV_ITEMS = NAV_GROUPS.flatMap(g => g.items)

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all relative"
      aria-label="Toggle theme"
    >
      <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
    </button>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const { user, signOut } = useAuth()
  const { sidebarOpen, toggleSidebar } = useAppStore()
  const [mobileOpen, setMobileOpen] = useState(false)

  const initials = user?.email?.slice(0, 2).toUpperCase() ?? '??'

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={`flex items-center h-16 px-4 border-b border-border flex-shrink-0 ${sidebarOpen ? 'gap-3' : 'justify-center'}`}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20 flex-shrink-0">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <AnimatePresence>
          {sidebarOpen && (
            <motion.span initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }} transition={{ duration: 0.2 }}
              className="text-sm font-bold tracking-tight text-foreground overflow-hidden whitespace-nowrap">
              AutoSEO
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <AnimatePresence>
              {sidebarOpen && (
                <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-widest px-3 mb-1">
                  {group.label}
                </motion.p>
              )}
            </AnimatePresence>
            <div className="space-y-0.5">
              {group.items.map((item) => {
          const active = location.pathname === item.href || (item.href !== '/dashboard' && location.pathname.startsWith(item.href))
          return (
            <Link key={item.href} to={item.href} onClick={() => setMobileOpen(false)}
              title={!sidebarOpen ? item.label : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all group relative ${
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              } ${!sidebarOpen ? 'justify-center' : ''}`}>
              {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-primary" />}
              <item.icon className={`flex-shrink-0 ${active ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'}`} style={{ height: '18px', width: '18px' }} />
              <AnimatePresence>
                {sidebarOpen && (
                  <motion.span initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }} transition={{ duration: 0.2 }}
                    className="overflow-hidden whitespace-nowrap">
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="px-3 py-3 border-t border-border flex-shrink-0">
        <div className={`flex items-center gap-3 px-2 py-2 rounded-lg ${!sidebarOpen ? 'justify-center' : ''}`}>
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0 bg-gradient-to-br from-cyan-500 to-blue-600">
            {initials}
          </div>
          <AnimatePresence>
            {sidebarOpen && (
              <motion.div initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }} transition={{ duration: 0.2 }}
                className="flex-1 min-w-0 overflow-hidden">
                <p className="text-xs font-medium text-foreground truncate">{user?.email ?? 'User'}</p>
                <p className="text-[10px] text-muted-foreground">Free plan</p>
              </motion.div>
            )}
          </AnimatePresence>
          {sidebarOpen && (
            <button onClick={signOut} title="Sign out"
              className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors flex-shrink-0">
              <LogOut className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className={`hidden lg:flex flex-col flex-shrink-0 border-r border-border bg-card transition-all duration-300 ease-in-out ${sidebarOpen ? 'w-56' : 'w-16'}`}>
        <SidebarContent />
      </aside>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="lg:hidden fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)} />
            <motion.aside initial={{ x: -256 }} animate={{ x: 0 }} exit={{ x: -256 }}
              transition={{ type: 'tween', duration: 0.25 }}
              className="lg:hidden fixed left-0 top-0 bottom-0 z-50 w-64 bg-card border-r border-border flex flex-col">
              <div className="flex items-center justify-between h-16 px-4 border-b border-border">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-600">
                    <Zap className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-sm font-bold text-foreground">AutoSEO</span>
                </div>
                <button onClick={() => setMobileOpen(false)} className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-4">
                {NAV_GROUPS.map((group) => (
                  <div key={group.label}>
                    <p className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-widest px-3 mb-1">{group.label}</p>
                    <div className="space-y-0.5">
                      {group.items.map((item) => {
                        const active = location.pathname === item.href || (item.href !== '/dashboard' && location.pathname.startsWith(item.href))
                        return (
                          <Link key={item.href} to={item.href} onClick={() => setMobileOpen(false)}
                            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${active ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-muted'}`}>
                            <item.icon className="h-4 w-4 flex-shrink-0" />
                            {item.label}
                          </Link>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </nav>
              <div className="px-3 py-3 border-t border-border">
                <div className="flex items-center gap-3 px-2 py-2">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold text-white">{initials}</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-foreground truncate">{user?.email ?? 'User'}</p>
                    <p className="text-[10px] text-muted-foreground">Free plan</p>
                  </div>
                  <button onClick={signOut} className="p-1 text-muted-foreground hover:text-foreground">
                    <LogOut className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-border bg-card/50 backdrop-blur-sm flex-shrink-0">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileOpen(true)} className="lg:hidden p-2 rounded-lg text-muted-foreground hover:bg-muted">
              <Menu className="h-5 w-5" />
            </button>
            <button onClick={toggleSidebar} className="hidden lg:flex h-8 w-8 rounded-lg items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
              aria-label="Toggle sidebar">
              {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            <NotificationBell />
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold text-white cursor-pointer">
              {initials}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 md:px-6 py-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
