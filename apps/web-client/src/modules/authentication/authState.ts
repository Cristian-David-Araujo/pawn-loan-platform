import { computed, reactive } from 'vue'
import { clearAuthSession, getStoredAccessToken, getStoredUsername, setAuthSession } from './session'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

interface LoginPayload {
  username: string
  password: string
}

interface LoginResponse {
  access_token: string
  token_type: string
}

export enum UserRole {
  Administrator = 'administrator',
  LoanOfficer = 'loan_officer',
  Collector = 'collector'
}

export interface UserProfile {
  id: number
  username: string
  full_name: string
  email: string
  phone: string
  document_number: string
  address: string
  role: UserRole
  is_active: boolean
}

const state = reactive({
  accessToken: getStoredAccessToken(),
  username: getStoredUsername(),
  currentUser: null as UserProfile | null
})

const extractErrorMessage = async (response: Response) => {
  try {
    const data = (await response.json()) as { detail?: string }
    return data.detail ?? 'Authentication failed'
  } catch {
    return 'Authentication failed'
  }
}

const login = async (payload: LoginPayload) => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  if (!response.ok) {
    throw new Error(await extractErrorMessage(response))
  }

  const data = (await response.json()) as LoginResponse
  state.accessToken = data.access_token
  state.username = payload.username
  setAuthSession(data.access_token, payload.username)
  await fetchCurrentUser()
}

const fetchCurrentUser = async () => {
  if (!state.accessToken) return
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${state.accessToken}` }
  })
  if (response.ok) {
    state.currentUser = (await response.json()) as UserProfile
  } else {
    logout()
  }
}

const logout = () => {
  state.accessToken = ''
  state.username = ''
  state.currentUser = null
  clearAuthSession()
}

export const hasRole = (roles: UserRole[]) => {
  if (!state.currentUser) return false
  return roles.includes(state.currentUser.role as UserRole)
}

const forgotPassword = async (usernameOrEmail: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username_or_email: usernameOrEmail })
  })

  if (!response.ok) {
    throw new Error(await extractErrorMessage(response))
  }

  return (await response.json()) as { message: string; reset_token: string | null }
}

const resetPassword = async (token: string, newPassword: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password: newPassword })
  })

  if (!response.ok) {
    throw new Error(await extractErrorMessage(response))
  }

  return (await response.json()) as { message: string }
}

export const useAuthState = () => ({
  state,
  isAuthenticated: computed(() => Boolean(state.accessToken)),
  hasRole,
  login,
  logout,
  fetchCurrentUser,
  forgotPassword,
  resetPassword
})
