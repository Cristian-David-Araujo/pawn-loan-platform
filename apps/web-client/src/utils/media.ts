export interface ImageCompressionOptions {
  maxDimension: number
  targetBytes: number
}

export interface PreparedFile {
  file: File
  compressed: boolean
}

const supportedImageTypes = new Set(['image/jpeg', 'image/png', 'image/webp'])

const fileStem = (name: string) => name.replace(/\.[^.]+$/, '') || 'imagen'

const canvasBlob = (canvas: HTMLCanvasElement, quality: number) =>
  new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))

/**
 * Reduces only oversized photos before they cross the network. Keeping the original when it
 * already fits avoids a second lossy encode; a scan that is huge is resized with enough room
 * for document text to remain legible.
 */
export const compressImageFile = async (
  file: File,
  { maxDimension, targetBytes }: ImageCompressionOptions
): Promise<PreparedFile> => {
  if (!supportedImageTypes.has(file.type) || typeof createImageBitmap === 'undefined') {
    return { file, compressed: false }
  }

  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    return { file, compressed: false }
  }

  try {
    const longestSide = Math.max(bitmap.width, bitmap.height)
    if (file.size <= targetBytes && longestSide <= maxDimension) {
      return { file, compressed: false }
    }

    const scale = Math.min(1, maxDimension / longestSide)
    const width = Math.max(1, Math.round(bitmap.width * scale))
    const height = Math.max(1, Math.round(bitmap.height * scale))
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d')
    if (!context) {
      return { file, compressed: false }
    }
    context.drawImage(bitmap, 0, 0, width, height)

    let output: Blob | null = null
    for (const quality of [0.88, 0.8, 0.72, 0.64, 0.56]) {
      output = await canvasBlob(canvas, quality)
      if (output && output.size <= targetBytes) {
        break
      }
    }
    if (!output) {
      return { file, compressed: false }
    }

    return {
      file: new File([output], `${fileStem(file.name)}.jpg`, {
        type: 'image/jpeg',
        lastModified: file.lastModified
      }),
      compressed: true
    }
  } finally {
    bitmap.close()
  }
}

export const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
