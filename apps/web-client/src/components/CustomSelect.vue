<template>
  <div class="custom-select" ref="containerRef" :class="{ 'is-open': isOpen }">
    <button 
      :id="id"
      type="button" 
      class="select-button" 
      :class="inputClass"
      @click="toggleDropdown"
      :aria-expanded="isOpen"
      :disabled="disabled"
    >
      <span class="selected-label">{{ selectedLabel || placeholder || t('common.select') }}</span>
      <ChevronDown class="select-icon" :size="16" />
    </button>
    
    <ul v-if="isOpen" class="select-dropdown">
      <li 
        v-for="option in options" 
        :key="String(option.value)" 
        :class="{ 'is-selected': option.value === modelValue }"
        @mousedown.prevent="selectOption(option)"
        @click.stop="selectOption(option)"
      >
        {{ option.label }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

export interface SelectOption {
  value: string | number | null
  label: string
}

const props = defineProps<{
  modelValue: string | number | null
  options: SelectOption[]
  placeholder?: string
  inputClass?: string
  id?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number | null): void
  (e: 'change', value: string | number | null): void
}>()

const { t } = useI18n()

const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)

const selectedLabel = computed(() => {
  const selected = props.options.find(o => o.value === props.modelValue)
  return selected ? selected.label : ''
})

const toggleDropdown = () => {
  if (props.disabled) return
  isOpen.value = !isOpen.value
}

const selectOption = (option: SelectOption) => {
  if (props.disabled) return
  isOpen.value = false
  if (option.value !== props.modelValue) {
    emit('update:modelValue', option.value)
    emit('change', option.value)
  }
}

const handleClickOutside = (e: MouseEvent) => {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.custom-select {
  position: relative;
}
.select-button {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 0.65rem 1rem;
  font-family: inherit;
  font-size: 0.95rem;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: var(--transition);
  min-height: 48px;
}
.select-button:hover {
  border-color: #cbd5e1;
}
.select-button:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--shadow-focus);
  background: #fff;
}
.select-button:disabled {
  background: var(--surface-hover);
  color: var(--muted);
  cursor: not-allowed;
}
.is-open .select-button {
  border-color: var(--accent);
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}
.select-icon {
  color: var(--muted);
  transition: transform 0.2s ease;
}
.is-open .select-icon {
  transform: rotate(180deg);
}
.selected-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.select-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--surface);
  border: 1px solid var(--accent);
  border-top: none;
  border-bottom-left-radius: var(--radius-sm);
  border-bottom-right-radius: var(--radius-sm);
  max-height: 250px;
  overflow-y: auto;
  z-index: 1000;
  list-style: none;
  padding: 0;
  margin: 0;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  animation: slideDown 0.2s ease-out forwards;
  transform-origin: top;
}
@keyframes slideDown {
  from { opacity: 0; transform: scaleY(0.95); }
  to { opacity: 1; transform: scaleY(1); }
}
.select-dropdown li {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--line);
  color: var(--text);
  transition: background 0.1s ease;
}
.select-dropdown li:last-child {
  border-bottom: none;
}
.select-dropdown li:hover {
  background: var(--surface-hover);
}
.select-dropdown li.is-selected {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 500;
}
</style>
