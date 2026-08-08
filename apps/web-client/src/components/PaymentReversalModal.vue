<template>
  <div v-if="payment" class="modal-backdrop" @click.self="close">
    <div class="modal-panel card">
      <div class="modal-header">
        <h3>{{ t('payments.deletePayment') }}</h3>
        <button class="btn btn-secondary btn-icon" type="button" :aria-label="t('common.close')" @click="close">
          <X :size="16" />
        </button>
      </div>

      <div class="mt-16">
        <p>
          {{ t('payments.deletePaymentExplain', {
            id: payment.id,
            amount: formatCurrency(payment.totalAmount)
          }) }}
        </p>
        <p class="pill pill-warning mt-8">{{ t('payments.deletePaymentKeepsRecord') }}</p>

        <div class="form-section mt-16">
          <label>
            {{ t('payments.reversalReason') }}
            <textarea v-model="reason" rows="3" :placeholder="t('payments.reversalReasonPlaceholder')"></textarea>
          </label>
        </div>

        <p v-if="error" class="pill pill-overdue">{{ error }}</p>
      </div>

      <div class="modal-actions form-actions mt-24">
        <button class="btn btn-secondary" type="button" @click="close">
          {{ t('common.cancel') }}
        </button>
        <button class="btn btn-danger" type="button" :disabled="!canSubmit" @click="submit">
          <Trash2 :size="16" />
          {{ t('payments.confirmDeletePayment') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Trash2, X } from 'lucide-vue-next'

import { apiClient, apiErrorMessage } from '../services/api'
import type { Payment } from '../types/domain'
import { formatCurrency } from '../utils/currency'

/**
 * Collects the reason and performs the reversal that "deletes" a payment.
 *
 * Shared by every screen that lists payments (the payments history, the customer detail and
 * the loan detail) so the wording, the minimum reason and the error handling cannot drift
 * between them — the whole point is that a removal is answerable the same way everywhere.
 *
 * On failure the modal stays open with the server's reason, so the operator can read it and
 * retry instead of hunting for a notice on the page behind.
 */
const props = defineProps<{ payment: Payment | null }>()

const emit = defineEmits<{
  close: []
  deleted: [paymentId: number]
}>()

const { t } = useI18n()

const reason = ref('')
const error = ref('')
const submitting = ref(false)

watch(
  () => props.payment?.id,
  () => {
    reason.value = ''
    error.value = ''
  }
)

// Mirrors the API's minimum: an unexplained deletion is not traceable.
const canSubmit = computed(() => reason.value.trim().length >= 3 && !submitting.value)

const close = () => emit('close')

const submit = async () => {
  const target = props.payment
  if (!target || !canSubmit.value) {
    return
  }

  submitting.value = true
  error.value = ''
  try {
    await apiClient.request(`/payments/${target.id}/reverse`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason.value.trim() })
    })
    emit('deleted', target.id)
    emit('close')
  } catch (caught) {
    error.value = apiErrorMessage(caught) || t('messages.operationFailed')
  } finally {
    submitting.value = false
  }
}
</script>
