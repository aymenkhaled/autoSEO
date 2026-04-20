import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sitesApi, crawlsApi } from '@/lib/api-client'

// --- Sites Hooks ---
export function useSites(page = 1) {
  return useQuery({
    queryKey: ['sites', page],
    queryFn: () => sitesApi.list(page),
  })
}

export function useSite(id: string) {
  return useQuery({
    queryKey: ['sites', id],
    queryFn: () => sitesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateSite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => sitesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites'] })
    },
  })
}

export function useDeleteSite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => sitesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites'] })
    },
  })
}

// --- Crawls Hooks ---
export function useCrawls(siteId?: string) {
  return useQuery({
    queryKey: ['crawls', siteId],
    queryFn: () => crawlsApi.list(siteId),
  })
}

export function useTriggerCrawl() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (siteId: string) => crawlsApi.trigger(siteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crawls'] })
    },
  })
}
