const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
const API_USERNAME = import.meta.env.VITE_API_USERNAME ?? 'admin'
const API_PASSWORD = import.meta.env.VITE_API_PASSWORD ?? 'admin123'

let accessToken = ''

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  if (!accessToken) {
    await login()
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
    await login()
    const retry = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
        ...(init?.headers ?? {})
      }
    })

    if (!retry.ok) {
      throw new Error(await retry.text())
    }

    return retry.json() as Promise<T>
  }

  if (!response.ok) {
    throw new Error(await response.text())
  }

  if (response.status === 204) {
    return {} as T
  }

  return response.json() as Promise<T>
}

const login = async () => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: API_USERNAME, password: API_PASSWORD })
  })

  if (!response.ok) {
    throw new Error('Unable to authenticate against backend. Check VITE_API_USERNAME and VITE_API_PASSWORD.')
  }

  const data = (await response.json()) as { access_token: string }
  accessToken = data.access_token
}

export const apiClient = {
  request,
  login
}
