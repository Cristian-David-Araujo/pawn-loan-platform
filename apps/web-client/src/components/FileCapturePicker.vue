<template>
  <fieldset class="file-capture-picker">
    <legend>{{ label }}</legend>
    <p v-if="hint" class="picker-hint">{{ hint }}</p>

    <div class="capture-actions">
      <input
        ref="cameraInput"
        class="visually-hidden"
        type="file"
        accept="image/*"
        capture="environment"
        @change="addFiles"
      />
      <input
        ref="fileInput"
        class="visually-hidden"
        type="file"
        :accept="accept"
        :multiple="maxFiles > 1"
        @change="addFiles"
      />
      <button class="btn btn-secondary capture-button" type="button" :disabled="isProcessing || isFull" @click="openCamera">
        <Camera :size="16" aria-hidden="true" />
        {{ t('media.takePhoto') }}
      </button>
      <button class="btn btn-secondary capture-button" type="button" :disabled="isProcessing || isFull" @click="openFiles">
        <Upload :size="16" aria-hidden="true" />
        {{ t('media.chooseFile') }}
      </button>
    </div>

    <p v-if="isProcessing" class="picker-status" role="status">
      <LoaderCircle :size="15" class="spin" aria-hidden="true" />
      {{ t('media.preparingFile') }}
    </p>
    <p v-if="error" class="picker-error" role="alert">{{ error }}</p>
    <p v-else-if="compressedCount" class="picker-status">
      {{ t('media.filesCompressed', { count: compressedCount }) }}
    </p>

    <ul v-if="modelValue.length" class="selected-files" :aria-label="t('media.selectedFiles')">
      <li v-for="file in modelValue" :key="fileKey(file)" class="selected-file">
        <img v-if="isImage(file)" :src="previewFor(file)" :alt="t('media.previewAlt', { name: file.name })" />
        <FileText v-else :size="22" aria-hidden="true" />
        <span class="selected-file-copy">
          <strong>{{ file.name }}</strong>
          <small>{{ formatFileSize(file.size) }}</small>
        </span>
        <button
          class="btn btn-ghost btn-icon remove-file"
          type="button"
          :aria-label="t('media.removeFile', { name: file.name })"
          @click="removeFile(file)"
        >
          <X :size="16" aria-hidden="true" />
        </button>
      </li>
    </ul>
  </fieldset>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Camera, FileText, LoaderCircle, Upload, X } from 'lucide-vue-next'

import { compressImageFile, formatFileSize } from '../utils/media'

const props = withDefaults(
  defineProps<{
    modelValue: File[]
    label: string
    hint?: string
    accept?: string
    maxFiles?: number
    maxBytes?: number
    maxDimension?: number
    targetBytes?: number
  }>(),
  {
    hint: '',
    accept: 'image/jpeg,image/png,image/webp',
    maxFiles: 12,
    maxBytes: 5 * 1024 * 1024,
    maxDimension: 1920,
    targetBytes: 1_500_000
  }
)

const emit = defineEmits<{ 'update:modelValue': [files: File[]] }>()
const { t } = useI18n()
const cameraInput = ref<HTMLInputElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const isProcessing = ref(false)
const error = ref('')
const compressedCount = ref(0)
const previewUrls = new Map<File, string>()

const isFull = computed(() => props.modelValue.length >= props.maxFiles)
const isImage = (file: File) => file.type.startsWith('image/')
const fileKey = (file: File) => `${file.name}-${file.size}-${file.lastModified}`

const releaseRemovedPreviews = (files: File[]) => {
  for (const [file, url] of previewUrls) {
    if (!files.includes(file)) {
      URL.revokeObjectURL(url)
      previewUrls.delete(file)
    }
  }
}

watch(
  () => props.modelValue,
  (files) => releaseRemovedPreviews(files),
  { deep: false }
)

onBeforeUnmount(() => {
  for (const url of previewUrls.values()) URL.revokeObjectURL(url)
})

const previewFor = (file: File) => {
  const existing = previewUrls.get(file)
  if (existing) return existing
  const url = URL.createObjectURL(file)
  previewUrls.set(file, url)
  return url
}

const openCamera = () => cameraInput.value?.click()
const openFiles = () => fileInput.value?.click()

const addFiles = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const sourceFiles = Array.from(input.files ?? [])
  input.value = ''
  if (!sourceFiles.length || isFull.value) return

  error.value = ''
  compressedCount.value = 0
  isProcessing.value = true
  try {
    const availableSlots = props.maxFiles - props.modelValue.length
    const selected = sourceFiles.slice(0, availableSlots)
    const prepared = await Promise.all(
      selected.map(async (file) => {
        if (!isImage(file) && file.type !== 'application/pdf') {
          throw new Error(t('media.invalidType'))
        }
        const result = isImage(file)
          ? await compressImageFile(file, {
              maxDimension: props.maxDimension,
              targetBytes: props.targetBytes
            })
          : { file, compressed: false }
        if (result.file.size > props.maxBytes) {
          throw new Error(t('media.fileTooLarge', { size: Math.floor(props.maxBytes / (1024 * 1024)) }))
        }
        return result
      })
    )
    compressedCount.value = prepared.filter((item) => item.compressed).length
    emit('update:modelValue', [...props.modelValue, ...prepared.map((item) => item.file)])
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : t('media.prepareFailed')
  } finally {
    isProcessing.value = false
  }
}

const removeFile = (file: File) => emit('update:modelValue', props.modelValue.filter((item) => item !== file))
</script>

<style scoped>
.file-capture-picker {
  min-width: 0;
  margin: 0;
  padding: 0.85rem;
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius);
  background: var(--surface-soft);
}

.file-capture-picker legend {
  padding: 0 0.25rem;
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 650;
}

.picker-hint,
.picker-status,
.picker-error {
  margin: 0.2rem 0 0.75rem;
  font-size: var(--fs-sm);
  line-height: 1.45;
}

.picker-hint,
.picker-status {
  color: var(--muted);
}

.picker-error {
  color: var(--danger-text);
}

.capture-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.capture-button {
  min-height: 44px;
}

.picker-status {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.selected-files {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 0.5rem;
  padding: 0;
  margin: 0.75rem 0 0;
  list-style: none;
}

.selected-file {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.55rem;
  padding: 0.45rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
}

.selected-file img {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: var(--radius-xs);
  object-fit: cover;
  background: var(--surface-hover);
}

.selected-file-copy {
  display: grid;
  min-width: 0;
  flex: 1;
}

.selected-file-copy strong {
  overflow: hidden;
  font-size: var(--fs-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-file-copy small {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
}

.remove-file {
  flex: 0 0 auto;
  min-height: 2.75rem;
  min-width: 2.75rem;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .spin { animation: none; }
}
</style>
