const LOCAL_AUTH_TOKEN_KEY = 'autoseo.local_jwt'

export function getLocalAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(LOCAL_AUTH_TOKEN_KEY)
}

export function setLocalAccessToken(token: string) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(LOCAL_AUTH_TOKEN_KEY, token)
}

export function clearLocalAccessToken() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(LOCAL_AUTH_TOKEN_KEY)
}
