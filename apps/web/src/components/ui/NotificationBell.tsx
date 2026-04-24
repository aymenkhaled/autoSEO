import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Bell, CheckCircle2, ExternalLink, FileText, RefreshCw, X } from 'lucide-react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { notificationsApi } from '@/lib/api-client'

const ICON_MAP: Record<string, { icon: any; color: string }> = {
  issue_critical: { icon: Bell, color: 'text-red-500 bg-red-500/10' },
  fix_applied: { icon: CheckCircle2, color: 'text-green-500 bg-green-500/10' },
  crawl_complete: { icon: RefreshCw, color: 'text-cyan-500 bg-cyan-500/10' },
  'crawl.completed': { icon: RefreshCw, color: 'text-cyan-500 bg-cyan-500/10' },
  'fix.pr_created': { icon: ExternalLink, color: 'text-blue-500 bg-blue-500/10' },
  'fix.deployed': { icon: CheckCircle2, color: 'text-green-500 bg-green-500/10' },
  'fix.apply_failed': { icon: AlertTriangle, color: 'text-amber-500 bg-amber-500/10' },
  'webhook.delivery': { icon: FileText, color: 'text-blue-500 bg-blue-500/10' },
  info: { icon: FileText, color: 'text-blue-500 bg-blue-500/10' },
}

function notificationTarget(notification: any) {
  const data = notification?.data || {}
  if (data.issue_id) return '/dashboard/fixes'
  if (data.webhook_id) return '/dashboard/integrations'
  if (data.site_id) return `/dashboard/sites/${data.site_id}`
  if (notification?.type === 'webhook.delivery') return '/dashboard/integrations'
  if (notification?.type?.startsWith('fix.')) return '/dashboard/fixes'
  if (notification?.type?.startsWith('crawl.')) return '/dashboard/sites'
  return '/dashboard/settings'
}

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
  const ref = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ['notifications-bell'],
    queryFn: () => notificationsApi.list(),
  })

  const markAllRead = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications-bell'] }),
  })

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications-bell'] }),
  })

  const notifications = data?.notifications ?? []
  const unread = data?.unread_count ?? 0

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-all"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500 ring-2 ring-background" />}
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
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground">Notifications</span>
                {unread > 0 && <span className="text-xs font-bold bg-red-500 text-white px-1.5 py-0.5 rounded-full">{unread}</span>}
              </div>
              {unread > 0 && (
                <button onClick={() => markAllRead.mutate()} className="text-xs text-muted-foreground hover:text-primary transition-colors">
                  Mark all read
                </button>
              )}
            </div>

            <div className="max-h-80 overflow-y-auto divide-y divide-border">
              {notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center px-4">
                  <Bell className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm font-medium text-foreground">All caught up</p>
                  <p className="text-xs text-muted-foreground mt-1">No notifications right now.</p>
                </div>
              ) : (
                notifications.map((notification: any) => {
                  const iconCfg = ICON_MAP[notification.type] ?? ICON_MAP.info
                  const Icon = iconCfg.icon
                  const target = notificationTarget(notification)
                  return (
                    <div
                      key={notification.id}
                      className={`flex items-start gap-3 p-4 transition-colors cursor-pointer ${notification.read ? '' : 'bg-primary/3'} hover:bg-muted/50`}
                      onClick={() => markRead.mutate(notification.id)}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${iconCfg.color}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold leading-tight text-foreground">
                          {!notification.read && <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary mr-1.5 mb-0.5 align-middle" />}
                          {notification.title}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{notification.body}</p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[10px] text-muted-foreground">
                            {notification.created_at ? timeAgo(notification.created_at) : 'just now'}
                          </span>
                          <Link to={target} className="text-[10px] text-primary hover:underline flex items-center gap-0.5" onClick={() => setOpen(false)}>
                            View <ExternalLink className="h-2.5 w-2.5" />
                          </Link>
                        </div>
                      </div>
                      <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0">
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  )
                })
              )}
            </div>

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
