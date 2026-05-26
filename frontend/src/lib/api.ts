const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const getToken = (): string | null =>
  typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

export const setToken = (token: string): void =>
  localStorage.setItem('access_token', token)

export const removeToken = (): void =>
  localStorage.removeItem('access_token')

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  if (!(options.body instanceof URLSearchParams)) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }

  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: string
  email: string
  created_at: string
}

export const authApi = {
  register: (email: string, password: string) =>
    api.post<UserResponse>('/auth/register', { email, password }),

  login: (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password })
    return request<AuthResponse>('/auth/login', {
      method: 'POST',
      body,
    })
  },

  me: () => api.get<UserResponse>('/auth/me'),
}
