import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'

import IdentityDocumentScanner from '../components/IdentityDocumentScanner.vue'
import { messages } from '../i18n/messages'

const i18n = createI18n({ legacy: false, locale: 'es', fallbackLocale: 'en', messages })

describe('IdentityDocumentScanner camera preview', () => {
  const stopTrack = vi.fn()
  const stream = { getTracks: () => [{ stop: stopTrack }] } as unknown as MediaStream
  const getUserMedia = vi.fn().mockResolvedValue(stream)
  let playSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    stopTrack.mockClear()
    getUserMedia.mockClear()
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia }
    })
    Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', {
      configurable: true,
      writable: true,
      value: null
    })
    playSpy = vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
  })

  afterEach(() => {
    playSpy.mockRestore()
  })

  it('mounts the video before attaching the camera stream and shows the live preview', async () => {
    const wrapper = mount(IdentityDocumentScanner, {
      props: { modelValue: [] },
      global: { plugins: [i18n] }
    })

    await wrapper.get('.scanner-actions .btn').trigger('click')
    await flushPromises()

    expect(getUserMedia).toHaveBeenCalledWith({
      audio: false,
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      }
    })
    expect(wrapper.get('[data-testid="identity-camera-preview"]').isVisible()).toBe(true)
    expect((wrapper.get('video').element as HTMLVideoElement).srcObject).toBe(stream)
    expect(playSpy).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Vista previa en vivo')

    wrapper.unmount()
    expect(stopTrack).toHaveBeenCalledOnce()
  })
})
