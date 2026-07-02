<template>
  <div class="password-input">
    <input
      :type="visible ? 'text' : 'password'"
      :value="modelValue"
      v-bind="$attrs"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <button
      type="button"
      class="password-toggle"
      :aria-label="visible ? t('common.hidePassword') : t('common.showPassword')"
      :title="visible ? t('common.hidePassword') : t('common.showPassword')"
      @click="visible = !visible"
    >
      <EyeOff v-if="visible" :size="16" />
      <Eye v-else :size="16" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Eye, EyeOff } from 'lucide-vue-next'

defineOptions({ inheritAttrs: false })

defineProps<{ modelValue: string }>()
defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const { t } = useI18n()
const visible = ref(false)
</script>

<style scoped>
.password-input {
  position: relative;
  display: block;
  width: 100%;
}

.password-input input {
  width: 100%;
  padding-right: 2.6rem;
}

.password-toggle {
  position: absolute;
  top: 50%;
  right: 0.6rem;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  border: none;
  background: transparent;
  color: var(--color-text-muted, #6b7280);
  cursor: pointer;
  border-radius: 6px;
}

.password-toggle:hover,
.password-toggle:focus-visible {
  color: var(--color-text, #111827);
}
</style>
