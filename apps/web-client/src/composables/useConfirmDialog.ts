import { ref } from 'vue'

const isOpen = ref(false)
const message = ref('')
const resolveCallback = ref<((value: boolean) => void) | null>(null)

export function useConfirmDialog() {
  const confirm = (msg: string): Promise<boolean> => {
    message.value = msg
    isOpen.value = true
    return new Promise((resolve) => {
      resolveCallback.value = resolve
    })
  }

  const accept = () => {
    isOpen.value = false
    if (resolveCallback.value) {
      resolveCallback.value(true)
      resolveCallback.value = null
    }
  }

  const cancel = () => {
    isOpen.value = false
    if (resolveCallback.value) {
      resolveCallback.value(false)
      resolveCallback.value = null
    }
  }

  return {
    isOpen,
    message,
    confirm,
    accept,
    cancel
  }
}
