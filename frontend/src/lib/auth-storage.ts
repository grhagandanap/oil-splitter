/**
 * Token storage helpers (SSR-safe).
 *
 * Tokens are persisted in `localStorage` so they survive page reloads. All
 * accessors are no-ops during server-side rendering where `window` is not
 * defined.
 */

const ACCESS_KEY = 'oil_splitter_access_token'
const REFRESH_KEY = 'oil_splitter_refresh_token'

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

export const tokenStore = {
  getAccess(): string | null {
    return isBrowser() ? window.localStorage.getItem(ACCESS_KEY) : null
  },
  getRefresh(): string | null {
    return isBrowser() ? window.localStorage.getItem(REFRESH_KEY) : null
  },
  set(access: string, refresh: string) {
    if (!isBrowser()) return
    window.localStorage.setItem(ACCESS_KEY, access)
    window.localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    if (!isBrowser()) return
    window.localStorage.removeItem(ACCESS_KEY)
    window.localStorage.removeItem(REFRESH_KEY)
  },
}
