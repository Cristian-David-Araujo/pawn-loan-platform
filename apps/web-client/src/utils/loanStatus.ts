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
 * See docs/status-model.md for what each state means and what moves a loan between them.
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

/* ── Why a loan is closed ────────────────────────────────────────────────────────────────
 *
 * `closed` hides four different endings, and for a report they are not the same event:
 * a customer paid, the loan was renewed into another, an operator wrote the balance off, or
 * it was settled for less than owed. Each already leaves its own mark on the row; what was
 * missing was one place that reads them, so every report worked it out its own way or not at
 * all.
 *
 * Derived, never stored: a fifth `LoanStatus` value would need a migration that alters a
 * native Postgres type and a review of every comparison against the four that exist, to
 * record something the columns already say.
 */
export type LoanClosureReason = 'paid' | 'renewed' | 'settled' | 'written_off'

const CLOSURE_KEYS: Record<LoanClosureReason, string> = {
  paid: 'loanStatus.closurePaid',
  renewed: 'loanStatus.closureRenewed',
  settled: 'loanStatus.closureSettled',
  written_off: 'loanStatus.closureWrittenOff'
}

export interface ClosableLoan {
  status: string
  settledAt?: string | null
  forceClosedAt?: string | null
  /** Set on the loan that *replaced* this one, so the source is identified by being pointed at. */
  renewedIntoId?: number | null
}

/**
 * Why a closed loan is closed, or `null` if it is still open.
 *
 * Order matters. A renewal closes the source *and* zeroes its outstanding, and a settlement
 * closes a loan that may also carry a forced-close stamp from an earlier attempt; the most
 * specific fact wins, and "paid" is only what is left when none of the others applies.
 */
export const loanClosureReason = (loan: ClosableLoan): LoanClosureReason | null => {
  if (loan.status !== 'closed') return null
  if (loan.renewedIntoId) return 'renewed'
  if (loan.settledAt) return 'settled'
  if (loan.forceClosedAt) return 'written_off'
  return 'paid'
}

export const loanClosureReasonKey = (reason: LoanClosureReason): string => CLOSURE_KEYS[reason]
