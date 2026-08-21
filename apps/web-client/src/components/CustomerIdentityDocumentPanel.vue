<template>
  <section class="identity-document-panel" :aria-labelledby="headingId">
    <div class="identity-document-head">
      <div>
        <h4 :id="headingId">{{ t('media.identityDocument') }}</h4>
        <p class="muted">
          {{ identityDocuments.length ? t('media.documentSidesAttached', { count: identityDocuments.length }) : t('media.noDocumentAttached') }}
        </p>
      </div>
      <span v-if="identityDocuments.length" class="pill document-count">{{ identityDocuments.length }}</span>
    </div>

    <IdentityDocumentScanner v-if="canEdit" v-model="pendingDocuments" class="mt-8" />

    <p v-if="message" :class="['document-message', messageType === 'error' ? 'document-message-error' : 'document-message-success']" role="status">
      {{ message }}
    </p>

    <div v-if="canEdit && pendingDocuments.length" class="document-actions">
      <button class="btn" type="button" :disabled="uploading" @click="upload">
        <LoaderCircle v-if="uploading" :size="16" class="spin" aria-hidden="true" />
        <Upload v-else :size="16" aria-hidden="true" />
        {{ uploading ? t('media.uploading') : t('media.saveDocumentSides') }}
      </button>
    </div>

    <div v-if="identityDocuments.length" class="document-sides" :aria-label="t('media.savedDocumentSides')">
      <article v-for="document in orderedDocuments" :key="document.id" class="document-side">
        <div class="document-side-copy">
          <strong>{{ sideLabel(document.side) }}</strong>
          <span :title="document.filename">{{ document.filename }}</span>
          <small>{{ formatFileSize(document.size_bytes) }}</small>
        </div>
        <div class="document-side-actions">
          <button class="btn btn-secondary btn-icon" type="button" :aria-label="t('media.openDocumentSide', { side: sideLabel(document.side) })" @click="openDocument(document)">
            <ExternalLink :size="16" aria-hidden="true" />
          </button>
          <button v-if="canEdit" class="btn btn-secondary btn-icon" type="button" :aria-label="t('media.removeDocumentSide', { side: sideLabel(document.side) })" @click="removeDocument(document)">
            <Trash2 :size="16" aria-hidden="true" />
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ExternalLink, LoaderCircle, Trash2, Upload } from 'lucide-vue-next'

import { apiClient, apiErrorMessage } from '../services/api'
import { type IdentityDocumentSide, type PendingIdentityDocument } from '../utils/identityScanner'
import { formatFileSize } from '../utils/media'
import IdentityDocumentScanner from './IdentityDocumentScanner.vue'

interface IdentityDocument {
  id: number
  side: IdentityDocumentSide
  filename: string
  size_bytes: number
}

const props = defineProps<{ customerId: number; canEdit: boolean }>()
const { t } = useI18n()
const pendingDocuments = ref<PendingIdentityDocument[]>([])
const identityDocuments = ref<IdentityDocument[]>([])
const uploading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const headingId = computed(() => `identity-document-${props.customerId}`)
const orderedDocuments = computed(() => {
  const order: Record<IdentityDocumentSide, number> = { front: 0, back: 1, combined: 2 }
  return [...identityDocuments.value].sort((first, second) => order[first.side] - order[second.side])
})
const sideLabel = (side: IdentityDocumentSide) => t(`media.documentSide.${side}`)

const loadDocuments = async () => {
  try {
    identityDocuments.value = await apiClient.request<IdentityDocument[]>(`/customers/${props.customerId}/identity-document`)
  } catch (cause) {
    identityDocuments.value = []
    messageType.value = 'error'
    message.value = apiErrorMessage(cause)
  }
}

watch(
  () => props.customerId,
  () => {
    pendingDocuments.value = []
    message.value = ''
    void loadDocuments()
  },
  { immediate: true }
)

const upload = async () => {
  if (!pendingDocuments.value.length || uploading.value) return
  uploading.value = true
  message.value = ''
  const queued = [...pendingDocuments.value]
  try {
    for (const document of queued) {
      const formData = new FormData()
      formData.append('file', document.file, document.file.name)
      formData.append('side', document.side)
      const saved = await apiClient.requestUpload<IdentityDocument>(
        `/customers/${props.customerId}/identity-document`,
        formData
      )
      identityDocuments.value = [...identityDocuments.value.filter((item) => item.side !== saved.side), saved]
    }
    pendingDocuments.value = []
    messageType.value = 'success'
    message.value = t('media.documentSidesSaved')
  } catch (cause) {
    messageType.value = 'error'
    message.value = apiErrorMessage(cause)
  } finally {
    uploading.value = false
  }
}

const openDocument = async (document: IdentityDocument) => {
  try {
    const file = await apiClient.requestFile(
      `/customers/${props.customerId}/identity-document/${document.side}/file`,
      document.filename
    )
    const url = URL.createObjectURL(file.blob)
    const link = window.document.createElement('a')
    link.href = url
    link.target = '_blank'
    link.rel = 'noopener'
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (cause) {
    messageType.value = 'error'
    message.value = apiErrorMessage(cause)
  }
}

const removeDocument = async (document: IdentityDocument) => {
  try {
    await apiClient.request(`/customers/${props.customerId}/identity-document/${document.side}`, { method: 'DELETE' })
    identityDocuments.value = identityDocuments.value.filter((item) => item.id !== document.id)
    messageType.value = 'success'
    message.value = t('media.documentRemoved')
  } catch (cause) {
    messageType.value = 'error'
    message.value = apiErrorMessage(cause)
  }
}
</script>

<style scoped>
.identity-document-panel { min-width: 0; padding: 0.85rem; border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); }
.identity-document-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem; }
.identity-document-head h4 { margin: 0; }
.document-count { min-width: 1.65rem; text-align: center; font-family: var(--font-mono); }
.document-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem; }
.document-actions .btn, .document-side-actions .btn { min-width: 2.75rem; min-height: 2.75rem; }
.document-message { margin: 0.75rem 0 0; font-size: var(--fs-sm); }
.document-message-success { color: var(--success-text); }
.document-message-error { color: var(--danger-text); }
.document-sides { display: grid; gap: 0.5rem; margin-top: 0.85rem; }
.document-side { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: 0.75rem; padding: 0.65rem; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface-soft); }
.document-side-copy { display: grid; min-width: 0; gap: 0.1rem; }
.document-side-copy strong { font-size: var(--fs-sm); }
.document-side-copy span { overflow: hidden; color: var(--muted); font-size: var(--fs-sm); text-overflow: ellipsis; white-space: nowrap; }
.document-side-copy small { color: var(--muted); font-family: var(--font-mono); font-size: var(--fs-xs); }
.document-side-actions { display: flex; flex: 0 0 auto; gap: 0.35rem; }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
@media (max-width: 40rem) { .identity-document-head { display: grid; } .document-count { justify-self: start; } }
</style>
