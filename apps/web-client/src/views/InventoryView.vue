<template>
  <section>
    <PageHeader :title="t('inventory.title')" :subtitle="t('inventory.subtitle')">
      <template #icon>
        <Package :size="18" />
      </template>
    </PageHeader>

    <div class="card mt-16">
      <div class="table-toolbar">
        <input 
          v-model="searchQuery" 
          class="table-search" 
          type="text" 
          :placeholder="t('common.searchPlaceholder')" 
        />
        <CustomSelect 
          v-model="filterStatus" 
          inputClass="table-select" 
          :options="statusOptions" 
        />
        <span class="table-count">{{ t('inventory.totalItems', { count: filteredItems.length }, { default: `Total: ${filteredItems.length}` }) }}</span>
      </div>

      <div v-if="loading" class="text-center muted mt-16 p-16">
        {{ t('common.loading') }}
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ t('common.id') }}</th>
              <th>{{ t('collateral.custodyCode') }}</th>
              <th>{{ t('common.description') }}</th>
              <th>{{ t('collateral.appraisedValue') }}</th>
              <th>{{ t('common.status') }}</th>
              <th>{{ t('inventory.salePrice') }}</th>
              <th>{{ t('inventory.saleDate') }}</th>
              <th>{{ t('common.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in paginatedItems" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.custody_code || item.custodyCode }}</td>
              <td>
                <div><strong>{{ item.description }}</strong></div>
                <div v-if="item.serial_number || item.serialNumber" class="muted text-xs">SN: {{ item.serial_number || item.serialNumber }}</div>
              </td>
              <td>{{ formatCurrency(item.appraised_value || item.appraisedValue) }}</td>
              <td>
                <span :class="['pill', item.status === 'for_sale' ? 'bg-warning text-warning-dark' : 'bg-success text-success-dark']">
                  {{ t(`inventory.status${item.status === 'for_sale' ? 'ForSale' : 'Sold'}`) }}
                </span>
              </td>
              <td>{{ item.sale_price ? formatCurrency(item.sale_price) : '-' }}</td>
              <td>{{ item.sold_at ? formatDateDMY(item.sold_at.split('T')[0]) : '-' }}</td>
              <td>
                <button 
                  v-if="item.status === 'for_sale'" 
                  class="btn btn-secondary btn-sm" 
                  type="button" 
                  @click="openSellModal(item)"
                >
                  <DollarSign :size="14" />
                  {{ t('inventory.sellItem') }}
                </button>
              </td>
            </tr>
            <tr v-if="!filteredItems.length">
              <td colspan="8" class="text-center muted">{{ t('inventory.noItems') }}</td>
            </tr>
          </tbody>
        </table>
        <Pagination v-model="currentPage" :totalItems="filteredItems.length" :itemsPerPage="itemsPerPage" />
      </div>
    </div>

    <!-- Sell Modal (Using standard modal panel) -->
    <div v-if="showSellModal" class="modal-backdrop" @click.self="closeSellModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ t('inventory.sellItem') }}</h3>
          <button class="btn btn-secondary btn-icon" type="button" @click="closeSellModal">
            <X :size="16" />
          </button>
        </div>

        <div class="mt-16">
          <div v-if="confirmStep === 1">
            <label>
              {{ t('inventory.salePrice') }}
              <input type="number" v-model="salePrice" min="0" step="0.01" class="w-full mt-4" />
            </label>
            <label class="mt-16">
              {{ t('inventory.notes') }}
              <textarea v-model="saleNotes" rows="3" class="w-full mt-4"></textarea>
            </label>
          </div>
          <div v-else class="text-center p-16">
            <AlertTriangle :size="32" class="text-warning mx-auto mb-8" style="color: #d97706;" />
            <p><strong>{{ t('inventory.confirmSellStepOne', { item: selectedItem?.description, price: formatCurrency(salePrice || 0) }) }}</strong></p>
            <p class="muted mt-8">{{ t('inventory.confirmSellStepTwo') }}</p>
          </div>
        </div>

        <div class="form-actions mt-16" style="display: flex; justify-content: flex-end; gap: 1rem;">
          <button class="btn btn-secondary" type="button" @click="closeSellModal" :disabled="isSubmitting">
            {{ t('common.cancel') }}
          </button>
          <button class="btn" type="button" @click="handleSell" :disabled="isSubmitting">
            <span v-if="isSubmitting" class="spinner-small"></span>
            <span v-else>{{ confirmStep === 1 ? t('inventory.continue') : t('inventory.confirm') }}</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platformStore'
import PageHeader from '../components/PageHeader.vue'
import CustomSelect from '../components/CustomSelect.vue'
import Pagination from '../components/Pagination.vue'
import { Package, Search, DollarSign, X, AlertTriangle } from 'lucide-vue-next'

const { t, locale } = useI18n()
const store = usePlatformStore()

const items = ref<any[]>([])
const loading = ref(true)
const searchQuery = ref('')
const filterStatus = ref('for_sale') // for_sale or sold
const currentPage = ref(1)
const itemsPerPage = 10

const showSellModal = ref(false)
const selectedItem = ref<any>(null)
const salePrice = ref<number | null>(null)
const saleNotes = ref('')
const isSubmitting = ref(false)
const confirmStep = ref(1)

const statusOptions = computed(() => [
  { value: 'for_sale', label: t('inventory.statusForSale') },
  { value: 'sold', label: t('inventory.statusSold') },
  { value: '', label: t('loans.allStatuses') }
])

const currencyCode = computed(() => store.state.globalSettings?.currencyCode ?? 'COP')
const formatCurrency = (val: number) => {
  if (val === null || val === undefined) return '-'
  return new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: currencyCode.value }).format(val)
}

const formatDateDMY = (dateString: string) => {
  if (!dateString) return '-'
  const [y, m, d] = dateString.split('-')
  return `${d}/${m}/${y}`
}

onMounted(async () => {
  await loadItems()
})

const loadItems = async () => {
  try {
    loading.value = true
    const allItems = await store.fetchCollateralItems()
    // Inventory only cares about for_sale and sold
    items.value = allItems.filter((i: any) => i.status === 'for_sale' || i.status === 'sold')
  } catch (err: any) {
    alert(t('common.errors?.generic') || 'Error fetching data')
  } finally {
    loading.value = false
  }
}

const filteredItems = computed(() => {
  let result = items.value

  if (filterStatus.value) {
    result = result.filter(i => i.status === filterStatus.value)
  }

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(i => 
      i.description?.toLowerCase().includes(q) || 
      i.custody_code?.toLowerCase().includes(q) ||
      i.custodyCode?.toLowerCase().includes(q)
    )
  }
  
  return result.sort((a, b) => b.id - a.id) // Sort newest first
})

const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  return filteredItems.value.slice(start, start + itemsPerPage)
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
      alert(t('inventory.invalidPrice'))
      return
    }
    confirmStep.value = 2
    return
  }

  if (!selectedItem.value) return
  try {
    isSubmitting.value = true
    await store.sellCollateralItem(selectedItem.value.id, salePrice.value!, saleNotes.value)
    closeSellModal()
    await loadItems()
  } catch (err: any) {
    alert(err.message || t('inventory.sellError'))
    confirmStep.value = 1
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.pill {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.bg-warning { background-color: #fef3c7; }
.text-warning-dark { color: #92400e; }
.bg-success { background-color: #dcfce7; }
.text-success-dark { color: #166534; }
.text-warning { color: #d97706; }
.mx-auto { margin-left: auto; margin-right: auto; }
.mb-8 { margin-bottom: 0.5rem; }
.text-xs { font-size: 0.75rem; }
</style>
