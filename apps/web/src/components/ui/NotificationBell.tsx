import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell, Bug, CheckCircle2, AlertTriangle, FileText,
  X, ExternalLink, RefreshCw,
} from 'lucide-react'
import { Link } from 'react-router'

interface AppNotification {
  id: string
  type: 'issue_critical' | 'fix_applied' | 'crawl_complete' | 'info'
  title: string
  message: string
  link?: string
  read: boolean
  created_at: string
}

const ICON_MAP = {
  issue_critical: { icon: AlertTriangle, color: 'text-red-500 bg-red-500/10' },
  fix_applied: { icon: CheckCircle2, color: 'text-green-500 bg-green-500/10' },
  crawl_complete: { icon: RefreshCw, color: 'text-cyan-500 bg-cyan-500/10' },
  info: { icon: FileText, color: 'text-blue-500 bg-blue-500/10' },
}

// Sample notifications — in production these come from /notifications API
const SAMPLE: AppNotification[] = [
  {
    id: '1',
    type: 'issue_critical',
    title: 'Critical issue detected',
    message: 'Broken internal link found on /services page.',
    link: '/dashboard/issues',
    read: false,
    created_at: new Date(Date.now() - 3 * 60000).toISOString(),
  },
  {
    id: '2',
    type: 'fix_applied',
    title: 'Fix applied successfully',
    message: 'Meta description updated on /about via WordPress API.',
    link: '/dashboard/fixes',
    read: false,
    created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: '3',
    type: 'crawl_complete',
    title: 'Crawl completed',
    message: '247 pages crawled. 23 new issues found.',
    link: '/dashboard/sites',
    read: true,
    created_at: new Date(Date.now() - 5 * 3600000).toISOString(),
  },
  {
    id: '4',
    type: 'fix_applied',
    title: 'Bulk fix applied',
    message: '8 missing alt texts filled automatically.',
    link: '/dashboard/fixes',
    read: true,
    created_at: new Date(Date.now() - 24 * 3600000).toISOString(),
  },
]

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState(SAMPLE)
  const ref = useRef<HTMLDivElement>(null)

  const unread = notifications.filter(n => !n.read).length

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const markAllRead = () => setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  const markRead = (id: string) => setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
  const dismiss = (id: string) => setNotifications(prev => prev.filter(n => n.id !== id))

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500 ring-2 ring-background" />
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-10 w-80 rounded-xl border border-border bg-card shadow-xl shadow-black/10 z-50 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground">Notifications</span>
                {unread > 0 && (
                  <span className="text-xs font-bold bg-red-500 text-white px-1.5 py-0.5 rounded-full">
                    {unread}
                  </span>
                )}
              </div>
              {unread > 0 && (
                <button onClick={markAllRead} className="text-xs text-muted-foreground hover:text-primary transition-colors">
                  Mark all read
                </button>
              )}
            </div>

            {/* Items */}
            <div className="max-h-80 overflow-y-auto divide-y divide-border">
              {notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center px-4">
                  <Bell className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm font-medium text-foreground">All caught up!</p>
                  <p className="text-xs text-muted-foreground mt-1">No notifications right now.</p>
                </div>
              ) : (
                notifications.map((n) => {
                  const { icon: Icon, color } = ICON_MAP[n.type]
                  return (
                    <div
                      key={n.id}
                      className={`flex items-start gap-3 p-4 transition-colors cursor-pointer ${n.read ? '' : 'bg-primary/3'} hover:bg-muted/50`}
                      onClick={() => markRead(n.id)}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${color}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`text-xs font-semibold leading-tight ${n.read ? 'text-foreground' : 'text-foreground'}`}>
                            {!n.read && <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary mr-1.5 mb-0.5 align-middle" />}
                            {n.title}
                          </p>
                          <button
                            onClick={(e) => { e.stopPropagation(); dismiss(n.id) }}
                            className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{n.message}</p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[10px] text-muted-foreground">{timeAgo(n.created_at)}</span>
                          {n.link && (
                            <Link to={n.link} className="text-[10px] text-primary hover:underline flex items-center gap-0.5" onClick={() => setOpen(false)}>
                              View <ExternalLink className="h-2.5 w-2.5" />
                            </Link>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2.5 border-t border-border bg-muted/20">
              <Link to="/dashboard/settings" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
                Manage notification preferences →
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
