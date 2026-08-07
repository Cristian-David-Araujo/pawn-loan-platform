<template>
  <div
    v-if="isOpen"
    class="modal-backdrop confirm-backdrop"
    role="alertdialog"
    aria-modal="true"
    :aria-label="t('common.confirmAction', 'Confirm Action')"
    @click.self="cancel"
  >
    <div class="modal-panel card modal-panel-sm">
      <div class="modal-header">
        <h3>{{ t('common.confirmAction', 'Confirm Action') }}</h3>
        <button
          class="btn btn-secondary btn-icon"
          type="button"
          :aria-label="t('common.cancel')"
          @click="cancel"
        >
          <X :size="16" aria-hidden="true" />
        </button>
      </div>

      <div class="modal-body">
        <!-- pre-line so a message can itemise what it is about to act on. -->
        <p class="confirm-message">{{ message }}</p>
      </div>

      <div class="modal-actions form-actions">
        <button class="btn btn-secondary" type="button" @click="cancel">
          {{ t('common.cancel') }}
        </button>
        <button ref="acceptRef" class="btn btn-danger" type="button" @click="accept">
          <Check :size="16" aria-hidden="true" />
          {{ t('common.accept', 'Accept') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { X, Check } from 'lucide-vue-next'
import { useConfirmDialog } from '../composables/useConfirmDialog'

const { t } = useI18n()
const { isOpen, message, accept, cancel } = useConfirmDialog()

const acceptRef = ref<HTMLButtonElement | null>(null)

/* Escape answers the dialog "no". A confirmation the keyboard cannot dismiss is a trap, and
   this one is mounted once in App.vue so it sits over whatever opened it. */
const onKeydown = (event: KeyboardEvent) => {
  if (isOpen.value && event.key === 'Escape') {
    event.preventDefault()
    cancel()
  }
}

/* Focus lands on the confirming button so the dialog can be answered without reaching for
   the mouse. It is the destructive one, which is why Escape is wired first. */
watch(isOpen, async (open) => {
  if (!open) return
  await nextTick()
  acceptRef.value?.focus()
})

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
/* Above --z-modal: a confirmation is routinely opened from inside another modal, and
   answering it must not be blocked by the panel that asked. Replaces an inline
   `style="z-index: 9999"`. */
.confirm-backdrop {
  z-index: var(--z-confirm);
}

.confirm-message {
  white-space: pre-line;
  color: var(--text-secondary);
}

.modal-panel-sm {
  max-width: 420px;
  width: 100%;
}

.modal-actions {
  margin-top: 1.25rem;
}
</style>
