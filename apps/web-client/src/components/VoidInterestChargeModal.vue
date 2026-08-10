<template>
  <div v-if="charge" class="modal-backdrop" @click.self="close">
    <div class="modal-panel card">
      <div class="modal-header">
        <h3>{{ t('interest.voidCharge') }}</h3>
        <button class="btn btn-secondary btn-icon" type="button" :aria-label="t('common.close')" @click="close">
          <X :size="16" />
        </button>
      </div>

      <div class="mt-16">
        <p>
          {{ t('interest.voidChargeExplain', {
            period: charge.billing_period,
            loanId: charge.loan_id,
            amount: formatCurrency(charge.current_outstanding_balance)
          }) }}
        </p>
        <p class="pill pill-warning mt-8">{{ t('interest.voidChargeKeepsRecord') }}</p>

        <div class="form-section mt-16">
          <label>
            {{ t('interest.voidReason') }}
            <textarea v-model="reason" rows="3" :placeholder="t('interest.voidReasonPlaceholder')"></textarea>
          </label>
        </div>

        <p v-if="error" class="pill pill-overdue">{{ error }}</p>
      </div>

      <div class="modal-actions form-actions mt-24">
        <button class="btn btn-secondary" type="button" @click="close">
          {{ t('common.cancel') }}
        </button>
        <button class="btn btn-danger" type="button" :disabled="!canSubmit" @click="submit">
          <Ban :size="16" />
          {{ t('interest.confirmVoidCharge') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Ban, X } from 'lucide-vue-next'

import { apiClient, apiErrorMessage } from '../services/api'
import { formatCurrency } from '../utils/currency'

/**
 * Collects the reason and voids a generated interest charge.
 *
 * Deliberately the same shape as `PaymentReversalModal`: a destructive action that forgives
 * money is answerable the same way everywhere, so the wording, the enforced minimum and the
 * error display live in one component rather than being retyped per screen.
 *
 * It is a sibling rather than a reuse of that component because the endpoint, the noun and
 * the confirmation text are different — sharing it would mean a component that branches on
 * which kind of thing it is cancelling.
 *
 * On failure the modal stays open showing the server's own message. That matters more here
 * than for a payment: the API refuses with 409 when money is already allocated to the charge,
 * and that message is the instruction ("reverse them first"), not just an error.
 */
export interface VoidableCharge {
  interest_charge_id: number
  loan_id: number
  billing_period: string
  current_outstanding_balance: number
}

const props = defineProps<{ charge: VoidableCharge | null }>()

const emit = defineEmits<{
  close: []
  voided: [chargeId: number]
}>()

const { t } = useI18n()

const reason = ref('')
const error = ref('')
const submitting = ref(false)

watch(
  () => props.charge?.interest_charge_id,
  () => {
    reason.value = ''
    error.value = ''
  }
)

// Mirrors the API's minimum: an unexplained write-off is not traceable.
const canSubmit = computed(() => reason.value.trim().length >= 3 && !submitting.value)

const close = () => emit('close')

const submit = async () => {
  const target = props.charge
  if (!target || !canSubmit.value) {
    return
  }

  submitting.value = true
  error.value = ''
  try {
    await apiClient.request(`/interest/charges/${target.interest_charge_id}/void`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason.value.trim() })
    })
    emit('voided', target.interest_charge_id)
    emit('close')
  } catch (caught) {
    error.value = apiErrorMessage(caught) || t('messages.operationFailed')
  } finally {
    submitting.value = false
  }
}
</script>
