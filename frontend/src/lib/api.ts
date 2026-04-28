/**
 * `ky` HTTP client configured for the FastAPI backend.
 *
 * Hooks attach the JWT access token from `tokenStore` and transparently
 * refresh-and-retry once on a 401 response, so feature code can stay focused
 * on the request/response shape.
 */

import ky, { HTTPError } from 'ky'

import { tokenStore } from './auth-storage'

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  'http://localhost:8000/api/v1'

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.getRefresh()
  if (!refresh) return null

  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    try {
      const data = await ky
        .post(`${API_BASE_URL}/auth/refresh`, {
          json: { refresh_token: refresh },
          throwHttpErrors: true,
        })
        .json<{ access_token: string; refresh_token: string }>()
      tokenStore.set(data.access_token, data.refresh_token)
      return data.access_token
    } catch {
      tokenStore.clear()
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export const api = ky.create({
  baseUrl: API_BASE_URL.endsWith('/') ? API_BASE_URL : `${API_BASE_URL}/`,
  timeout: 30_000,
  hooks: {
    beforeRequest: [
      ({ request }) => {
        const access = tokenStore.getAccess()
        if (access) request.headers.set('Authorization', `Bearer ${access}`)
      },
    ],
    afterResponse: [
      async ({ request, response }) => {
        if (response.status !== 401) return response
        const url = request.url
        if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
          return response
        }
        const fresh = await refreshAccessToken()
        if (!fresh) return response
        const retryRequest = new Request(request, {
          headers: new Headers(request.headers),
        })
        retryRequest.headers.set('Authorization', `Bearer ${fresh}`)
        return fetch(retryRequest)
      },
    ],
  },
})

/**
 * Best-effort extraction of the backend's `detail` error message from a
 * `ky` `HTTPError`.
 */
export async function readErrorMessage(error: unknown): Promise<string> {
  if (error instanceof HTTPError) {
    try {
      const body = (await error.response.clone().json()) as {
        detail?: string | { msg?: string }[]
      }
      if (typeof body.detail === 'string') return body.detail
      if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        return body.detail[0].msg
      }
    } catch {
      // ignore parse errors
    }
    return error.response.statusText || 'Request failed'
  }
  if (error instanceof Error) return error.message
  return 'Unexpected error'
}

export { HTTPError }
