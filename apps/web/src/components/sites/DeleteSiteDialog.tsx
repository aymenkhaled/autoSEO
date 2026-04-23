import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Loader2, Trash2, X } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { sitesApi } from '@/lib/api-client'

function errorMessage(error: any) {
  const detail = error?.parsed?.detail ?? error?.response?.data?.detail ?? error?.response?.detail ?? error?.message
  if (typeof detail === 'string') return detail
  if (detail?.message) return detail.message
  return 'Site deletion failed.'
}

export function DeleteSiteDialog({
  site,
  open,
  onClose,
  onDeleted,
}: {
  site: any | null
  open: boolean
  onClose: () => void
  onDeleted?: (result: any) => void
}) {
  const queryClient = useQueryClient()
  const [confirmation, setConfirmation] = useState('')
  const [serverError, setServerError] = useState<string | null>(null)

  const expected = useMemo(() => site?.name || '', [site?.name])
  const canDelete = !!site && confirmation.trim() === expected

  const deleteSite = useMutation({
    mutationFn: async (id: string) => {
      try {
        return await sitesApi.delete(id)
      } catch (error: any) {
        if (error?.response) {
          let parsed = null
          try {
            parsed = await error.response.json()
          } catch {
            parsed = null
          }
          throw { parsed, message: error?.message, response: error?.response }
        }
        throw error
      }
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['sites'] })
      queryClient.invalidateQueries({ queryKey: ['site', site?.id] })
      queryClient.invalidateQueries({ queryKey: ['site-summary', site?.id] })
      setServerError(null)
      toast.success(result?.message || 'Site deleted')
      onDeleted?.(result)
      onClose()
      setConfirmation('')
    },
    onError: (error: any) => {
      setServerError(errorMessage(error))
      toast.error(errorMessage(error))
    },
  })

  const handleClose = () => {
    if (deleteSite.isPending) return
    setServerError(null)
    setConfirmation('')
    onClose()
  }

  if (!open || !site) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          className="relative z-10 w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl bg-red-500/10 text-red-500">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-foreground">Delete site permanently</h2>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  This removes the site, crawls, pages, issues, reports, keywords, competitors, snippet data, and related history.
                </p>
              </div>
            </div>
            <button onClick={handleClose} className="text-muted-foreground hover:text-foreground transition-colors">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-5 rounded-xl border border-border bg-muted/20 p-4 space-y-2">
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Site</p>
              <p className="text-sm font-medium text-foreground mt-1">{site.name}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{site.domain}</p>
            </div>
            <p className="text-xs text-muted-foreground">
              To confirm, type <span className="font-semibold text-foreground">{expected}</span>.
            </p>
          </div>

          {serverError && (
            <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-xs text-red-300">
              {serverError}
            </div>
          )}

          <div className="mt-4">
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Confirmation text</label>
            <input
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              placeholder={expected}
              className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-red-500/30"
            />
          </div>

          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 h-10 rounded-lg border border-border text-sm text-muted-foreground hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => site?.id && deleteSite.mutate(site.id)}
              disabled={!canDelete || deleteSite.isPending}
              className="flex-1 inline-flex items-center justify-center gap-2 h-10 rounded-lg bg-red-500 text-white text-sm font-semibold hover:bg-red-600 transition-colors disabled:opacity-50"
            >
              {deleteSite.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              {deleteSite.isPending ? 'Deleting...' : 'Delete site'}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
