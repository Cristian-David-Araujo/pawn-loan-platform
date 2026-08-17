<template>
  <div class="allocation-detail">
    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="muted">{{ error }}</p>

    <template v-else-if="data">
      <p v-if="!data.allocations.length" class="muted">
        {{ t('payments.allocationUnavailable') }}
      </p>

      <table v-else class="allocation-table">
        <thead>
          <tr>
            <th>{{ t('common.loan') }}</th>
            <th>{{ t('payments.period') }}</th>
            <th>{{ t('common.dueOn') }}</th>
            <th class="text-right">{{ t('common.periodInterest') }}</th>
            <th class="text-right">{{ t('payments.penalty') }}</th>
            <th class="text-right">{{ t('common.interest') }}</th>
            <th class="text-right">{{ t('common.principal') }}</th>
            <th class="text-right">{{ t('common.applied') }}</th>
            <th>{{ t('common.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in data.allocations" :key="row.payment_event_id">
            <td :data-label="t('common.loan')">#{{ row.loan_id }}</td>
            <td :data-label="t('payments.period')">{{ row.billing_period || '—' }}</td>
            <td :data-label="t('common.dueOn')">
              {{ row.charge_due_date ? formatDateDMY(row.charge_due_date) : '—' }}
            </td>
            <td class="text-right" :data-label="t('common.periodInterest')">
              {{ row.charge_amount !== null ? formatCurrency(row.charge_amount) : '—' }}
            </td>
            <td class="text-right" :data-label="t('payments.penalty')">{{ formatCurrency(row.allocated_to_penalty) }}</td>
            <td class="text-right" :data-label="t('common.interest')">{{ formatCurrency(row.allocated_to_interest) }}</td>
            <td class="text-right" :data-label="t('common.principal')">{{ formatCurrency(row.allocated_to_principal) }}</td>
            <td class="text-right num-strong" :data-label="t('common.applied')">
              {{ formatCurrency(row.allocated_total) }}
            </td>
            <td :data-label="t('common.status')">
              <span class="pill" :class="row.interest_charge_id === null ? 'pill-upcoming' : row.fully_covered ? 'pill-current' : 'pill-warning'">
                {{ allocationLabel(row) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Money the periods could not absorb. On an interest payment it became the customer's
           advance; on a foreclosure sale it is the house's. Either way a payment whose parts
           do not add up to its total is the thing this panel exists to make impossible. -->
      <p v-if="data.unallocated_amount > 0" class="muted mt-8">
        {{ t('payments.unallocatedNote', { amount: formatCurrency(data.unallocated_amount) }) }}
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * What one payment was actually applied to.
 *
 * `Payment` alone cannot explain itself: it stores per-bucket totals and its `loan_id` is only
 * the *first* loan touched, while one payment routinely settles several periods across several
 * loans, oldest first. `GET /payments/{id}/allocations` returns the ledger rows in the order the
 * money was applied, and the receipt has used it for a while — the customer detail had two flat
 * tables instead, one per payment and one per ledger row, with nothing linking them, so
 * answering "what did this cover?" meant matching rows by date and amount by eye.
 *
 * Fetched when the row is opened rather than for every payment on the page: a customer with
 * eighty payments would otherwise fire eighty requests to render a table nobody has expanded.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { apiClient, apiErrorMessage } from '../services/api'
import { formatCurrency } from '../utils/currency'
import { formatDateDMY } from '../utils/date'

interface PaymentAllocation {
  payment_event_id: number
  payment_type: string
  loan_id: number
  interest_charge_id: number | null
  billing_period: string
  charge_amount: number | null
  charge_due_date: string | null
  allocated_to_interest: number
  allocated_to_penalty: number
  allocated_to_principal: number
  allocated_total: number
  fully_covered: boolean
  is_reversed: boolean
}

interface PaymentAllocations {
  payment_id: number
  total_amount: number
  total_allocated: number
  unallocated_amount: number
  allocations: PaymentAllocation[]
}

const props = defineProps<{ paymentId: number | null }>()

const { t } = useI18n()

const data = ref<PaymentAllocations | null>(null)
const loading = ref(false)
const error = ref('')

const allocationLabel = (row: PaymentAllocation) => {
  // A row with no charge is principal or an advance — "fully covered" means nothing there.
  if (row.interest_charge_id === null) return t('payments.appliedToPrincipal')
  return row.fully_covered ? t('payments.periodSettled') : t('payments.partial')
}

watch(
  () => props.paymentId,
  async (id) => {
    if (id === null) return
    loading.value = true
    error.value = ''
    data.value = null
    try {
      data.value = await apiClient.request<PaymentAllocations>(`/payments/${id}/allocations`)
    } catch (caught) {
      error.value = apiErrorMessage(caught) || t('messages.operationFailed')
    } finally {
      loading.value = false
    }
  },
  { immediate: true }
)
</script>
