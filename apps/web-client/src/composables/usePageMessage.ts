import { computed, ref } from 'vue'

/**
 * The one-line result banner a view shows after an action.
 *
 * Five views each held a bare `const message = ref('')` and rendered it in a plain
 * `.notice` — the success tone — for successes *and* for failures alike. So at the counter,
 * with a customer waiting, a rejected payment looked exactly like an accepted one. The
 * classes to tell them apart (`.notice-error`, `.notice-warning`) already existed and were
 * used correctly by `ScheduledBackupCard`; the views simply never reached for them.
 *
 * This is a composable rather than a fifth copy of the same two refs so that the tone
 * cannot be forgotten again: there is no way to set the text without saying what it is.
 *
 * Not a global singleton, unlike the confirm dialog — each view owns its own banner, and
 * two views mounted at once must not overwrite each other's result.
 */
export type MessageTone = 'success' | 'error' | 'warning'

/** What the store's mutations return: `{ ok, messageKey }`. */
interface MutationResult {
  ok: boolean
  messageKey: string
}

export const usePageMessage = () => {
  const message = ref('')
  const tone = ref<MessageTone>('success')

  const messageClass = computed(() => ({
    notice: true,
    'notice-error': tone.value === 'error',
    'notice-warning': tone.value === 'warning'
  }))

  /** An action that did what it said. */
  const notify = (text: string) => {
    message.value = text
    tone.value = 'success'
  }

  /** An action that did not. */
  const fail = (text: string) => {
    message.value = text
    tone.value = 'error'
  }

  /** Something happened, but not cleanly — a partial result the operator should read. */
  const warn = (text: string) => {
    message.value = text
    tone.value = 'warning'
  }

  /**
   * Takes a store mutation's `{ ok, messageKey }` and a translator, and picks the tone from
   * `ok`. The views were already branching on `ok` immediately afterwards; the banner just
   * never listened to it.
   */
  const report = (result: MutationResult, translate: (key: string) => string) => {
    const text = translate(result.messageKey)
    if (result.ok) notify(text)
    else fail(text)
  }

  const clearMessage = () => {
    message.value = ''
    tone.value = 'success'
  }

  return { message, tone, messageClass, notify, fail, warn, report, clearMessage }
}
