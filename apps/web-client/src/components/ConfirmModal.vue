<template>
  <div v-if="isOpen" class="modal-backdrop" style="z-index: 9999;" @click.self="cancel">
    <div class="modal-panel card modal-panel-sm">
      <div class="modal-header">
        <h3>{{ t('common.confirmAction', 'Confirm Action') }}</h3>
        <button class="btn btn-secondary btn-icon" type="button" @click="cancel">
          <X :size="16" />
        </button>
      </div>

      <div class="modal-body mt-16">
        <p>{{ message }}</p>
      </div>

      <div class="modal-actions form-actions mt-24" style="display: flex; gap: 1rem; align-items: center; justify-content: flex-end;">
        <button class="btn btn-secondary" type="button" @click="cancel">
          {{ t('common.cancel') }}
        </button>
        <button class="btn btn-danger" type="button" @click="accept">
          <Check :size="16" />
          {{ t('common.accept', 'Accept') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { X, Check } from 'lucide-vue-next'
import { useConfirmDialog } from '../composables/useConfirmDialog'

const { t } = useI18n()
const { isOpen, message, accept, cancel } = useConfirmDialog()
</script>

<style scoped>
.modal-panel-sm {
  max-width: 400px;
  width: 100%;
}
</style>
