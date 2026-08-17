import { useRouter, type RouteLocationRaw } from 'vue-router'

/**
 * A back control that returns where the operator came from.
 *
 * A detail page is reached from more than one place — a loan from the loans list, from a
 * customer's loans tab, or from a pasted link — so a fixed destination is wrong for every
 * entry point but one. The loan page always pushed to `/loans`, which meant opening a loan
 * from inside a customer and pressing back dropped you in the loan list, with the customer
 * you were working through gone.
 *
 * `history.state.back` is set by Vue Router whenever the previous entry belongs to this app,
 * so it distinguishes "there is somewhere of ours to go back to" from a link opened in a
 * fresh tab — where `router.back()` would leave the application entirely.
 */
export const useBackNavigation = (fallback: RouteLocationRaw) => {
  const router = useRouter()

  return () => {
    if (window.history.state?.back) {
      router.back()
      return
    }
    void router.push(fallback)
  }
}
