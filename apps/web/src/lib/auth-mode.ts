export type AuthMode = 'supabase' | 'local_jwt'

export const SUPABASE_AUTH_ENABLED = Boolean(
  import.meta.env.VITE_SUPABASE_URL && import.meta.env.VITE_SUPABASE_ANON_KEY,
)

export const AUTH_MODE: AuthMode = SUPABASE_AUTH_ENABLED ? 'supabase' : 'local_jwt'
