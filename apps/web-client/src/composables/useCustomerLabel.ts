import { useI18n } from 'vue-i18n'

import { usePlatformStore } from '../stores/platformStore'

/**
 * Resolves a customer id to a display name, falling back to the translated "unknown"
 * string.
 *
 * LoansView and ReportingView each carried an identical copy of this, guarding against a
 * `'__UNKNOWN_CUSTOMER__'` sentinel the store used to return. The store now answers `null`,
 * and this is the one place that decides what an absent customer reads as — so the wording
 * cannot drift between the loans table and the arrears report, which name the same person.
 */
export const useCustomerLabel = () => {
  const { getCustomerName } = usePlatformStore()
  const { t } = useI18n()

  const customerLabel = (customerId: number): string =>
    getCustomerName(customerId) ?? t('messages.unknownCustomer')

  return { customerLabel }
}
