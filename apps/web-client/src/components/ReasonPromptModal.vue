<template>
  <div v-if="open" class="modal-backdrop" @click.self="close">
    <div class="modal-panel card">
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button class="btn btn-secondary btn-icon" type="button" :aria-label="t('common.close')" @click="close">
          <X :size="16" />
        </button>
      </div>

      <div class="mt-16">
        <p>{{ explanation }}</p>
        <p v-if="warning" class="pill pill-warning mt-8">{{ warning }}</p>

        <div class="form-section mt-16">
          <label>
            {{ label }}
            <textarea ref="fieldRef" v-model="reason" rows="3" :placeholder="placeholder"></textarea>
          </label>
        </div>

        <p v-if="error" class="pill pill-overdue">{{ error }}</p>
      </div>

      <div class="modal-actions form-actions mt-24">
        <button class="btn btn-secondary" type="button" @click="close">
          {{ t('common.cancel') }}
        </button>
        <button class="btn btn-danger" type="button" :disabled="!canSubmit" @click="submit">
          <slot name="icon" />
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Asks for a written reason before an action that forgives money or hides a debt.
 *
 * Presentation only: it collects the text and enforces the minimum, then hands it back. The
 * caller owns the endpoint and every word on screen, because the wording is what makes each
 * of these answerable in its own terms — a reversal, a void and a pause are not the same act
 * and must not be described as if they were.
 *
 * It exists because the third one arrived. `PaymentReversalModal` and
 * `VoidInterestChargeModal` each own their request, which was right at two; pausing a loan
 * used `window.prompt` instead — unstyled, outside the app's modal language, with the
 * three-character floor enforced only by silently discarding shorter answers, so an operator
 * who typed "ok" saw the dialog close and nothing happen. That is the same "three treatments
 * for one act" drift the destructive buttons had.
 */
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { X } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    explanation: string
    label: string
    placeholder: string
    confirmLabel: string
    warning?: string
    error?: string
    /** Mirrors the API's floor. Three characters is not an explanation, but it stops an
     *  empty string standing in for one. */
    minLength?: number
  }>(),
  { warning: '', error: '', minLength: 3 }
)

const emit = defineEmits<{
  close: []
  confirm: [reason: string]
}>()

const { t } = useI18n()

const reason = ref('')
const fieldRef = ref<HTMLTextAreaElement | null>(null)

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return
    reason.value = ''
    // The field is the only thing to do here, so the keyboard starts in it.
    await nextTick()
    fieldRef.value?.focus()
  }
)

const canSubmit = computed(() => reason.value.trim().length >= props.minLength)

const close = () => emit('close')
const submit = () => {
  if (canSubmit.value) emit('confirm', reason.value.trim())
}
</script>
