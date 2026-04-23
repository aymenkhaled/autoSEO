import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import type { User, Session } from '@supabase/supabase-js'
import { AUTH_MODE, type AuthMode, SUPABASE_AUTH_ENABLED } from '@/lib/auth-mode'
import { clearLocalAccessToken, getLocalAccessToken, setLocalAccessToken } from '@/lib/auth-storage'

interface AuthUser {
  id: string
  email: string
  full_name?: string
  avatar_url?: string
}

type LocalSession = {
  access_token: string
  token_type: string
  expires_in?: number
}

type AuthSession = Session | LocalSession | null

type AuthState = {
  user: AuthUser | null
  session: AuthSession
  loading: boolean
  authMode: AuthMode
}

const INITIAL_STATE: AuthState = {
  user: null,
  session: null,
  loading: true,
  authMode: AUTH_MODE,
}

let authState: AuthState = INITIAL_STATE
let initialized = false
let initPromise: Promise<void> | null = null
const listeners = new Set<() => void>()

function notifyListeners() {
  listeners.forEach((listener) => listener())
}

function setAuthState(next: Partial<AuthState>) {
  authState = { ...authState, ...next }
  notifyListeners()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function mapSupabaseUser(user: User): AuthUser {
  return {
    id: user.id,
    email: user.email ?? '',
    full_name: user.user_metadata?.full_name,
    avatar_url: user.user_metadata?.avatar_url,
  }
}

function mapLocalUser(user: any): AuthUser {
  return {
    id: user.id,
    email: user.email ?? '',
    full_name: user.full_name ?? undefined,
    avatar_url: user.avatar_url ?? undefined,
  }
}

async function parseJsonOrDetail(response: Response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof data?.detail === 'string'
      ? data.detail
      : data?.detail?.message || data?.message || 'Request failed'
    throw new Error(detail)
  }
  return data
}

async function localGetMe(token: string) {
  const response = await fetch('/api/v1/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJsonOrDetail(response)
}

async function localAuthRequest(path: 'register' | 'login', body: Record<string, unknown>) {
  const response = await fetch(`/api/v1/auth/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrDetail(response)
}

async function initializeAuth() {
  if (initialized) {
    setAuthState({ loading: false })
    return
  }
  if (initPromise) return initPromise

  initPromise = (async () => {
    if (SUPABASE_AUTH_ENABLED && supabase) {
      const { data: { session } } = await supabase.auth.getSession()
      setAuthState({
        session,
        user: session ? mapSupabaseUser(session.user) : null,
        loading: false,
      })

      supabase.auth.onAuthStateChange((_event, nextSession) => {
        setAuthState({
          session: nextSession,
          user: nextSession ? mapSupabaseUser(nextSession.user) : null,
          loading: false,
        })
      })
      initialized = true
      return
    }

    const token = getLocalAccessToken()
    if (!token) {
      setAuthState({ session: null, user: null, loading: false })
      initialized = true
      return
    }

    try {
      const user = await localGetMe(token)
      setAuthState({
        session: { access_token: token, token_type: 'bearer' },
        user: mapLocalUser(user),
        loading: false,
      })
    } catch {
      clearLocalAccessToken()
      setAuthState({ session: null, user: null, loading: false })
    }
    initialized = true
  })().finally(() => {
    initPromise = null
  })

  return initPromise
}

async function signIn(email: string, password: string) {
  if (SUPABASE_AUTH_ENABLED && supabase) {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw new Error(error.message)
    return data
  }

  const token = await localAuthRequest('login', { email, password })
  setLocalAccessToken(token.access_token)
  const user = await localGetMe(token.access_token)
  setAuthState({
    session: token,
    user: mapLocalUser(user),
    loading: false,
  })
  return { session: token, user }
}

async function signUp(email: string, password: string, fullName: string, orgName?: string) {
  if (SUPABASE_AUTH_ENABLED && supabase) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName, org_name: orgName } },
    })
    if (error) throw new Error(error.message)
    return data
  }

  const derivedOrgName = orgName?.trim() || `${fullName.split(' ')[0] || fullName}'s Organization`
  const token = await localAuthRequest('register', {
    email,
    password,
    full_name: fullName,
    org_name: derivedOrgName,
  })
  setLocalAccessToken(token.access_token)
  const user = await localGetMe(token.access_token)
  setAuthState({
    session: token,
    user: mapLocalUser(user),
    loading: false,
  })
  return { session: token, user }
}

async function signInWithGoogle() {
  if (!SUPABASE_AUTH_ENABLED || !supabase) {
    throw new Error('Google sign-in requires Supabase browser auth to be configured.')
  }
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: `${window.location.origin}/dashboard` },
  })
  if (error) throw new Error(error.message)
}

async function signOut() {
  if (SUPABASE_AUTH_ENABLED && supabase) {
    await supabase.auth.signOut()
  } else {
    clearLocalAccessToken()
    setAuthState({ session: null, user: null, loading: false })
  }
  window.location.href = '/login'
}

async function getToken(): Promise<string | null> {
  if (SUPABASE_AUTH_ENABLED && supabase) {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ?? null
  }
  return getLocalAccessToken()
}

export function useAuth() {
  const [state, setState] = useState<AuthState>(authState)

  useEffect(() => {
    const unsubscribe = subscribe(() => setState({ ...authState }))
    void initializeAuth()
    return () => {
      unsubscribe()
    }
  }, [])

  return {
    session: state.session,
    user: state.user,
    loading: state.loading,
    authMode: state.authMode,
    supportsGoogleAuth: SUPABASE_AUTH_ENABLED,
    isAuthenticated: !!state.user,
    signIn,
    signUp,
    signInWithGoogle,
    signOut,
    getToken,
  }
}
