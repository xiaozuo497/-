import { apiClient } from './client'

export interface CurrentUser {
  id: string
  username: string
  real_name: string
  role: string
  phone?: string
  status: string
}

const USER_STORAGE_KEY = 'cold-chain-current-user'
const TOKEN_STORAGE_KEY = 'cold-chain-access-token'

export async function login(username: string, password: string) {
  const { data } = await apiClient.post<{ user: CurrentUser; access_token: string }>('/auth/login', { username, password })
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user))
  localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token)
  return data.user
}

export function getCurrentUser(): CurrentUser | null {
  const raw = localStorage.getItem(USER_STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as CurrentUser
  } catch {
    localStorage.removeItem(USER_STORAGE_KEY)
    return null
  }
}

export function getAuthToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function logout() {
  localStorage.removeItem(USER_STORAGE_KEY)
  localStorage.removeItem(TOKEN_STORAGE_KEY)
  localStorage.removeItem('cold-chain-last-solution')
  localStorage.removeItem('cold-chain-all-solutions')
}

export function isAuthenticated() {
  return Boolean(getCurrentUser() && getAuthToken())
}
