import { createI18n } from 'vue-i18n'
import { messages, type AppLocale } from './messages'

export type { AppLocale } from './messages'

const STORAGE_KEY = 'pawn-platform-locale'

const isSupported = (value: string | null | undefined): value is AppLocale =>
  value === 'en' || value === 'es'

/**
 * What language to open in: the operator's stored choice, else what the browser asks for,
 * else Spanish.
 *
 * The browser is read from `navigator.languages` — the full ordered list — and matched on each
 * tag's **primary subtag**, not by searching the string. `'en'` appears inside `fr-ES` and
 * `'es'` inside `en-ES`, so a substring test picks a language from a region.
 *
 * A browser asking for neither gets **Spanish**, which is what the staff work in and what the
 * API falls back to for the same decision. It used to be English here and Spanish there, so a
 * Portuguese-speaking machine read the app in English and got its recovery email in Spanish.
 */
const detectLocale = (): AppLocale => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (isSupported(saved)) {
    return saved
  }

  const requested = navigator.languages?.length ? navigator.languages : [navigator.language]
  for (const tag of requested) {
    const primary = tag?.toLowerCase().split('-')[0]
    if (isSupported(primary)) {
      return primary
    }
  }

  return 'es'
}

export const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages
})

/**
 * Tells the *document* what language it is in.
 *
 * `<html lang>` is not decoration: it is what a screen reader picks a voice and pronunciation
 * from, what the browser's "translate this page?" offer is based on, and what CSS hyphenation
 * keys off. It was hardcoded `en` in index.html, so the whole Spanish interface was announced
 * with an English voice — and the browser kept offering to translate a page already in the
 * reader's language.
 */
const applyDocumentLanguage = (locale: AppLocale) => {
  document.documentElement.setAttribute('lang', locale)
}

/**
 * The one way the interface language changes.
 *
 * Applies it, remembers it, and tells the document — three things that have to happen together.
 * Callers used to do the first two by hand at the single call site that existed; a second
 * switcher (the sign-in screen needs one, see below) would have been a second chance to forget
 * one of them.
 */
export const setLocale = (locale: AppLocale) => {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  applyDocumentLanguage(locale)
}

/**
 * The locale to tell the API about, readable without a component instance.
 *
 * The forgot-password call happens on a screen with no session, and the recovery email has to
 * arrive in the language the operator is reading the app in — which is this, not
 * `navigator.language`.
 */
export const getStoredLocale = (): AppLocale => i18n.global.locale.value as AppLocale

// The initial value came from `detectLocale()` above; the document still says whatever
// index.html hardcoded until this runs.
applyDocumentLanguage(i18n.global.locale.value as AppLocale)
