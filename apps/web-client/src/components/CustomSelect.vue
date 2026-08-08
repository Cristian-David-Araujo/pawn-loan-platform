<template>
  <div class="custom-select" ref="containerRef" :class="{ 'is-open': isOpen }">
    <button
      :id="id"
      ref="buttonRef"
      type="button"
      class="select-button"
      :class="[inputClass, { 'is-placeholder': !selectedLabel }]"
      role="combobox"
      aria-haspopup="listbox"
      :aria-expanded="isOpen"
      :aria-controls="listboxId"
      :aria-activedescendant="isOpen && activeIndex >= 0 ? `${listboxId}-opt-${activeIndex}` : undefined"
      :disabled="disabled"
      @click="toggleDropdown"
      @keydown="onButtonKeydown"
    >
      <span class="selected-label">{{ selectedLabel || placeholder || t('common.select') }}</span>
      <ChevronDown class="select-icon" :size="16" aria-hidden="true" />
    </button>

    <ul v-if="isOpen" :id="listboxId" class="select-dropdown" role="listbox" ref="listRef">
      <li
        v-for="(option, index) in options"
        :key="String(option.value)"
        :id="`${listboxId}-opt-${index}`"
        role="option"
        :aria-selected="option.value === modelValue"
        :class="{ 'is-selected': option.value === modelValue, 'is-active': index === activeIndex }"
        @mousedown.prevent="selectOption(option)"
        @click.stop="selectOption(option)"
        @mousemove="activeIndex = index"
      >
        {{ option.label }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, useId, watch } from 'vue'
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
const buttonRef = ref<HTMLButtonElement | null>(null)
const listRef = ref<HTMLElement | null>(null)
const listboxId = `select-${useId()}`

/* The option the keyboard is sitting on. Tracked separately from the selected
   value: arrowing through a list must not commit anything until Enter, or a
   keyboard user would fire a change event for every option they pass over. */
const activeIndex = ref(-1)

const selectedLabel = computed(() => {
  const selected = props.options.find((o) => o.value === props.modelValue)
  return selected ? selected.label : ''
})

const selectedIndex = () => props.options.findIndex((o) => o.value === props.modelValue)

const openDropdown = (startAt?: number) => {
  if (props.disabled) return
  isOpen.value = true
  activeIndex.value = startAt ?? (selectedIndex() >= 0 ? selectedIndex() : 0)
}

const closeDropdown = () => {
  isOpen.value = false
  activeIndex.value = -1
}

const toggleDropdown = () => {
  if (props.disabled) return
  if (isOpen.value) closeDropdown()
  else openDropdown()
}

const selectOption = (option: SelectOption) => {
  if (props.disabled) return
  closeDropdown()
  if (option.value !== props.modelValue) {
    emit('update:modelValue', option.value)
    emit('change', option.value)
  }
}

const moveActive = (delta: number) => {
  if (!props.options.length) return
  const next = activeIndex.value + delta
  activeIndex.value = Math.min(Math.max(next, 0), props.options.length - 1)
}

/* The whole control is one button, so every key has to be handled here. Without
   this the app's only dropdown could be opened from the keyboard but never
   answered — the options were plain <li> with mouse handlers. */
const onButtonKeydown = (event: KeyboardEvent) => {
  if (props.disabled) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      if (isOpen.value) moveActive(1)
      else openDropdown()
      break
    case 'ArrowUp':
      event.preventDefault()
      if (isOpen.value) moveActive(-1)
      else openDropdown(props.options.length - 1)
      break
    case 'Home':
      if (!isOpen.value) return
      event.preventDefault()
      activeIndex.value = 0
      break
    case 'End':
      if (!isOpen.value) return
      event.preventDefault()
      activeIndex.value = props.options.length - 1
      break
    case 'Enter':
    case ' ':
      event.preventDefault()
      if (isOpen.value && activeIndex.value >= 0) selectOption(props.options[activeIndex.value])
      else openDropdown()
      break
    case 'Escape':
      if (!isOpen.value) return
      event.preventDefault()
      closeDropdown()
      break
    case 'Tab':
      // Tabbing away commits nothing and leaves the list closed.
      closeDropdown()
      break
  }
}

// Keep the active option inside the scroll area of a long list.
watch(activeIndex, async (index) => {
  if (!isOpen.value || index < 0) return
  await nextTick()
  listRef.value?.querySelector<HTMLElement>(`#${CSS.escape(listboxId)}-opt-${index}`)
    ?.scrollIntoView({ block: 'nearest' })
})

const handleClickOutside = (e: MouseEvent) => {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    closeDropdown()
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
  gap: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.8rem;
  font-family: inherit;
  font-size: var(--fs-base);
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: border-color var(--transition), box-shadow var(--transition);
  min-height: 44px;
}

.select-button:hover:not(:disabled) {
  border-color: var(--line-hover);
}

.select-button:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--shadow-focus);
}

.select-button:disabled {
  background: var(--surface-soft);
  color: var(--muted);
  cursor: not-allowed;
  border-color: var(--line);
}

/* An unanswered dropdown reads as a prompt, not as a value. */
.select-button.is-placeholder .selected-label {
  color: var(--muted);
}

.is-open .select-button {
  border-color: var(--accent);
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.select-icon {
  color: var(--muted);
  flex-shrink: 0;
  transition: transform var(--transition);
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
  z-index: var(--z-dropdown);
  list-style: none;
  padding: 0;
  margin: 0;
  box-shadow: var(--shadow-md);
  animation: select-in 140ms var(--ease);
  transform-origin: top;
}

@keyframes select-in {
  from { opacity: 0; transform: scaleY(0.97); }
  to { opacity: 1; transform: scaleY(1); }
}

.select-dropdown li {
  padding: 0.5rem 0.8rem;
  font-size: var(--fs-base);
  cursor: pointer;
  border-bottom: 1px solid var(--line-light);
  color: var(--text);
  transition: background-color var(--transition-fast);
}

.select-dropdown li:last-child {
  border-bottom: none;
}

/* Pointer hover and keyboard focus land on the same treatment, so the list
   looks the same however it is being driven. */
.select-dropdown li:hover,
.select-dropdown li.is-active {
  background: var(--surface-hover);
}

.select-dropdown li.is-selected {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.select-dropdown li.is-selected.is-active {
  background: var(--accent-border);
}

@media (prefers-reduced-motion: reduce) {
  .select-dropdown { animation: none; }
}
</style>
