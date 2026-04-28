import { api } from '#/lib/api'
import { tokenStore } from '#/lib/auth-storage'

import type { LoginPayload, RegisterPayload, TokenPair, User } from './types'

export async function login(payload: LoginPayload): Promise<TokenPair> {
  const tokens = await api.post('auth/login', { json: payload }).json<TokenPair>()
  tokenStore.set(tokens.access_token, tokens.refresh_token)
  return tokens
}

export async function register(payload: RegisterPayload): Promise<User> {
  return api.post('auth/register', { json: payload }).json<User>()
}

export async function fetchMe(): Promise<User> {
  return api.get('auth/me').json<User>()
}

export function logout() {
  tokenStore.clear()
}
