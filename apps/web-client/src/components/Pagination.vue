<template>
  <div v-if="totalPages > 1" class="pagination-wrapper">
    <div class="pagination-info">
      {{ t('common.showing') }} {{ startIndex + 1 }} - {{ Math.min(endIndex, totalItems) }} {{ t('common.of') }} {{ totalItems }}
    </div>
    <div class="pagination-controls">
      <button
        class="pagination-btn"
        :disabled="currentPage === 1"
        @click="goToPage(currentPage - 1)"
        type="button"
      >
        <ChevronLeft :size="16" />
      </button>

      <div class="pagination-pages">
        <template v-for="page in visiblePages" :key="page">
          <span v-if="page === '...'" class="pagination-ellipsis">...</span>
          <button
            v-else
            class="pagination-btn"
            :class="{ active: page === currentPage }"
            @click="goToPage(page as number)"
            type="button"
          >
            {{ page }}
          </button>
        </template>
      </div>

      <button
        class="pagination-btn"
        :disabled="currentPage === totalPages"
        @click="goToPage(currentPage + 1)"
        type="button"
      >
        <ChevronRight :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

const props = defineProps<{
  totalItems: number
  itemsPerPage: number
  modelValue: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', page: number): void
}>()

const { t } = useI18n()

const currentPage = computed({
  get: () => props.modelValue,
  set: (val: number) => emit('update:modelValue', val)
})

const totalPages = computed(() => Math.ceil(props.totalItems / props.itemsPerPage) || 1)

const startIndex = computed(() => (currentPage.value - 1) * props.itemsPerPage)
const endIndex = computed(() => startIndex.value + props.itemsPerPage)

// Reset to page 1 if total items changes and we are out of bounds
watch(() => props.totalItems, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = 1
  }
})

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

// Logic to show a max of 5 page buttons with ellipses
const visiblePages = computed(() => {
  const current = currentPage.value
  const total = totalPages.value
  
  if (total <= 5) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  
  if (current <= 3) {
    return [1, 2, 3, 4, '...', total]
  }
  
  if (current >= total - 2) {
    return [1, '...', total - 3, total - 2, total - 1, total]
  }
  
  return [1, '...', current - 1, current, current + 1, '...', total]
})
</script>

<style scoped>
.pagination-wrapper {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 0 0.5rem;
  margin-top: 1rem;
  border-top: 1px solid var(--line);
}

.pagination-info {
  font-size: 0.85rem;
  color: var(--muted);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.pagination-pages {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.pagination-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 0 0.5rem;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text);
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
}

.pagination-btn:hover:not(:disabled) {
  background: var(--surface-hover);
  border-color: var(--muted);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--surface-soft);
}

.pagination-btn.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.pagination-ellipsis {
  color: var(--muted);
  padding: 0 0.25rem;
  user-select: none;
}
</style>
