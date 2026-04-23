import { screen } from '@testing-library/react'
import { vi } from 'vitest'

import LoginPage from '@/pages/LoginPage'
import { renderWithProviders } from '@/test/test-utils'

const useAuthMock = vi.fn()

vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => useAuthMock(),
}))

vi.mock('next-themes', () => ({
  useTheme: () => ({ theme: 'dark', setTheme: vi.fn() }),
  ThemeProvider: ({ children }: any) => children,
}))

describe('LoginPage auth modes', () => {
  it('hides Google sign-in in local auth mode', () => {
    useAuthMock.mockReturnValue({
      authMode: 'local_jwt',
      supportsGoogleAuth: false,
      signIn: vi.fn(),
      signInWithGoogle: vi.fn(),
    })

    renderWithProviders(<LoginPage />)

    expect(screen.getByText(/Local email\/password auth is active/i)).toBeInTheDocument()
    expect(screen.queryByText(/Continue with Google/i)).not.toBeInTheDocument()
  })

  it('shows Google sign-in in Supabase mode', () => {
    useAuthMock.mockReturnValue({
      authMode: 'supabase',
      supportsGoogleAuth: true,
      signIn: vi.fn(),
      signInWithGoogle: vi.fn(),
    })

    renderWithProviders(<LoginPage />)

    expect(screen.getByText(/Supabase browser auth is active/i)).toBeInTheDocument()
    expect(screen.getByText(/Continue with Google/i)).toBeInTheDocument()
  })
})
