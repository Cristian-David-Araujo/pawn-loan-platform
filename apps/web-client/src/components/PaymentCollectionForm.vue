<template>
  <div class="card mt-16">
    <!-- Tab-specific summary lines and warnings. -->
    <slot />

    <label class="mt-16">
      {{ t('payments.notes') }}
      <input v-model="notes" :placeholder="t('payments.notesPlaceholder')" />
    </label>

    <div class="collection-actions form-inline mt-16">
      <label>
        {{ t('payments.paymentMethod') }}
        <CustomSelect v-model="method" :options="paymentMethodOptions" />
      </label>
      <label>
        {{ t('payments.totalAmount') }}
        <CurrencyInput v-model="amount" @input="emit('amountEdited')" />
      </label>
      <button class="btn btn-secondary" type="button" @click="emit('useSuggested')">
        <Sparkles :size="16" />
        {{ t('payments.useSuggested') }}
      </button>

      <div class="collection-spacer"></div>

      <label class="checkbox-row collection-print">
        <input v-model="printReceipt" type="checkbox" />
        {{ t('common.printReceiptOnSave') }}
      </label>
      <button class="btn" type="button" :disabled="submitDisabled" @click="emit('submit')">
        <slot name="icon" />
        {{ submitLabel }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sparkles } from 'lucide-vue-next'

import CurrencyInput from './CurrencyInput.vue'
import CustomSelect from './CustomSelect.vue'
import type { PaymentMethod } from '../types/domain'

/**
 * The "take the money" footer shared by both payment tabs: amount, method, suggested
 * amount, print toggle and submit. Kept as one component so the two collection flows
 * cannot drift apart in layout or wording — everything above it is tab-specific and
 * arrives through the default slot.
 */
const props = defineProps<{
  submitLabel: string
  submitDisabled?: boolean
}>()

const emit = defineEmits<{
  submit: []
  useSuggested: []
  /** Fired on real keystrokes, so callers can stop auto-syncing the amount to the selection. */
  amountEdited: []
}>()

const amount = defineModel<number>('amount', { required: true })
const method = defineModel<PaymentMethod>('method', { required: true })
const notes = defineModel<string>('notes', { required: true })
const printReceipt = defineModel<boolean>('printReceipt', { required: true })

const { t } = useI18n()

const submitDisabled = computed(() => props.submitDisabled === true)

const paymentMethodOptions = computed(() => [
  { value: 'cash', label: t('common.cash') },
  { value: 'bank-transfer', label: t('common.bankTransfer') },
  { value: 'other', label: t('common.other') }
])
</script>

<style scoped>
.collection-actions {
  align-items: flex-end;
  border-top: 1px solid var(--line);
  padding-top: 1rem;
}

.collection-spacer {
  flex: 1;
}

.collection-print {
  margin-bottom: 0;
}
</style>
