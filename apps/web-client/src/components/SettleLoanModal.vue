<template>
  <div v-if="loan" class="modal-backdrop" @click.self="close">
    <div class="modal-panel card">
      <div class="modal-header">
        <h3>{{ t('loans.settleLoan') }}</h3>
        <button class="btn btn-secondary btn-icon" type="button" :aria-label="t('common.close')" @click="close">
          <X :size="16" />
        </button>
      </div>

      <div class="mt-16">
        <p>{{ t('loans.settleExplain', { id: loan.id, total: formatCurrency(totalOwed) }) }}</p>
        <p class="pill pill-warning mt-8">{{ t('loans.settleWritesOff') }}</p>

        <div class="form-section mt-16">
          <div class="grid grid-2">
            <label>
              {{ t('loans.settleAmount') }}
              <CurrencyInput v-model="amount" />
            </label>
            <label>
              {{ t('common.method') }}
              <CustomSelect v-model="method" :options="methodOptions" />
            </label>
          </div>

          <!-- Deliberately no preselected option. Handing the pledge back and keeping it for
               sale are opposite decisions, and neither should happen because a radio came
               pre-ticked. The API refuses the request without it for the same reason. -->
          <fieldset class="mt-16">
            <legend class="form-section-title">{{ t('loans.settleCollateralQuestion') }}</legend>
            <label class="checkbox-row">
              <input v-model="collateralAction" type="radio" value="release" />
              {{ t('loans.settleReleaseCollateral') }}
            </label>
            <label class="checkbox-row">
              <input v-model="collateralAction" type="radio" value="for_sale" />
              {{ t('loans.settleKeepForSale') }}
            </label>
          </fieldset>

          <label class="mt-16">
            {{ t('loans.settleReason') }}
            <textarea v-model="reason" rows="3" :placeholder="t('loans.settleReasonPlaceholder')"></textarea>
          </label>
        </div>

        <p class="mt-8">{{ t('loans.settleWillWriteOff', { amount: formatCurrency(writeOff) }) }}</p>
        <p v-if="error" class="pill pill-overdue mt-8">{{ error }}</p>
      </div>

      <div class="modal-actions form-actions mt-24">
        <button class="btn btn-secondary" type="button" @click="close">{{ t('common.cancel') }}</button>
        <button class="btn btn-danger" type="button" :disabled="!canSubmit" @click="submit">
          <HandCoins :size="16" />
          {{ t('loans.confirmSettle') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { HandCoins, X } from 'lucide-vue-next'

import { apiClient, apiErrorMessage } from '../services/api'
import type { Loan } from '../types/domain'
import { formatCurrency } from '../utils/currency'
import CurrencyInput from './CurrencyInput.vue'
import CustomSelect from './CustomSelect.vue'

/**
 * A negotiated settlement: take what can be collected and write off the rest.
 *
 * The last resort, so it is the loudest confirmation in the product — it names the total
 * owed, and it keeps a running figure of what will be forgiven as the operator types. That
 * number is the point of the screen: the amount collected is the easy half of the decision.
 */
const props = defineProps<{
  loan: Loan | null
  pendingInterest: number
}>()

const emit = defineEmits<{
  close: []
  settled: [loanId: number]
}>()

const { t } = useI18n()

const amount = ref(0)
const reason = ref('')
const method = ref('cash')
const collateralAction = ref('')
const error = ref('')
const submitting = ref(false)

// The same three the collection form offers. A settlement is still money over the counter,
// and a fourth vocabulary for how it arrived would show up in the payment history as a
// method no other screen knows.
const methodOptions = [
  { value: 'cash', label: t('common.cash') },
  { value: 'bank-transfer', label: t('common.bankTransfer') },
  { value: 'other', label: t('common.other') }
]

const totalOwed = computed(() =>
  Math.round(((props.loan?.outstandingPrincipal ?? 0) + props.pendingInterest) * 100) / 100
)

const writeOff = computed(() => Math.max(0, Math.round((totalOwed.value - amount.value) * 100) / 100))

watch(
  () => props.loan?.id,
  () => {
    amount.value = 0
    reason.value = ''
    method.value = 'cash'
    collateralAction.value = ''
    error.value = ''
  }
)

const canSubmit = computed(
  () =>
    reason.value.trim().length >= 3 &&
    collateralAction.value !== '' &&
    amount.value >= 0 &&
    amount.value <= totalOwed.value &&
    !submitting.value
)

const close = () => emit('close')

const submit = async () => {
  const target = props.loan
  if (!target || !canSubmit.value) return

  submitting.value = true
  error.value = ''
  try {
    await apiClient.request(`/loans/${target.id}/settle`, {
      method: 'POST',
      body: JSON.stringify({
        amount: amount.value,
        reason: reason.value.trim(),
        payment_method: method.value,
        collateral_action: collateralAction.value
      })
    })
    emit('settled', target.id)
    emit('close')
  } catch (caught) {
    error.value = apiErrorMessage(caught) || t('messages.operationFailed')
  } finally {
    submitting.value = false
  }
}
</script>
