import { fireEvent, screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import { vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'

import NotificationBell from '@/components/ui/NotificationBell'

const listMock = vi.fn()
const markReadMock = vi.fn()
const markAllReadMock = vi.fn()

vi.mock('@/lib/api-client', () => ({
  notificationsApi: {
    list: () => listMock(),
    markRead: (id: string) => markReadMock(id),
    markAllRead: () => markAllReadMock(),
  },
}))

function renderBell() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <NotificationBell />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('NotificationBell', () => {
  it('routes crawl notifications to the site workspace', async () => {
    listMock.mockResolvedValue({
      unread_count: 1,
      notifications: [
        {
          id: 'notif-1',
          type: 'crawl.completed',
          title: 'Crawl completed',
          body: 'Strategy finished crawling.',
          data: { site_id: 'site-123' },
          read: false,
          created_at: new Date().toISOString(),
        },
      ],
    })
    markReadMock.mockResolvedValue({ success: true })
    markAllReadMock.mockResolvedValue({ success: true })

    const { container } = renderBell()
    fireEvent.click(screen.getByLabelText(/Notifications/i))

    await waitFor(() => {
      const link = container.querySelector('a[href="/dashboard/sites/site-123"]')
      expect(link).toBeTruthy()
    })
  })
})
