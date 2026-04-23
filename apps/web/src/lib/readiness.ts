export type ReadinessState =
  | 'working'
  | 'setup_required'
  | 'monitoring_only'
  | 'tracking_only'
  | 'saved_only'
  | 'unavailable_without_provider'

export const READINESS_META: Record<ReadinessState, { label: string; className: string }> = {
  working: {
    label: 'Working',
    className: 'bg-green-500/10 text-green-500 border-green-500/20',
  },
  setup_required: {
    label: 'Setup required',
    className: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  },
  monitoring_only: {
    label: 'Monitoring only',
    className: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  },
  tracking_only: {
    label: 'Tracking only',
    className: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
  },
  saved_only: {
    label: 'Saved only',
    className: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  },
  unavailable_without_provider: {
    label: 'Needs provider',
    className: 'bg-slate-500/10 text-slate-300 border-slate-500/20',
  },
}

export function readinessMeta(state?: string) {
  return READINESS_META[(state as ReadinessState) || 'setup_required'] ?? READINESS_META.setup_required
}

export function deriveSiteCardState(site: any) {
  if (site?.status === 'crawling') {
    return { dot: 'bg-amber-500 animate-pulse', label: 'Crawling' }
  }
  if (site?.status === 'error') {
    return { dot: 'bg-red-500', label: 'Needs attention' }
  }
  if (!site?.last_crawled_at) {
    return { dot: 'bg-blue-500', label: 'Setup required' }
  }
  if (!site?.ownership_verified || site?.status === 'pending_verification') {
    return { dot: 'bg-amber-500', label: 'Verification required' }
  }
  if (site?.connection_type === 'crawler' || site?.connection_type === 'snippet') {
    return { dot: 'bg-cyan-500', label: 'Monitoring only' }
  }
  if (site?.status === 'active') {
    return { dot: 'bg-green-500', label: 'Active' }
  }
  return { dot: 'bg-slate-400', label: 'Pending setup' }
}

export function connectionSummary(site: any) {
  const connectionType = site?.connection_type || 'crawler'
  if (connectionType === 'snippet') {
    return {
      monitoringLabel: 'Snippet monitoring',
      writeLabel: 'Not configured',
    }
  }
  if (['wordpress', 'shopify', 'webflow', 'github'].includes(connectionType)) {
    return {
      monitoringLabel: 'Crawler monitoring',
      writeLabel: connectionType.charAt(0).toUpperCase() + connectionType.slice(1),
    }
  }
  return {
    monitoringLabel: 'Crawler monitoring',
    writeLabel: 'Not configured',
  }
}
