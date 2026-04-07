const ACCESS_TOKEN_KEY = 'pawn-platform-access-token'
const USERNAME_KEY = 'pawn-platform-username'

export const getStoredAccessToken = () => localStorage.getItem(ACCESS_TOKEN_KEY) ?? ''

export const getStoredUsername = () => localStorage.getItem(USERNAME_KEY) ?? ''

export const setAuthSession = (accessToken: string, username: string) => {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(USERNAME_KEY, username)
}

export const clearAuthSession = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(USERNAME_KEY)
}
