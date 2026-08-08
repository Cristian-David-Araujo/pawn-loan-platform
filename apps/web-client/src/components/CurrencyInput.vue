<template>
  <input
    type="text"
    inputmode="numeric"
    class="currency-input"
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
import { formatAmountForInput, parseAmountFromInput } from '../utils/currency'

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

/* Grouping comes from the portfolio's currency, not from `en-US`. Typing an amount used to
   show `1,250,000` while every screen displaying it showed `1.250.000`. */
const formattedValue = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined || isNaN(props.modelValue)) {
    return ''
  }
  if (props.modelValue === 0) {
    return '0'
  }
  return formatAmountForInput(props.modelValue)
})

const handleInput = (e: Event) => {
  const target = e.target as HTMLInputElement

  if (!target.value.replace(/\D/g, '')) {
    emit('update:modelValue', 0)
    target.value = ''
    return
  }

  const numericValue = parseAmountFromInput(target.value)
  emit('update:modelValue', numericValue)
  target.value = formatAmountForInput(numericValue)
}
</script>

<style scoped>
/* Figures line up with every other amount on the screen. */
.currency-input {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
</style>
