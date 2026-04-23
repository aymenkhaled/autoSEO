import { createClient } from '@supabase/supabase-js'
import { SUPABASE_AUTH_ENABLED } from '@/lib/auth-mode'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string

export const supabase = SUPABASE_AUTH_ENABLED
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null

export type SupabaseClient = typeof supabase
