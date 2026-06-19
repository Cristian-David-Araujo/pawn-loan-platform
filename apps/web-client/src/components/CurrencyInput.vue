<template>
  <input
    type="text"
    :value="formattedValue"
    @input="handleInput"
    :placeholder="placeholder"
    :required="required"
    :disabled="disabled"
    :class="inputClass"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: number
  placeholder?: string
  required?: boolean
  disabled?: boolean
  inputClass?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>()

const formattedValue = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined || isNaN(props.modelValue)) {
    return ''
  }
  if (props.modelValue === 0) {
    return '0'
  }
  return props.modelValue.toLocaleString('en-US')
})

const handleInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  const rawValue = target.value.replace(/\D/g, '')
  
  if (!rawValue) {
    emit('update:modelValue', 0)
    target.value = ''
    return
  }

  const numericValue = parseInt(rawValue, 10)
  emit('update:modelValue', numericValue)
  target.value = numericValue.toLocaleString('en-US')
}
</script>
