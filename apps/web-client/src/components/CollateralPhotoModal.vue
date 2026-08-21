<template>
  <div v-if="open" class="modal-backdrop" @click.self="close">
    <section class="modal-panel card photo-modal" role="dialog" aria-modal="true" aria-labelledby="collateral-photo-title">
      <div class="modal-header">
        <div>
          <h3 id="collateral-photo-title">{{ t('media.collateralPhotos') }}</h3>
          <p class="muted">{{ itemDescription }}</p>
        </div>
        <button class="btn btn-secondary btn-icon close-button" type="button" :aria-label="t('common.close')" @click="close">
          <X :size="16" aria-hidden="true" />
        </button>
      </div>

      <FileCapturePicker
        v-if="canEdit"
        v-model="selectedFiles"
        class="mt-16"
        :label="t('media.addCollateralPhotos')"
        :hint="t('media.photoHint')"
      />

      <p v-if="message" :class="['media-message', messageType === 'error' ? 'media-message-error' : 'media-message-success']" role="status">
        {{ message }}
      </p>

      <div v-if="canEdit" class="form-actions mt-16">
        <button class="btn" type="button" :disabled="uploading || !selectedFiles.length" @click="uploadSelected">
          <LoaderCircle v-if="uploading" :size="16" class="spin" aria-hidden="true" />
          <Upload v-else :size="16" aria-hidden="true" />
          {{ uploading ? t('media.uploading') : t('media.savePhotos') }}
        </button>
      </div>

      <div v-if="loading" class="photo-grid photo-grid-loading" role="status" :aria-label="t('common.loading')">
        <span v-for="index in 3" :key="index" class="photo-skeleton" />
      </div>
      <div v-else-if="photos.length" class="photo-grid">
        <article v-for="photo in photos" :key="photo.id" class="photo-card">
          <img
            v-if="photo.previewUrl"
            :src="photo.previewUrl"
            :alt="t('media.collateralPhotoAlt', { name: photo.filename })"
          />
          <div v-else class="photo-placeholder"><ImageOff :size="28" aria-hidden="true" /></div>
          <div class="photo-card-footer">
            <span :title="photo.filename">{{ photo.filename }}</span>
            <span>{{ formatFileSize(photo.size_bytes) }}</span>
          </div>
          <div class="photo-card-actions">
            <button class="btn btn-secondary btn-icon" type="button" :aria-label="t('media.openPhoto', { name: photo.filename })" @click="openPhoto(photo)">
              <ExternalLink :size="16" aria-hidden="true" />
            </button>
            <button v-if="canEdit" class="btn btn-secondary btn-icon" type="button" :aria-label="t('media.deletePhoto', { name: photo.filename })" @click="removePhoto(photo)">
              <Trash2 :size="16" aria-hidden="true" />
            </button>
          </div>
        </article>
      </div>
      <div v-else class="media-empty-state">
        <ImagePlus :size="24" aria-hidden="true" />
        <p>{{ t('media.noCollateralPhotos') }}</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ExternalLink, ImageOff, ImagePlus, LoaderCircle, Trash2, Upload, X } from 'lucide-vue-next'

import { apiClient, apiErrorMessage } from '../services/api'
import { formatFileSize } from '../utils/media'
import FileCapturePicker from './FileCapturePicker.vue'

interface CollateralPhoto {
  id: number
  filename: string
  content_type: string
  size_bytes: number
  previewUrl?: string
}

const props = defineProps<{ open: boolean; itemId: number | null; itemDescription: string; canEdit: boolean }>()
const emit = defineEmits<{ close: []; updated: [] }>()
const { t } = useI18n()
const selectedFiles = ref<File[]>([])
const photos = ref<CollateralPhoto[]>([])
const loading = ref(false)
const uploading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const revokePreviews = () => {
  for (const photo of photos.value) {
    if (photo.previewUrl) URL.revokeObjectURL(photo.previewUrl)
  }
}

onBeforeUnmount(revokePreviews)

const loadPhotos = async () => {
  if (!props.itemId) return
  loading.value = true
  message.value = ''
  revokePreviews()
  try {
    const metadata = await apiClient.request<CollateralPhoto[]>(`/collateral-items/${props.itemId}/photos`)
    const withPreviews = await Promise.all(
      metadata.map(async (photo) => {
        if (!photo.content_type.startsWith('image/')) return photo
        const file = await apiClient.requestFile(
          `/collateral-items/${props.itemId}/photos/${photo.id}/file`,
          photo.filename
        )
        return { ...photo, previewUrl: URL.createObjectURL(file.blob) }
      })
    )
    photos.value = withPreviews
  } catch (cause) {
    messageType.value = 'error'
    message.value = apiErrorMessage(cause)
    photos.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.open, props.itemId] as const,
  ([isOpen, itemId]) => {
    selectedFiles.value = []
    if (isOpen && itemId) void loadPhotos()
  },
  { immediate: true }
)

const close = () => {
  selectedFiles.value = []
  emit('close')
}

const uploadSelected = async () => {
  if (!props.itemId || !selectedFiles.value.length || uploading.value) return
  uploading.value = true
  message.value = ''
  try {
    for (const file of selectedFiles.value) {
      const formData = new FormData()
      formData.append('file', file, file.name)
      await apiClient.requestUpload(`/collateral-items/${props.itemId}/photos`, formData)
    }
    selectedFiles.value = []
    messageType.value = 'success'
    message.value = t('media.photosSaved')
    await loadPhotos()
    emit('updated')
  } catch (cause) {
    messageType.value = 'error'
    message.value = apiErrorMessage(cause)
  } finally {
    uploading.value = false
  }
}

const openPhoto = async (photo: CollateralPhoto) => {
  if (!props.itemId) return
  try {
    const file = await apiClient.requestFile(
      `/collateral-items/${props.itemId}/photos/${photo.id}/file`,
      photo.filename
    )
    const url = URL.createObjectURL(file.blob)
    const link = document.createElement('a')
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

const removePhoto = async (photo: CollateralPhoto) => {
  if (!props.itemId) return
  try {
    await apiClient.request(`/collateral-items/${props.itemId}/photos/${photo.id}`, { method: 'DELETE' })
    messageType.value = 'success'
    message.value = t('media.photoDeleted')
    await loadPhotos()
    emit('updated')
  } catch (cause) {
    messageType.value = 'error'
    message.value = apiErrorMessage(cause)
  }
}
</script>

<style scoped>
.photo-modal { width: min(52rem, calc(100vw - 2rem)); max-height: min(48rem, calc(100dvh - 2rem)); overflow: auto; }
.close-button { min-width: 2.75rem; min-height: 2.75rem; }
.media-message { margin: 0.75rem 0 0; font-size: var(--fs-sm); }
.media-message-success { color: var(--success-text); }
.media-message-error { color: var(--danger-text); }
.photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr)); gap: 0.75rem; margin-top: 1rem; }
.photo-card { overflow: hidden; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface); }
.photo-card img, .photo-placeholder { display: grid; width: 100%; aspect-ratio: 4 / 3; place-items: center; background: var(--surface-soft); object-fit: cover; }
.photo-card-footer { display: grid; gap: 0.1rem; padding: 0.5rem 0.55rem 0; font-size: var(--fs-xs); }
.photo-card-footer span:first-child { overflow: hidden; color: var(--text); font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.photo-card-footer span:last-child { color: var(--muted); font-family: var(--font-mono); }
.photo-card-actions { display: flex; justify-content: flex-end; gap: 0.25rem; padding: 0.35rem; }
.photo-card-actions .btn { min-height: 2.75rem; min-width: 2.75rem; }
.photo-grid-loading { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.photo-skeleton { display: block; min-height: 9rem; border-radius: var(--radius-sm); background: var(--surface-hover); }
.media-empty-state { display: grid; min-height: 11rem; place-items: center; align-content: center; gap: 0.5rem; margin-top: 1rem; border: 1px dashed var(--line-strong); border-radius: var(--radius-sm); color: var(--muted); text-align: center; }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
@media (max-width: 40rem) { .photo-modal { width: calc(100vw - 1rem); max-height: calc(100dvh - 1rem); } .photo-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
