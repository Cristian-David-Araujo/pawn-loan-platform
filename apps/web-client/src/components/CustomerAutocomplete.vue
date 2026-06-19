<template>
  <div class="customer-autocomplete" ref="containerRef">
    <input 
      type="text" 
      v-model="searchQuery" 
      @focus="isOpen = true"
      @input="isOpen = true"
      :placeholder="placeholder" 
      class="w-100"
    />
    <ul v-if="isOpen && filteredCustomers.length > 0" class="autocomplete-dropdown">
      <li 
        v-for="customer in filteredCustomers" 
        :key="customer.id" 
        @click.stop="selectCustomer(customer)"
      >
        <span class="customer-name">{{ customer.fullName }}</span>
        <span class="customer-doc muted">{{ customer.documentType }} {{ customer.documentNumber }}</span>
      </li>
    </ul>
    <div v-else-if="isOpen && searchQuery && filteredCustomers.length === 0" class="autocomplete-dropdown empty">
      {{ t('common.searchPlaceholder') }} - No results.
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  modelValue: number | null
  customers: any[]
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | null): void
}>()

const { t } = useI18n()

const searchQuery = ref('')
const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)

watch(searchQuery, (newVal) => {
  if (!newVal && props.modelValue !== null) {
    emit('update:modelValue', null)
  }
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    const cust = props.customers.find(c => c.id === newVal)
    if (cust) {
      searchQuery.value = `${cust.fullName}`
    } else {
      searchQuery.value = ''
    }
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

const selectCustomer = (customer: any) => {
  searchQuery.value = `${customer.fullName}`
  isOpen.value = false
  emit('update:modelValue', customer.id)
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
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  max-height: 250px;
  overflow-y: auto;
  z-index: 1000;
  list-style: none;
  padding: 0;
  margin: 4px 0 0 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.autocomplete-dropdown li {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}
.autocomplete-dropdown li:last-child {
  border-bottom: none;
}
.autocomplete-dropdown li:hover {
  background: var(--surface-hover);
}
.customer-name {
  font-weight: 500;
  color: var(--text-color);
}
.customer-doc {
  font-size: 0.85rem;
  margin-top: 2px;
}
.autocomplete-dropdown.empty {
  padding: 10px 12px;
  color: var(--text-muted);
  text-align: center;
}
</style>
