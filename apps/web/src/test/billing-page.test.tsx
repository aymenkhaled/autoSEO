import { screen } from '@testing-library/react'
import { vi } from 'vitest'

import BillingPage from '@/pages/BillingPage'
import { renderWithProviders } from '@/test/test-utils'

const usageJsonMock = vi.fn()
const readinessMock = vi.fn()

vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: () => ({ json: () => usageJsonMock() }),
  },
  systemApi: {
    readiness: () => readinessMock(),
  },
}))

describe('BillingPage truthfulness', () => {
  it('disables unfinished billing actions and shows readiness state', async () => {
    usageJsonMock.mockResolvedValue({
      plan: 'free',
      usage: {
        sites: { used: 1, limit: 1 },
        crawls: { used: 2, limit: 5 },
        ai_fixes: { used: 0, limit: 10 },
      },
      ai_cost: { cost_usd: 0, tokens: 0 },
    })
    readinessMock.mockResolvedValue({
      features: {
        billing: {
          state: 'saved_only',
          label: 'Stripe wiring deferred',
          description: 'Billing state is visible, but checkout and portal actions stay disabled.',
        },
      },
    })

    renderWithProviders(<BillingPage />)

    expect(await screen.findByText(/Stripe wiring deferred/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Checkout not wired yet/i).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Billing portal not wired yet/i })).toBeDisabled()
  })
})
