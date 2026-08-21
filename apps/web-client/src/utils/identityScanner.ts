import { compressImageFile } from './media'

export type IdentityDocumentSide = 'front' | 'back' | 'combined'

export interface PendingIdentityDocument {
  side: IdentityDocumentSide
  file: File
}

interface DocumentCrop {
  x: number
  y: number
  width: number
  height: number
  confidence: number
}

const ID_CARD_RATIO = 1.586

const blobFromCanvas = (canvas: HTMLCanvasElement) =>
  new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92))

const centeredCardCrop = (width: number, height: number): DocumentCrop => {
  const availableWidth = width * 0.92
  const availableHeight = height * 0.92
  const cropWidth = Math.min(availableWidth, availableHeight * ID_CARD_RATIO)
  const cropHeight = cropWidth / ID_CARD_RATIO
  return {
    x: Math.round((width - cropWidth) / 2),
    y: Math.round((height - cropHeight) / 2),
    width: Math.round(cropWidth),
    height: Math.round(cropHeight),
    confidence: 0.25
  }
}

/**
 * Finds the four longest contrast transitions near the expected card boundary. It is a
 * deliberately light browser-only detector: no image or document is sent to a third party,
 * and when a busy background hides an edge it falls back to the framing guide instead of
 * producing an unusable crop.
 */
const detectCardCrop = (canvas: HTMLCanvasElement): DocumentCrop => {
  const sampleWidth = Math.min(480, canvas.width)
  const sampleHeight = Math.max(1, Math.round((canvas.height / canvas.width) * sampleWidth))
  const sample = document.createElement('canvas')
  sample.width = sampleWidth
  sample.height = sampleHeight
  const context = sample.getContext('2d', { willReadFrequently: true })
  if (!context) return centeredCardCrop(canvas.width, canvas.height)
  context.drawImage(canvas, 0, 0, sampleWidth, sampleHeight)
  const pixels = context.getImageData(0, 0, sampleWidth, sampleHeight).data
  const vertical = Array<number>(sampleWidth).fill(0)
  const horizontal = Array<number>(sampleHeight).fill(0)

  const luminanceAt = (x: number, y: number) => {
    const index = (y * sampleWidth + x) * 4
    return pixels[index] * 0.2126 + pixels[index + 1] * 0.7152 + pixels[index + 2] * 0.0722
  }

  for (let y = 1; y < sampleHeight - 1; y += 2) {
    for (let x = 1; x < sampleWidth - 1; x += 2) {
      const edgeX = Math.abs(luminanceAt(x + 1, y) - luminanceAt(x - 1, y))
      const edgeY = Math.abs(luminanceAt(x, y + 1) - luminanceAt(x, y - 1))
      vertical[x] += edgeX
      horizontal[y] += edgeY
    }
  }

  const strongest = (scores: number[], start: number, end: number) => {
    let index = start
    for (let current = start + 1; current < end; current += 1) {
      if (scores[current] > scores[index]) index = current
    }
    return { index, score: scores[index] }
  }
  const left = strongest(vertical, Math.round(sampleWidth * 0.04), Math.round(sampleWidth * 0.48))
  const right = strongest(vertical, Math.round(sampleWidth * 0.52), Math.round(sampleWidth * 0.96))
  const top = strongest(horizontal, Math.round(sampleHeight * 0.04), Math.round(sampleHeight * 0.48))
  const bottom = strongest(horizontal, Math.round(sampleHeight * 0.52), Math.round(sampleHeight * 0.96))
  const detectedWidth = right.index - left.index
  const detectedHeight = bottom.index - top.index
  const ratio = detectedWidth / Math.max(1, detectedHeight)
  const score = left.score + right.score + top.score + bottom.score
  const meanScore =
    (vertical.reduce((sum, value) => sum + value, 0) + horizontal.reduce((sum, value) => sum + value, 0)) /
    (sampleWidth + sampleHeight)

  if (
    detectedWidth < sampleWidth * 0.35 ||
    detectedHeight < sampleHeight * 0.2 ||
    ratio < 1.15 ||
    ratio > 2.2 ||
    score < meanScore * 4
  ) {
    return centeredCardCrop(canvas.width, canvas.height)
  }

  const scaleX = canvas.width / sampleWidth
  const scaleY = canvas.height / sampleHeight
  const paddingX = detectedWidth * 0.025
  const paddingY = detectedHeight * 0.025
  return {
    x: Math.max(0, Math.round((left.index - paddingX) * scaleX)),
    y: Math.max(0, Math.round((top.index - paddingY) * scaleY)),
    width: Math.min(canvas.width, Math.round((detectedWidth + paddingX * 2) * scaleX)),
    height: Math.min(canvas.height, Math.round((detectedHeight + paddingY * 2) * scaleY)),
    confidence: Math.min(1, score / Math.max(1, meanScore * 8))
  }
}

const cropCanvas = (source: HTMLCanvasElement) => {
  const crop = detectCardCrop(source)
  const target = document.createElement('canvas')
  target.width = crop.width
  target.height = crop.height
  const context = target.getContext('2d')
  if (!context) throw new Error('No se pudo preparar el escaneo')
  context.drawImage(source, crop.x, crop.y, crop.width, crop.height, 0, 0, crop.width, crop.height)
  return { canvas: target, confidence: crop.confidence }
}

const fingerprint = (canvas: HTMLCanvasElement) => {
  const size = 12
  const sample = document.createElement('canvas')
  sample.width = size
  sample.height = size
  const context = sample.getContext('2d', { willReadFrequently: true })
  if (!context) return []
  context.drawImage(canvas, 0, 0, size, size)
  const pixels = context.getImageData(0, 0, size, size).data
  return Array.from({ length: size * size }, (_, index) => {
    const offset = index * 4
    return (pixels[offset] + pixels[offset + 1] + pixels[offset + 2]) / (3 * 255)
  })
}

export const fingerprintDifference = (first: number[], second: number[]) => {
  if (!first.length || first.length !== second.length) return 1
  return first.reduce((sum, value, index) => sum + Math.abs(value - second[index]), 0) / first.length
}

export const scanCanvasToFile = async (source: HTMLCanvasElement, side: IdentityDocumentSide) => {
  const { canvas, confidence } = cropCanvas(source)
  const blob = await blobFromCanvas(canvas)
  if (!blob) throw new Error('No se pudo crear el escaneo')
  const raw = new File([blob], `cedula-${side}.jpg`, { type: 'image/jpeg' })
  const prepared = await compressImageFile(raw, { maxDimension: 2400, targetBytes: 2_500_000 })
  return { file: prepared.file, confidence, fingerprint: fingerprint(canvas) }
}

const canvasFromImageFile = async (file: File) => {
  const bitmap = await createImageBitmap(file)
  try {
    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    const context = canvas.getContext('2d')
    if (!context) throw new Error('No se pudo leer la imagen')
    context.drawImage(bitmap, 0, 0)
    return canvas
  } finally {
    bitmap.close()
  }
}

/** Splits a landscape or portrait sheet with two IDs, then crops each side independently. */
export const segmentIdentityImage = async (file: File): Promise<PendingIdentityDocument[]> => {
  const canvas = await canvasFromImageFile(file)
  const ratio = canvas.width / canvas.height
  const twoAcross = ratio >= 2.1
  const twoDown = ratio <= 0.68
  if (!twoAcross && !twoDown) {
    const scan = await scanCanvasToFile(canvas, 'front')
    return [{ side: 'front', file: scan.file }]
  }

  const first = document.createElement('canvas')
  const second = document.createElement('canvas')
  if (twoAcross) {
    const half = Math.floor(canvas.width / 2)
    first.width = second.width = half
    first.height = second.height = canvas.height
    first.getContext('2d')?.drawImage(canvas, 0, 0, half, canvas.height, 0, 0, half, canvas.height)
    second.getContext('2d')?.drawImage(canvas, half, 0, half, canvas.height, 0, 0, half, canvas.height)
  } else {
    const half = Math.floor(canvas.height / 2)
    first.width = second.width = canvas.width
    first.height = second.height = half
    first.getContext('2d')?.drawImage(canvas, 0, 0, canvas.width, half, 0, 0, canvas.width, half)
    second.getContext('2d')?.drawImage(canvas, 0, half, canvas.width, half, 0, 0, canvas.width, half)
  }
  const [front, back] = await Promise.all([scanCanvasToFile(first, 'front'), scanCanvasToFile(second, 'back')])
  return [
    { side: 'front', file: front.file },
    { side: 'back', file: back.file }
  ]
}
