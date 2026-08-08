/**
 * The single money formatter.
 *
 * `formatCurrency` used to be written out in each of the nine places that shows an amount —
 * seven views, `LoanDetailModal`, `PaymentReversalModal` — and the copies had drifted. Eight
 * of them formatted with `es-MX`, which groups Colombian pesos as `COP 1,250,000.00`, while
 * the receipt in `InvoicePrintView` used `es-CO` and produced `$ 1.250.000`. The same debt
 * therefore read one way on the collection screen and another on the document handed to the
 * customer, and `CurrencyInput` — the field the amount is *typed* into — grouped with
 * `en-US` regardless of either.
 *
 * The currency code is portfolio policy (`GlobalSettings.currencyCode`), so like the date
 * format it lives at module level and is set once from the store rather than read from a
 * component. Locale follows the currency's own country: an amount in pesos is grouped the
 * way pesos are grouped, whichever language the interface is in. Changing the interface to
 * English must not change what a figure means.
 */

type CurrencyCode = string

let currencyCode: CurrencyCode = 'COP'

/**
 * Grouping belongs to the money, not to the reader. `es-CO` for pesos, `en-US` for dollars:
 * a figure must not change shape because someone switched the UI to English mid-shift.
 */
const LOCALE_BY_CURRENCY: Record<string, string> = {
  COP: 'es-CO',
  MXN: 'es-MX',
  ARS: 'es-AR',
  CLP: 'es-CL',
  PEN: 'es-PE',
  EUR: 'es-ES',
  USD: 'en-US'
}

const localeFor = (code: CurrencyCode) => LOCALE_BY_CURRENCY[code] ?? 'es-CO'

export const setGlobalCurrency = (code: string | null | undefined) => {
  currencyCode = typeof code === 'string' && code.trim().length === 3 ? code.trim().toUpperCase() : 'COP'
}

export const getGlobalCurrency = (): CurrencyCode => currencyCode

/**
 * Pesos have no cents in practice, so a trailing `,00` on every figure in a dense table is
 * noise the reader has to look past. Currencies that do use minor units keep them.
 */
const fractionDigitsFor = (code: CurrencyCode) => (code === 'COP' || code === 'CLP' ? 0 : 2)

export const formatCurrency = (amount: number | null | undefined): string => {
  if (amount === null || amount === undefined || Number.isNaN(amount)) {
    return '-'
  }

  const digits = fractionDigitsFor(currencyCode)
  return new Intl.NumberFormat(localeFor(currencyCode), {
    style: 'currency',
    currency: currencyCode,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(amount)
}

/** Counts and quantities: grouped, never a currency symbol. */
export const formatInteger = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '-'
  }

  return new Intl.NumberFormat(localeFor(currencyCode), { maximumFractionDigits: 0 }).format(value)
}

/** Axis labels and other places where the full figure would not fit. */
export const formatCompactNumber = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '-'
  }

  return new Intl.NumberFormat(localeFor(currencyCode), {
    notation: 'compact',
    maximumFractionDigits: 1
  }).format(value)
}

/**
 * What `CurrencyInput` shows while the operator types: grouping only, no symbol and no
 * decimals, because the field emits a plain integer.
 */
export const formatAmountForInput = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return ''
  }

  return new Intl.NumberFormat(localeFor(currencyCode), { maximumFractionDigits: 0 }).format(value)
}

/**
 * Reads back what `formatAmountForInput` wrote. Every non-digit is dropped, so it does not
 * matter whether the separator the locale produced was a dot, a comma or a narrow space.
 */
export const parseAmountFromInput = (raw: string): number => {
  const digits = raw.replace(/\D/g, '')
  if (!digits) {
    return 0
  }

  const parsed = Number.parseInt(digits, 10)
  return Number.isFinite(parsed) ? parsed : 0
}
