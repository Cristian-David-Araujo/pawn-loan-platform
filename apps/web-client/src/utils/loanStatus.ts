/**
 * The single source of truth for naming a loan's status.
 *
 * Three views had grown their own version — `CollateralsView` a class map, `CustomersView` a
 * label function taking a loan *id*, `InvoicePrintView` one taking a loan *object* plus a
 * second class map. Same four states, three implementations, and nothing keeping them in
 * step. That is exactly what `paymentTypeKey()` exists to prevent for payment types.
 *
 * **Two vocabularies, on purpose.**
 *
 * The operator's screens name the *lifecycle*: a loan is `active` in the sense of "open, on
 * the books". That is the right word next to a filter and a portfolio count.
 *
 * A printed document is read by the customer, who is not asking which lifecycle state their
 * loan occupies — they are asking whether they owe anything right now. There, `active` is
 * announced as **"al día"**, because that is what the status actually asserts on the day the
 * document is issued: no billing period is past its due date. Printing "Activo" answered a
 * question nobody had, and left the one they did have unanswered.
 *
 * Both vocabularies describe the same stored value. Neither invents a state.
 *
 * See docs/loan-status-model.md for what each state means and what moves a loan between them.
 */

export type LoanStatus = 'active' | 'overdue' | 'closed' | 'defaulted'

/** What the operator sees: the lifecycle state. */
const SCREEN_KEYS: Record<string, string> = {
  active: 'common.active',
  overdue: 'common.overdue',
  closed: 'common.closed',
  defaulted: 'common.defaulted'
}

/** What the customer reads on a printed document: the answer to "do I owe anything?". */
const DOCUMENT_KEYS: Record<string, string> = {
  active: 'loanStatus.docUpToDate',
  overdue: 'loanStatus.docOverdue',
  closed: 'loanStatus.docSettled',
  defaulted: 'loanStatus.docForeclosed'
}

/** The pill treatment. `defaulted` shares `overdue`'s danger tone: both mean money at risk. */
const STATUS_CLASSES: Record<string, string> = {
  active: 'status-active',
  overdue: 'status-overdue',
  closed: 'status-closed',
  defaulted: 'status-overdue'
}

/**
 * i18n key for a status on screen.
 *
 * An unknown value comes back as-is rather than blank: `t()` echoes a missing key, so a state
 * this map has not caught up with shows up verbatim and gets reported, which is how the drift
 * between the three copies was found in the first place.
 */
export const loanStatusKey = (status: string): string => SCREEN_KEYS[status] ?? status

/** i18n key for a status on a printed, customer-facing document. */
export const loanStatusDocumentKey = (status: string): string => DOCUMENT_KEYS[status] ?? status

export const loanStatusClass = (status: string): string => STATUS_CLASSES[status] ?? 'status-active'
