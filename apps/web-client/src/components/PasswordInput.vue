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

/* These referenced --color-text-muted and --color-text, which this design system has never
   defined, so both fell through to the hardcoded cool greys in the fallback slot — the one
   place in the app still painting in the old palette. */
.password-toggle {
  position: absolute;
  top: 50%;
  right: 0.4rem;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.35rem;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  border-radius: var(--radius-xs);
  transition: background-color var(--transition), color var(--transition);
}

.password-toggle:hover,
.password-toggle:focus-visible {
  color: var(--text);
  background: var(--surface-hover);
}
</style>
