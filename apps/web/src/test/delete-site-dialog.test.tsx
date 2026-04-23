import { fireEvent, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { DeleteSiteDialog } from '@/components/sites/DeleteSiteDialog'
import { renderWithProviders } from '@/test/test-utils'

const deleteMock = vi.fn()

vi.mock('@/lib/api-client', () => ({
  sitesApi: {
    delete: (id: string) => deleteMock(id),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('DeleteSiteDialog', () => {
  it('shows server conflict details when delete is blocked', async () => {
    deleteMock.mockRejectedValue({
      response: {
        json: async () => ({
          detail: {
            message: 'This site still has an active crawl. Cancel it first.',
          },
        }),
      },
      message: 'Delete failed',
    })

    renderWithProviders(
      <DeleteSiteDialog
        site={{ id: 'site-1', name: 'Strategy', domain: 'https://strategy.test' }}
        open
        onClose={vi.fn()}
      />,
    )

    fireEvent.change(screen.getByPlaceholderText('Strategy'), { target: { value: 'Strategy' } })
    fireEvent.click(screen.getByRole('button', { name: /Delete site/i }))

    await waitFor(() => {
      expect(screen.getByText(/active crawl/i)).toBeInTheDocument()
    })
  })
})
