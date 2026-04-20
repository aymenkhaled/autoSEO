import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

export function formatRelativeTime(date: string | Date): string {
  const now = new Date()
  const target = new Date(date)
  const diff = now.getTime() - target.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 30) return `${days}d ago`
  return formatDate(date)
}

export function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: 'hsl(0 84.2% 60.2%)',
    high:     'hsl(25 95% 53%)',
    medium:   'hsl(38 92% 50%)',
    low:      'hsl(217 91% 60%)',
    info:     'hsl(215 20% 65%)',
  }
  return colors[severity] || colors.info
}

export function getSeverityClass(severity: string): string {
  const classes: Record<string, string> = {
    critical: 'bg-red-500/10 text-red-500 border-red-500/20',
    high:     'bg-orange-500/10 text-orange-500 border-orange-500/20',
    medium:   'bg-amber-500/10 text-amber-500 border-amber-500/20',
    low:      'bg-blue-500/10 text-blue-500 border-blue-500/20',
    info:     'bg-slate-500/10 text-slate-500 border-slate-500/20',
  }
  return classes[severity] || classes.info
}

export function getScoreColor(score: number): string {
  if (score >= 90) return 'hsl(142 76% 36%)'
  if (score >= 70) return 'hsl(199 89% 48%)'
  if (score >= 50) return 'hsl(38 92% 50%)'
  return 'hsl(0 84.2% 60.2%)'
}

export function getScoreLabel(score: number): string {
  if (score >= 90) return 'Excellent'
  if (score >= 70) return 'Good'
  if (score >= 50) return 'Needs Work'
  return 'Poor'
}
