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

const state = reactive({
  accessToken: getStoredAccessToken(),
  username: getStoredUsername()
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
}

const logout = () => {
  state.accessToken = ''
  state.username = ''
  clearAuthSession()
}

export const useAuthState = () => ({
  state,
  isAuthenticated: computed(() => Boolean(state.accessToken)),
  login,
  logout
})
