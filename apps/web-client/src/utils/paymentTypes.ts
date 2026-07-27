/**
 * The single source of truth for translating `PaymentEvent.payment_type`.
 *
 * These strings are produced by the API, not chosen here. The current writers are
 * `pay_interest` (`interest_payment`, `partial_interest_payment`,
 * `interest_advance_payment`), `pay_principal` (`partial_principal_payment`,
 * `full_settlement`), the collateral sale (`collateral_sale`) and `mixed_payment`.
 * Adding a type on the server means adding it here too — this map used to be
 * copy-pasted into three views that had each drifted, so raw values like
 * `partial_interest_payment` leaked into the UI untranslated.
 *
 * The trailing entries are legacy values no current endpoint writes; they are kept so
 * rows recorded by older versions still render as words.
 */
const PAYMENT_TYPE_KEYS: Record<string, string> = {
  interest_payment: 'payments.typeInterest',
  partial_interest_payment: 'payments.typePartialInterest',
  interest_advance_payment: 'payments.typeInterestAdvance',
  partial_principal_payment: 'payments.typePartialPrincipal',
  full_settlement: 'payments.typeFullSettlement',
  mixed_payment: 'payments.typeMixed',
  collateral_sale: 'payments.typeCollateralSale',

  interest: 'payments.typeInterest',
  principal: 'payments.typePartialPrincipal',
  penalty_payment: 'payments.typePenalty',
  full_payoff: 'payments.typeFullSettlement',
  advance_payment: 'payments.typeAdvance',
  advance: 'payments.typeAdvance'
}

/**
 * i18n key for a `payment_type`. Unknown values are returned as-is: `t()` echoes a
 * missing key, so an unmapped type shows up verbatim instead of blank — visible enough
 * to get reported, which is how the drift above was found.
 */
export const paymentTypeKey = (paymentType: string): string =>
  PAYMENT_TYPE_KEYS[paymentType] ?? paymentType
