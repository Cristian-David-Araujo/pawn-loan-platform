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

const parseFilename = (contentDisposition: string | null, fallback: string) => {
  const match = contentDisposition?.match(/filename="?([^"]+)"?/)
  return match?.[1] ?? fallback
}

const requestFile = async (path: string, fallbackFilename: string): Promise<{ blob: Blob; filename: string }> => {
  const { logout } = useAuthState()
  const accessToken = getStoredAccessToken()
  if (!accessToken) {
    logout()
    throw new Error('Not authenticated')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` }
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

  return {
    blob: await response.blob(),
    filename: parseFilename(response.headers.get('content-disposition'), fallbackFilename)
  }
}

const requestUpload = async <T>(path: string, formData: FormData): Promise<T> => {
  const { logout } = useAuthState()
  const accessToken = getStoredAccessToken()
  if (!accessToken) {
    logout()
    throw new Error('Not authenticated')
  }

  // No Content-Type header: the browser sets the multipart boundary.
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData
  })

  if (response.status === 401) {
    logout()
    if (window.location.pathname !== '/login') {
      window.location.assign('/login')
    }
    throw new Error('Session expired')
  }

  if (!response.ok) {
    let detail = ''
    try {
      detail = ((await response.json()) as { detail?: string }).detail ?? ''
    } catch {
      detail = ''
    }
    throw new Error(detail || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

export const apiClient = {
  request,
  requestFile,
  requestUpload
}
