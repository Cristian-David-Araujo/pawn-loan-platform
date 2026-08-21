<template>
  <section class="identity-scanner" :aria-labelledby="headingId">
    <div class="scanner-head">
      <div>
        <h4 :id="headingId">{{ t('media.scanOrUploadDocument') }}</h4>
        <p class="muted">{{ t('media.documentScannerHint') }}</p>
      </div>
      <span class="scanner-state" :class="{ 'scanner-state-ready': cameraActive }">{{ scannerState }}</span>
    </div>

    <input ref="fileInput" class="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" @change="selectImage" />

    <div v-if="cameraActive || cameraStarting" class="scanner-video-wrap" data-testid="identity-camera-preview">
      <video ref="video" autoplay muted playsinline :aria-label="t('media.cameraPreview')" />
      <div v-if="cameraStarting" class="camera-loading" role="status">
        <LoaderCircle :size="22" class="spin" aria-hidden="true" />
        {{ t('media.cameraStarting') }}
      </div>
      <div class="card-guide" aria-hidden="true"><span /></div>
      <svg
        v-if="liveDetection"
        class="card-detection"
        :viewBox="detectionViewBox"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <polygon :points="detectionPoints" />
      </svg>
      <span v-if="liveDetection" class="detection-state">{{ t('media.documentLocated', { side: sideLabel(pendingSide) }) }}</span>
      <p class="scanner-video-instruction">{{ t('media.cameraPreview') }} · {{ scannerState }}. {{ liveInstruction }}</p>
    </div>

    <p v-if="message" class="scanner-message" :class="{ 'scanner-message-error': isError }" role="status">{{ message }}</p>

    <div class="scanner-actions">
      <button v-if="!cameraActive && !cameraStarting" class="btn" type="button" :disabled="preparing" @click="startCamera">
        <Camera :size="16" aria-hidden="true" />
        {{ t('media.openCamera') }}
      </button>
      <button v-else class="btn btn-secondary" type="button" :disabled="preparing" @click="captureCurrentSide">
        <ScanLine :size="16" aria-hidden="true" />
        {{ captureLabel }}
      </button>
      <button v-if="cameraActive" class="btn btn-secondary" type="button" @click="stopCamera">
        <VideoOff :size="16" aria-hidden="true" />
        {{ t('media.stopCamera') }}
      </button>
      <button class="btn btn-secondary" type="button" :disabled="preparing || cameraStarting" @click="fileInput?.click()">
        <Upload :size="16" aria-hidden="true" />
        {{ t('media.chooseFile') }}
      </button>
    </div>

    <p v-if="preparing" class="scanner-processing" role="status"><LoaderCircle :size="15" class="spin" aria-hidden="true" /> {{ t('media.segmentingDocument') }}</p>

    <ul v-if="modelValue.length" class="scanned-sides" :aria-label="t('media.scannedSides')">
      <li v-for="item in modelValue" :key="item.side" class="scanned-side">
        <img :src="previewFor(item.file)" :alt="t('media.scannedSideAlt', { side: sideLabel(item.side) })" />
        <div>
          <strong>{{ sideLabel(item.side) }}</strong>
          <small>{{ item.file.name }}</small>
          <small class="scanned-recognition">{{ recognitionLabel(item.recognition) }}</small>
        </div>
        <button class="btn btn-ghost btn-icon" type="button" :aria-label="t('media.removeScannedSide', { side: sideLabel(item.side) })" @click="remove(item.side)"><X :size="16" /></button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Camera, LoaderCircle, ScanLine, Upload, VideoOff, X } from 'lucide-vue-next'

import {
  detectIdentityDocument,
  fingerprintDifference,
  scanCanvasToFile,
  segmentIdentityImage,
  type IdentityDocumentDetection,
  type IdentityDocumentRecognition,
  type IdentityDocumentSide,
  type PendingIdentityDocument
} from '../utils/identityScanner'

const props = defineProps<{ modelValue: PendingIdentityDocument[] }>()
const emit = defineEmits<{ 'update:modelValue': [documents: PendingIdentityDocument[]] }>()
const { t } = useI18n()
const video = ref<HTMLVideoElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const cameraActive = ref(false)
const cameraStarting = ref(false)
const preparing = ref(false)
const detecting = ref(false)
const liveDetection = ref<IdentityDocumentDetection | null>(null)
const message = ref('')
const isError = ref(false)
const headingId = 'identity-scanner-heading'
let stream: MediaStream | null = null
let automaticTimer: number | null = null
let lastFingerprint: number[] = []
let lastCapturedAt = 0
const previewUrls = new Map<File, string>()

const pendingSide = computed<IdentityDocumentSide>(() => {
  if (!props.modelValue.some((item) => item.side === 'front')) return 'front'
  if (!props.modelValue.some((item) => item.side === 'back')) return 'back'
  return 'combined'
})
const scannerState = computed(() => {
  if (cameraStarting.value) return t('media.cameraStarting')
  if (!cameraActive.value) return t('media.cameraInactive')
  return pendingSide.value === 'front' ? t('media.scanningFront') : t('media.scanningBack')
})
const liveInstruction = computed(() =>
  liveDetection.value ? t('media.documentLocated', { side: sideLabel(pendingSide.value) }) : t('media.alignDocument')
)
const detectionViewBox = computed(() => {
  const detection = liveDetection.value
  return detection ? `0 0 ${detection.width} ${detection.height}` : '0 0 1 1'
})
const detectionPoints = computed(() => {
  const corners = liveDetection.value?.corners
  if (!corners) return ''
  return [corners.topLeft, corners.topRight, corners.bottomRight, corners.bottomLeft]
    .map((corner) => `${corner.x},${corner.y}`)
    .join(' ')
})
const captureLabel = computed(() =>
  pendingSide.value === 'front' ? t('media.captureFront') : t('media.captureBack')
)
const sideLabel = (side: IdentityDocumentSide) => t(`media.documentSide.${side}`)
const recognitionLabel = (recognition: IdentityDocumentRecognition) =>
  t(`media.documentRecognition.${recognition}`)

const previewFor = (file: File) => {
  const current = previewUrls.get(file)
  if (current) return current
  const url = URL.createObjectURL(file)
  previewUrls.set(file, url)
  return url
}
const releaseRemovedPreviews = (documents: PendingIdentityDocument[]) => {
  for (const [file, url] of previewUrls) {
    if (!documents.some((item) => item.file === file)) {
      URL.revokeObjectURL(url)
      previewUrls.delete(file)
    }
  }
}
watch(() => props.modelValue, releaseRemovedPreviews, { deep: false })

const setDocuments = (documents: PendingIdentityDocument[]) => emit('update:modelValue', documents)
const queue = (document: PendingIdentityDocument) => {
  setDocuments([...props.modelValue.filter((item) => item.side !== document.side), document])
}
const remove = (side: IdentityDocumentSide) => setDocuments(props.modelValue.filter((item) => item.side !== side))

const videoCanvas = () => {
  if (!video.value?.videoWidth || !video.value?.videoHeight) return null
  const canvas = window.document.createElement('canvas')
  canvas.width = video.value.videoWidth
  canvas.height = video.value.videoHeight
  canvas.getContext('2d')?.drawImage(video.value, 0, 0)
  return canvas
}

const capture = async (side: IdentityDocumentSide, automatic = false) => {
  const canvas = videoCanvas()
  if (!canvas || preparing.value || (side !== 'front' && side !== 'back')) return false
  preparing.value = true
  try {
    const scan = await scanCanvasToFile(canvas, side)
    if (automatic && scan.confidence < 0.42) return false
    if (scan.identification?.side && scan.identification.side !== side) {
      if (!automatic) {
        message.value = t('media.documentSideMismatch', {
          detected: sideLabel(scan.identification.side),
          expected: sideLabel(side)
        })
        isError.value = true
      }
      return false
    }
    if (automatic && side === 'back' && fingerprintDifference(lastFingerprint, scan.fingerprint) < 0.12) return false
    queue({ side, file: scan.file, recognition: scan.identification?.recognition ?? 'layout' })
    lastFingerprint = scan.fingerprint
    lastCapturedAt = Date.now()
    message.value = side === 'front' ? t('media.frontCapturedTurnOver') : t('media.backCaptured')
    isError.value = false
    if (side === 'back') stopCamera()
    return true
  } catch (cause) {
    if (!automatic) {
      message.value = cause instanceof Error ? cause.message : t('media.scanFailed')
      isError.value = true
    }
    return false
  } finally {
    preparing.value = false
  }
}

const captureCurrentSide = () => void capture(pendingSide.value)

const refreshLiveDetection = async () => {
  const canvas = videoCanvas()
  if (!canvas || detecting.value) return null
  detecting.value = true
  try {
    liveDetection.value = await detectIdentityDocument(canvas)
    return liveDetection.value
  } finally {
    detecting.value = false
  }
}

const automaticCapture = () => {
  if (!cameraActive.value || preparing.value || detecting.value || Date.now() - lastCapturedAt < 1400) return
  if (pendingSide.value !== 'front' && pendingSide.value !== 'back') return
  void refreshLiveDetection().then((detection) => {
    if (detection && detection.confidence >= 0.42) void capture(pendingSide.value, true)
  })
}

const startCamera = async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    message.value = t('media.cameraUnavailable')
    isError.value = true
    return
  }
  cameraStarting.value = true
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }
    })
    await nextTick()
    if (!video.value) {
      stream.getTracks().forEach((track) => track.stop())
      stream = null
      return
    }
    video.value.srcObject = stream
    await video.value.play()
    cameraActive.value = true
    message.value = t('media.autoScanReady')
    isError.value = false
    automaticTimer = window.setInterval(automaticCapture, 900)
  } catch {
    stopCamera()
    message.value = t('media.cameraPermissionDenied')
    isError.value = true
  } finally {
    cameraStarting.value = false
  }
}

const stopCamera = () => {
  if (automaticTimer !== null) window.clearInterval(automaticTimer)
  automaticTimer = null
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
  if (video.value) video.value.srcObject = null
  cameraActive.value = false
  cameraStarting.value = false
  liveDetection.value = null
}

const selectImage = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  preparing.value = true
  message.value = ''
  try {
    if (file.type === 'application/pdf') {
      queue({ side: 'combined', file, recognition: 'layout' })
    } else {
      const sides = await segmentIdentityImage(file)
      // A v-model update reaches the parent on the next render. Build the full replacement
      // locally so a two-sided image cannot lose its front scan while its back scan is queued.
      const next = [...props.modelValue]
      for (const side of sides) {
        const existingIndex = next.findIndex((item) => item.side === side.side)
        if (existingIndex >= 0) next.splice(existingIndex, 1)
        next.push(side)
      }
      setDocuments(next)
    }
    isError.value = false
    message.value = t('media.documentSegmented')
  } catch (cause) {
    message.value = cause instanceof Error ? cause.message : t('media.scanFailed')
    isError.value = true
  } finally {
    preparing.value = false
  }
}

onBeforeUnmount(() => {
  stopCamera()
  for (const url of previewUrls.values()) URL.revokeObjectURL(url)
})
</script>

<style scoped>
.identity-scanner { padding: 0.85rem; border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface-soft); }
.scanner-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem; }
.scanner-head h4 { margin: 0; }
.scanner-state { flex: 0 0 auto; padding: 0.2rem 0.4rem; border: 1px solid var(--line); border-radius: var(--radius-xs); color: var(--muted); font-size: var(--fs-xs); font-weight: 650; }
.scanner-state-ready { border-color: var(--accent-border); color: var(--accent); }
.scanner-video-wrap { position: relative; overflow: hidden; margin-top: 0.85rem; border-radius: var(--radius-sm); background: var(--sidebar-bg); aspect-ratio: 16 / 10; }
.scanner-video-wrap video { width: 100%; height: 100%; object-fit: contain; }
.camera-loading { position: absolute; inset: 0; z-index: 2; display: grid; place-items: center; align-content: center; gap: 0.5rem; background: var(--sidebar-bg); color: var(--text-inverse); font-size: var(--fs-sm); }
.card-guide { position: absolute; inset: 50% auto auto 50%; width: min(78%, 32rem); aspect-ratio: 1.586; border: 2px solid var(--text-inverse); border-radius: var(--radius-xs); box-shadow: 0 0 0 100vmax rgba(28, 26, 23, 0.42); transform: translate(-50%, -50%); }
.card-guide span { position: absolute; inset: -3px; border: 1px solid rgba(255, 255, 255, 0.6); }
.card-detection { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.card-detection polygon { fill: rgba(36, 91, 94, 0.14); stroke: var(--accent); stroke-width: 5; vector-effect: non-scaling-stroke; }
.detection-state { position: absolute; top: 0.65rem; left: 50%; max-width: calc(100% - 1.3rem); padding: 0.25rem 0.5rem; border: 1px solid var(--accent-border); border-radius: var(--radius-xs); background: var(--surface); color: var(--accent); font-size: var(--fs-xs); font-weight: 650; text-align: center; transform: translateX(-50%); }
.scanner-video-instruction { position: absolute; inset: auto 0 0; margin: 0; padding: 0.7rem 1rem; background: rgba(28, 26, 23, 0.72); color: var(--text-inverse); font-size: var(--fs-sm); text-align: center; }
.scanner-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.85rem; }
.scanner-actions .btn { min-height: 44px; }
.scanner-message, .scanner-processing { display: flex; align-items: center; gap: 0.4rem; margin: 0.7rem 0 0; color: var(--success-text); font-size: var(--fs-sm); }
.scanner-message-error { color: var(--danger-text); }
.scanned-sides { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 0.5rem; padding: 0; margin: 0.85rem 0 0; list-style: none; }
.scanned-side { display: flex; min-width: 0; align-items: center; gap: 0.55rem; padding: 0.45rem; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--surface); }
.scanned-side img { width: 4rem; height: 2.6rem; border-radius: var(--radius-xs); object-fit: cover; }
.scanned-side div { display: grid; min-width: 0; flex: 1; }
.scanned-side strong { font-size: var(--fs-sm); }
.scanned-side small { overflow: hidden; color: var(--muted); font-size: var(--fs-xs); text-overflow: ellipsis; white-space: nowrap; }
.scanned-side .scanned-recognition { color: var(--success-text); }
.scanned-side .btn { min-width: 2.75rem; min-height: 2.75rem; }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
@media (max-width: 40rem) { .scanner-head { display: grid; } .scanner-state { justify-self: start; } }
</style>
