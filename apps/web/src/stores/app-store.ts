import { create } from 'zustand'

interface AppState {
  // Sidebar
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  // Current site context
  currentSiteId: string | null
  setCurrentSiteId: (id: string | null) => void

  // Notifications
  notifications: Array<{
    id: string
    type: 'success' | 'error' | 'info' | 'warning'
    message: string
    timestamp: number
  }>
  addNotification: (type: 'success' | 'error' | 'info' | 'warning', message: string) => void
  clearNotification: (id: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  // Sidebar
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // Current site context
  currentSiteId: null,
  setCurrentSiteId: (id) => set({ currentSiteId: id }),

  // Notifications
  notifications: [],
  addNotification: (type, message) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        {
          id: crypto.randomUUID(),
          type,
          message,
          timestamp: Date.now(),
        },
      ],
    })),
  clearNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}))
