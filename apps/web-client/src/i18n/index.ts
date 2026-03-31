import { createI18n } from 'vue-i18n'
import { messages, type AppLocale } from './messages'

export type { AppLocale } from './messages'

const STORAGE_KEY = 'pawn-platform-locale'

const detectLocale = (): AppLocale => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'en' || saved === 'es') {
    return saved
  }

  const fromBrowser = navigator.language.toLowerCase().startsWith('es') ? 'es' : 'en'
  return fromBrowser
}

export const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages
})

export const persistLocale = (locale: AppLocale) => {
  localStorage.setItem(STORAGE_KEY, locale)
}
