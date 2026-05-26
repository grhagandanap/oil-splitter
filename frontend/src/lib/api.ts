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

  if (
    !(options.body instanceof URLSearchParams) &&
    !(options.body instanceof FormData)
  ) {
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

// ── Project types & API ──────────────────────────────────────────────────────

export type ProjectStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type FileType = 'marker' | 'well' | 'production' | 'completion' | 'lumping'

export interface ProjectResponse {
  id: string
  name: string
  description: string | null
  status: ProjectStatus
  created_at: string
}

export interface DataFileResponse {
  id: string
  project_id: string
  file_type: FileType
  original_filename: string
  sheet_name: string | null
  storage_path: string
  uploaded_at: string
}

export interface ProjectWithFiles extends ProjectResponse {
  files: DataFileResponse[]
}

export interface ExecutionHistoryResponse {
  id: string
  project_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  result_file_url: string | null
  logs: string | null
  executed_at: string
}

export const projectsApi = {
  list: () => api.get<ProjectResponse[]>('/projects/'),

  create: (name: string, description?: string) =>
    api.post<ProjectResponse>('/projects/', { name, description }),

  get: (id: string) => api.get<ProjectWithFiles>(`/projects/${id}`),

  update: (id: string, data: { name?: string; description?: string }) =>
    request<ProjectResponse>(`/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),

  uploadFile: (projectId: string, fileType: FileType, file: File, sheetName?: string) => {
    const form = new FormData()
    form.append('file', file)
    const qs = sheetName ? `?sheet_name=${encodeURIComponent(sheetName)}` : ''
    return request<DataFileResponse>(
      `/projects/${projectId}/files/${fileType}${qs}`,
      { method: 'POST', body: form }
    )
  },

  listFiles: (projectId: string) =>
    api.get<DataFileResponse[]>(`/projects/${projectId}/files`),

  getHistory: (projectId: string) =>
    api.get<ExecutionHistoryResponse[]>(`/projects/${projectId}/history`),

  execute: (projectId: string) =>
    request<ExecutionHistoryResponse>(`/projects/${projectId}/execute`, { method: 'POST' }),

  downloadResult: (projectId: string, executionId: string) =>
    `${API_URL}/projects/${projectId}/history/${executionId}/download`,
}
