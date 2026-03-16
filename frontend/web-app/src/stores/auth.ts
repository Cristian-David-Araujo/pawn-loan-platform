import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/services/api'

interface User {
  id: string
  username: string
  email: string
  full_name?: string
  roles: Array<{ name: string }>
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(username: string, password: string): Promise<void> {
    const data = await authApi.login(username, password)
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    await fetchCurrentUser()
  }

  async function fetchCurrentUser(): Promise<void> {
    try {
      user.value = await authApi.getMe()
    } catch {
      // ignore
    }
  }

  function logout(): void {
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  if (token.value) {
    fetchCurrentUser()
  }

  return { token, refreshToken, user, isAuthenticated, login, logout, fetchCurrentUser }
})
