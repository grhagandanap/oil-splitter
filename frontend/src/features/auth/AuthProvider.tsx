import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { tokenStore } from '#/lib/auth-storage'

import {
  fetchMe,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
} from './api'
import type { LoginPayload, RegisterPayload, User } from './types'

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

type AuthContextValue = {
  user: User | null
  status: AuthStatus
  login: (payload: LoginPayload) => Promise<User>
  register: (payload: RegisterPayload) => Promise<User>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  const refresh = useCallback(async () => {
    if (!tokenStore.getAccess()) {
      setUser(null)
      setStatus('unauthenticated')
      return
    }
    try {
      const me = await fetchMe()
      setUser(me)
      setStatus('authenticated')
    } catch {
      tokenStore.clear()
      setUser(null)
      setStatus('unauthenticated')
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(async (payload: LoginPayload) => {
    await loginRequest(payload)
    const me = await fetchMe()
    setUser(me)
    setStatus('authenticated')
    return me
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    const created = await registerRequest(payload)
    await loginRequest({ email: payload.email, password: payload.password })
    const me = await fetchMe()
    setUser(me)
    setStatus('authenticated')
    return created
  }, [])

  const logout = useCallback(() => {
    logoutRequest()
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  const value = useMemo(
    () => ({ user, status, login, register, logout, refresh }),
    [user, status, login, register, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside an <AuthProvider>')
  }
  return ctx
}
