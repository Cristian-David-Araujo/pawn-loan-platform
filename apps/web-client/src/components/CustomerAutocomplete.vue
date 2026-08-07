<template>
  <div class="customer-autocomplete" ref="containerRef">
    <input
      :id="id"
      ref="inputRef"
      type="text"
      role="combobox"
      autocomplete="off"
      aria-haspopup="listbox"
      :aria-expanded="isOpen"
      :aria-controls="listboxId"
      :aria-activedescendant="isOpen && activeIndex >= 0 ? `${listboxId}-opt-${activeIndex}` : undefined"
      v-model="searchQuery"
      @focus="isOpen = true"
      @input="onInput"
      @keydown="onKeydown"
      :placeholder="placeholder"
      :class="inputClass"
    />
    <ul
      v-if="isOpen && filteredCustomers.length > 0"
      :id="listboxId"
      ref="listRef"
      class="autocomplete-dropdown"
      role="listbox"
    >
      <li
        v-for="(customer, index) in filteredCustomers"
        :key="customer.id"
        :id="`${listboxId}-opt-${index}`"
        role="option"
        :aria-selected="customer.id === modelValue"
        :class="{ 'is-active': index === activeIndex }"
        @mousedown.prevent="selectCustomer(customer)"
        @click.stop="selectCustomer(customer)"
        @mousemove="activeIndex = index"
      >
        <span class="customer-name">{{ customer.fullName }}</span>
        <span class="customer-doc muted">{{ customer.documentType }} {{ customer.documentNumber }}</span>
      </li>
    </ul>
    <div
      v-else-if="isOpen && searchQuery && filteredCustomers.length === 0"
      class="autocomplete-dropdown empty"
      role="status"
    >
      {{ t('customers.noMatches', { query: searchQuery }) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  modelValue: number | null
  customers: any[]
  placeholder?: string
  inputClass?: string
  id?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | null): void
}>()

const { t } = useI18n()

const searchQuery = ref('')
const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const listRef = ref<HTMLElement | null>(null)
const listboxId = `customer-ac-${useId()}`
const activeIndex = ref(-1)

watch(searchQuery, (newVal) => {
  if (!newVal && props.modelValue !== null) {
    emit('update:modelValue', null)
  }
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    const cust = props.customers.find(c => c.id === newVal)
    searchQuery.value = cust ? `${cust.fullName}` : ''
  } else {
    searchQuery.value = ''
  }
}, { immediate: true })

const filteredCustomers = computed(() => {
  if (!searchQuery.value) return props.customers.slice(0, 50)
  const q = searchQuery.value.toLowerCase()
  return props.customers.filter(c =>
    c.fullName.toLowerCase().includes(q) ||
    (c.documentNumber && c.documentNumber.includes(q))
  ).slice(0, 50)
})

// A fresh query invalidates whichever row the keyboard was sitting on.
const onInput = () => {
  isOpen.value = true
  activeIndex.value = -1
}

const selectCustomer = (customer: any) => {
  searchQuery.value = `${customer.fullName}`
  isOpen.value = false
  activeIndex.value = -1
  emit('update:modelValue', customer.id)
  inputRef.value?.blur()
}

/* The collector types a name and expects to arrow onto it. Without this the list could only
   be answered with the mouse, which is the slowest thing to reach for at a counter. */
const onKeydown = (event: KeyboardEvent) => {
  const options = filteredCustomers.value

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      isOpen.value = true
      if (options.length) activeIndex.value = Math.min(activeIndex.value + 1, options.length - 1)
      break
    case 'ArrowUp':
      event.preventDefault()
      if (options.length) activeIndex.value = Math.max(activeIndex.value - 1, 0)
      break
    case 'Enter':
      if (isOpen.value && activeIndex.value >= 0 && options[activeIndex.value]) {
        event.preventDefault()
        selectCustomer(options[activeIndex.value])
      }
      break
    case 'Escape':
      if (!isOpen.value) return
      event.preventDefault()
      isOpen.value = false
      activeIndex.value = -1
      break
    case 'Tab':
      isOpen.value = false
      activeIndex.value = -1
      break
  }
}

watch(activeIndex, async (index) => {
  if (!isOpen.value || index < 0) return
  await nextTick()
  listRef.value?.querySelector<HTMLElement>(`#${CSS.escape(listboxId)}-opt-${index}`)
    ?.scrollIntoView({ block: 'nearest' })
})

const handleClickOutside = (e: MouseEvent) => {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    isOpen.value = false
    activeIndex.value = -1
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
.customer-autocomplete {
  position: relative;
  width: 100%;
}

.autocomplete-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  max-height: 250px;
  overflow-y: auto;
  z-index: var(--z-dropdown);
  list-style: none;
  padding: 0;
  margin: 4px 0 0 0;
  box-shadow: var(--shadow-md);
}

.autocomplete-dropdown li {
  padding: 0.5rem 0.8rem;
  cursor: pointer;
  border-bottom: 1px solid var(--line-light);
  display: flex;
  flex-direction: column;
  transition: background-color var(--transition-fast);
}

.autocomplete-dropdown li:last-child {
  border-bottom: none;
}

/* Pointer and keyboard land on the same treatment. */
.autocomplete-dropdown li:hover,
.autocomplete-dropdown li.is-active {
  background: var(--surface-hover);
}

.customer-name {
  font-weight: 600;
  color: var(--text);
}

.customer-doc {
  font-size: var(--fs-sm);
  margin-top: 1px;
  font-variant-numeric: tabular-nums;
}

.autocomplete-dropdown.empty {
  padding: 0.75rem 0.8rem;
  color: var(--muted);
  font-size: var(--fs-sm);
  text-align: center;
}
</style>
