import { computed, ref } from 'vue'

/**
 * Light / dark, as a per-operator preference rather than portfolio policy.
 *
 * Module-level state, the same singleton shape as the platform store and the confirm dialog:
 * the topbar control and any other reader share one source of truth without a store.
 *
 * Three settings, not two. "System" is the default and is a real state, not a synonym for
 * light: a machine that switches to dark in the evening should take the app with it, and an
 * operator who has explicitly chosen light must keep light when it does. Collapsing the two
 * loses that distinction, which is why the resolved value is written to `data-theme` while
 * the *preference* is what gets stored.
 */
export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'pawn-theme'

const systemQuery = typeof window !== 'undefined' && typeof window.matchMedia === 'function'
  ? window.matchMedia('(prefers-color-scheme: dark)')
  : null

const readStoredPreference = (): ThemePreference => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored
    }
  } catch {
    // Private mode or a blocked storage partition. Falling back to the system
    // preference is strictly better than failing to render.
  }
  return 'system'
}

const preference = ref<ThemePreference>(readStoredPreference())
const systemPrefersDark = ref(systemQuery?.matches ?? false)

export const resolvedTheme = computed<ResolvedTheme>(() =>
  preference.value === 'system' ? (systemPrefersDark.value ? 'dark' : 'light') : preference.value
)

const apply = () => {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', resolvedTheme.value)
}

/* Only meaningful while the preference is 'system'; the listener stays attached either way
   so switching back to 'system' picks up the current setting without a reload. */
systemQuery?.addEventListener('change', (event) => {
  systemPrefersDark.value = event.matches
  apply()
})

const setPreference = (next: ThemePreference) => {
  preference.value = next
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // The theme still applies for this session; it just will not survive a reload.
  }
  apply()
}

/**
 * Cycles system → light → dark → system.
 *
 * A two-state toggle cannot return to "follow the machine" once it has been touched, which
 * strands anyone who taps it to look and then wants the automatic behaviour back.
 */
const cycleTheme = () => {
  setPreference(preference.value === 'system' ? 'light' : preference.value === 'light' ? 'dark' : 'system')
}

export const useTheme = () => ({
  preference,
  resolvedTheme,
  systemPrefersDark,
  setPreference,
  cycleTheme
})

/**
 * Called once from main.ts. The inline script in index.html has already written the
 * attribute to avoid a flash of the wrong theme; this re-applies from the same rules so the
 * two can never disagree, and it is what keeps the inline script a pure optimisation rather
 * than a second source of truth.
 */
export const initTheme = () => {
  apply()
}
