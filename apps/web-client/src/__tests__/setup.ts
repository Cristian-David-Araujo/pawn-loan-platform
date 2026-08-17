/**
 * What the test environment has to stand in for.
 *
 * happy-dom is a DOM, not a browser: it has no printer and no network. Both gaps surfaced the
 * moment every view was mounted, and both are worth stubbing rather than working around in
 * the test — a view that prints or fetches on mount is behaving correctly.
 */
import { vi } from 'vitest'

// `InvoicePrintView` calls this ~500ms after mount, which is its whole purpose. happy-dom
// does not define it, so the timer fired after the test had finished and took the run down
// with an unhandled exception.
window.print = vi.fn()

/* `authState.fetchCurrentUser` and the login flow use `fetch` directly rather than the api
   client, so mocking that module does not cover them and they reached for a real
   localhost:8000 — which on a CI runner is a connection refused, and on a developer's machine
   is worse: a test suite quietly talking to a live database. */
vi.stubGlobal(
  'fetch',
  vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
      text: () => Promise.resolve('')
    } as Response)
  )
)

// `crypto.randomUUID` backs the payment idempotency key.
if (!globalThis.crypto?.randomUUID) {
  vi.stubGlobal('crypto', { ...globalThis.crypto, randomUUID: () => 'test-key' })
}
