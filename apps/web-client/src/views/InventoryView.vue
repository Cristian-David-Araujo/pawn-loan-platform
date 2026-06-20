<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platformStore'
import { AlertCircle, Package, DollarSign, Search, Filter } from 'lucide-vue-next'

const { t } = useI18n()
const store = usePlatformStore()

const items = ref<any[]>([])
const loading = ref(true)
const searchQuery = ref('')
const filterStatus = ref('for_sale') // for_sale or sold

const showSellModal = ref(false)
const selectedItem = ref<any>(null)
const salePrice = ref<number | null>(null)
const saleNotes = ref('')
const isSubmitting = ref(false)
const confirmStep = ref(1)

onMounted(async () => {
  await loadItems()
})

const loadItems = async () => {
  try {
    loading.value = true
    items.value = await store.fetchCollateralItems()
  } catch (err: any) {
    alert(t('common.errors?.generic') || 'Error fetching data')
  } finally {
    loading.value = false
  }
}

const filteredItems = computed(() => {
  return items.value.filter((i: any) => {
    if (filterStatus.value && i.status !== filterStatus.value) return false
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      return i.description.toLowerCase().includes(q) || i.custody_code?.toLowerCase().includes(q)
    }
    return true
  })
})

const openSellModal = (item: any) => {
  selectedItem.value = item
  salePrice.value = item.appraised_value || item.appraisedValue || 0
  saleNotes.value = ''
  confirmStep.value = 1
  showSellModal.value = true
}

const closeSellModal = () => {
  showSellModal.value = false
  selectedItem.value = null
  salePrice.value = null
  saleNotes.value = ''
  confirmStep.value = 1
}

const handleSell = async () => {
  if (confirmStep.value === 1) {
    if (!salePrice.value || salePrice.value <= 0) {
      alert('Ingresa un precio valido')
      return
    }
    confirmStep.value = 2
    return
  }

  if (!selectedItem.value) return
  try {
    isSubmitting.value = true
    await store.sellCollateralItem(selectedItem.value.id, salePrice.value!, saleNotes.value)
    alert(t('common.success') || 'Success')
    closeSellModal()
    await loadItems()
  } catch (err: any) {
    alert(err.message || 'Error selling item')
    confirmStep.value = 1
  } finally {
    isSubmitting.value = false
  }
}

const formatCurrency = (val: number) => {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(val)
}
</script>

<template>
  <div class="inventory-view">
    <header class="page-header">
      <div class="header-content">
        <h1 class="page-title">{{ t('common.inventory.title') }}</h1>
        <p class="page-subtitle">{{ t('common.inventory.subtitle') }}</p>
      </div>
    </header>

    <div class="controls-bar">
      <div class="search-box">
        <Search class="search-icon" />
        <input 
          v-model="searchQuery"
          type="text" 
          :placeholder="t('common.search')"
          class="search-input"
        >
      </div>
      <div class="filter-box">
        <Filter class="filter-icon" />
        <select v-model="filterStatus" class="filter-select">
          <option value="for_sale">{{ t('common.inventory.statusForSale') }}</option>
          <option value="sold">{{ t('common.inventory.statusSold') }}</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ t('common.loading') }}</p>
    </div>

    <div v-else-if="filteredItems.length === 0" class="empty-state">
      <Package class="empty-icon" />
      <h3>{{ t('common.inventory.noItems') }}</h3>
    </div>

    <div v-else class="inventory-grid">
      <div 
        v-for="item in filteredItems" 
        :key="item.id"
        class="inventory-card"
      >
        <div class="card-header">
          <span class="custody-badge">{{ item.custody_code }}</span>
          <span :class="['status-badge', item.status]">{{ t(`common.inventory.status${item.status === 'for_sale' ? 'ForSale' : 'Sold'}`) }}</span>
        </div>
        <div class="card-body">
          <h3 class="item-desc">{{ item.description }}</h3>
          <p v-if="item.serial_number" class="item-meta">SN: {{ item.serial_number }}</p>
          <p class="item-meta">Avalúo: <strong class="appraised">{{ formatCurrency(item.appraised_value) }}</strong></p>
        </div>
        <div class="card-footer" v-if="item.status === 'for_sale'">
          <button class="btn btn-primary w-full" @click="openSellModal(item)">
            <DollarSign class="btn-icon" />
            {{ t('common.inventory.sellItem') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Sell Modal -->
    <div v-if="showSellModal" class="modal-overlay" @click.self="closeSellModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2 class="modal-title">{{ t('common.inventory.sellItem') }}</h2>
          <button class="close-btn" @click="closeSellModal">&times;</button>
        </div>
        
        <div class="modal-body">
          <div v-if="confirmStep === 1">
            <div class="form-group">
              <label>{{ t('common.inventory.salePrice') }}</label>
              <div class="input-with-icon">
                <DollarSign class="input-icon" />
                <input type="number" v-model="salePrice" class="form-input with-icon" min="0" step="0.01">
              </div>
            </div>
            <div class="form-group">
              <label>{{ t('common.inventory.notes') }}</label>
              <textarea v-model="saleNotes" class="form-input" rows="3"></textarea>
            </div>
          </div>
          <div v-else class="confirmation-step">
            <AlertCircle class="warning-icon" />
            <p>{{ t('common.inventory.confirmSellStepOne', { item: selectedItem?.description, price: formatCurrency(salePrice || 0) }) }}</p>
            <p class="text-muted mt-2">{{ t('common.inventory.confirmSellStepTwo') }}</p>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-ghost" @click="closeSellModal" :disabled="isSubmitting">
            {{ t('common.cancel') }}
          </button>
          <button class="btn btn-primary" @click="handleSell" :disabled="isSubmitting">
            <span v-if="isSubmitting" class="spinner-small"></span>
            <span v-else>{{ confirmStep === 1 ? t('common.continue') : t('common.confirm') }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inventory-view {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.page-subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

.controls-bar {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.search-box, .filter-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input, .filter-select {
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--text-primary);
  font-size: 0.95rem;
  min-width: 250px;
}

.search-icon, .filter-icon {
  position: absolute;
  left: 0.75rem;
  width: 18px;
  height: 18px;
  color: var(--text-secondary);
  pointer-events: none;
}

.inventory-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.inventory-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s, box-shadow 0.2s;
}

.inventory-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.card-header {
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0,0,0,0.01);
}

.custody-badge {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.for_sale {
  background: #fef3c7;
  color: #92400e;
}

.status-badge.sold {
  background: #dcfce7;
  color: #166534;
}

.card-body {
  padding: 1.5rem 1rem;
  flex: 1;
}

.item-desc {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.item-meta {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.appraised {
  color: var(--text-primary);
  font-size: 1.1rem;
}

.card-footer {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
  background: rgba(0,0,0,0.01);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.w-full {
  width: 100%;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  color: var(--text-secondary);
  text-align: center;
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--bg-surface);
  border-radius: 16px;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.5rem;
  line-height: 1;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-background);
  color: var(--text-primary);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.input-with-icon {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-secondary);
  width: 18px;
  height: 18px;
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-background);
  color: var(--text-primary);
  font-size: 1rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-input.with-icon {
  padding-left: 2.5rem;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.confirmation-step {
  text-align: center;
  padding: 2rem 1rem;
}

.warning-icon {
  width: 48px;
  height: 48px;
  color: #f59e0b;
  margin-bottom: 1rem;
}

.text-muted {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  background: rgba(0,0,0,0.02);
  border-radius: 0 0 16px 16px;
}

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover {
  background: var(--bg-background);
  color: var(--text-primary);
}

.spinner-small {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
</style>
