import { useAuthState } from '../modules/authentication/authState'
import { getStoredAccessToken } from '../modules/authentication/session'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const { logout } = useAuthState()
  const accessToken = getStoredAccessToken()
  if (!accessToken) {
    logout()
    throw new Error('Not authenticated')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
      ...(init?.headers ?? {})
    }
  })

  if (response.status === 401) {
    logout()
    if (window.location.pathname !== '/login') {
      window.location.assign('/login')
    }
    throw new Error('Session expired')
  }

  if (!response.ok) {
    throw new Error(await response.text())
  }

  if (response.status === 204) {
    return {} as T
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    return (await response.text()) as T
  }

  return response.json() as Promise<T>
}

export const apiClient = {
  request
}
