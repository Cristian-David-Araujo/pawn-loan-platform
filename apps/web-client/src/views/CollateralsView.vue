<template>
  <section>
    <PageHeader :title="t('collaterals.title')" :subtitle="t('collaterals.subtitle')">
      <template #icon>
        <Shield :size="18" />
      </template>
    </PageHeader>

    <div class="tabs mt-16">
      <button class="tab-btn" :class="{ active: activeTab === 'custody' }" @click="activeTab = 'custody'" type="button">
        {{ t('collaterals.tabCustody') }}
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'inventory' }" @click="activeTab = 'inventory'" type="button">
        {{ t('collaterals.tabInventory') }}
      </button>
    </div>

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
          :options="activeTab === 'custody' ? custodyStatusOptions : inventoryStatusOptions" 
        />
        <span class="table-count">{{ t('collaterals.totalItems', { count: filteredItems.length }, { default: `Total: ${filteredItems.length}` }) }}</span>
      </div>

      <div v-if="loading" class="text-center muted mt-16 p-16">
        {{ t('common.loading') }}
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr v-if="activeTab === 'custody'">
              <th>{{ t('common.id') }}</th>
              <th>{{ t('collateral.custodyCode') }}</th>
              <th>{{ t('common.description') }}</th>
              <th>{{ t('collateral.appraisedValue') }}</th>
              <th>{{ t('common.status') }}</th>
              <th>{{ t('common.loan') }}</th>
            </tr>
            <tr v-else>
              <th>{{ t('common.id') }}</th>
              <th>{{ t('collateral.custodyCode') }}</th>
              <th>{{ t('common.description') }}</th>
              <th>{{ t('collateral.appraisedValue') }}</th>
              <th>{{ t('common.loan') }}</th>
              <th>{{ t('common.status') }}</th>
              <th>{{ t('collaterals.salePrice') }}</th>
              <th>{{ t('collaterals.saleDate') }}</th>
              <th>{{ t('common.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in paginatedItems" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.custody_code || item.custodyCode }}</td>
              <td>{{ item.description }}</td>
              <td>{{ formatCurrency(item.appraised_value || item.appraisedValue) }}</td>
              
              <!-- Tab Custody Columns -->
              <template v-if="activeTab === 'custody'">
                <td>
                  <span :class="['pill', getStatusClass(item.status)]">
                    {{ getStatusLabel(item.status) }}
                  </span>
                </td>
                <td>
                  <div class="fw-bold">#{{ item.loan_id || item.loanId }}</div>
                  <div v-if="item.loan_status || item.loanStatus" class="muted text-xs mt-1">
                    <span :class="['pill', getLoanStatusClass(item.loan_status || item.loanStatus)]">
                      {{ t(`common.${(item.loan_status || item.loanStatus).toLowerCase()}`) }}
                    </span>
                  </div>
                </td>
              </template>

              <!-- Tab Inventory Columns -->
              <template v-else>
                <td>#{{ item.loan_id || item.loanId }}</td>
                <td>
                  <span :class="['pill', getStatusClass(item.status)]">
                    {{ getStatusLabel(item.status) }}
                  </span>
                </td>
                <td>{{ item.sale_price ? formatCurrency(item.sale_price) : '-' }}</td>
                <td>{{ item.sold_at ? formatDateDMY(item.sold_at.split('T')[0]) : '-' }}</td>
                <td>
                  <button 
                    v-if="item.status === 'for_sale'" 
                    class="btn btn-secondary btn-icon" 
                    type="button" 
                    :title="t('collaterals.sellItem')"
                    @click="openSellModal(item)"
                  >
                    <DollarSign :size="16" />
                  </button>
                </td>
              </template>

            </tr>
            <tr v-if="!filteredItems.length">
              <td :colspan="activeTab === 'custody' ? 6 : 9" class="text-center muted">{{ t('collaterals.noItems') }}</td>
            </tr>
          </tbody>
        </table>
        <Pagination v-model="currentPage" :totalItems="filteredItems.length" :itemsPerPage="itemsPerPage" />
      </div>
    </div>

    <!-- Sell Modal -->
    <div v-if="showSellModal" class="modal-backdrop" @click.self="closeSellModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ t('collaterals.sellItem') }}</h3>
          <button class="btn btn-secondary btn-icon" type="button" @click="closeSellModal">
            <X :size="16" />
          </button>
        </div>

        <div class="mt-16">
          <div v-if="confirmStep === 1">
            <label>
              {{ t('collaterals.salePrice') }}
              <input type="number" v-model="salePrice" min="0" step="0.01" class="w-full mt-4" />
            </label>
            <label class="mt-16">
              {{ t('collaterals.notes') }}
              <textarea v-model="saleNotes" rows="3" class="w-full mt-4"></textarea>
            </label>
          </div>
          <div v-else class="text-center p-16">
            <AlertTriangle :size="32" class="text-warning mx-auto mb-8" style="color: #d97706;" />
            <p><strong>{{ t('collaterals.confirmSellStepOne', { item: selectedItem?.description, price: formatCurrency(salePrice || 0) }) }}</strong></p>
            <p class="muted mt-8">{{ t('collaterals.confirmSellStepTwo') }}</p>
          </div>
        </div>

        <div class="form-actions mt-16" style="display: flex; justify-content: flex-end; gap: 1rem;">
          <button class="btn btn-secondary" type="button" @click="closeSellModal" :disabled="isSubmitting">
            {{ t('common.cancel') }}
          </button>
          <button class="btn" type="button" @click="handleSell" :disabled="isSubmitting">
            <span v-if="isSubmitting" class="spinner-small"></span>
            <span v-else>{{ confirmStep === 1 ? t('collaterals.continue') : t('collaterals.confirm') }}</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platformStore'
import PageHeader from '../components/PageHeader.vue'
import CustomSelect from '../components/CustomSelect.vue'
import Pagination from '../components/Pagination.vue'
import { Shield, Search, DollarSign, X, AlertTriangle } from 'lucide-vue-next'

const { t, locale } = useI18n()
const store = usePlatformStore()

const items = ref<any[]>([])
const loading = ref(true)
const searchQuery = ref('')
const activeTab = ref('custody')

const filterStatus = ref('')
const currentPage = ref(1)
const itemsPerPage = 10

const showSellModal = ref(false)
const selectedItem = ref<any>(null)
const salePrice = ref<number | null>(null)
const saleNotes = ref('')
const isSubmitting = ref(false)
const confirmStep = ref(1)

watch(activeTab, () => {
  filterStatus.value = ''
  currentPage.value = 1
})

const custodyStatusOptions = computed(() => [
  { value: '', label: t('loans.allStatuses') },
  { value: 'in_custody', label: t('collaterals.statusInCustody') },
  { value: 'returned', label: t('collaterals.statusReturned') },
  { value: 'released', label: t('collaterals.statusReleased') }
])

const inventoryStatusOptions = computed(() => [
  { value: '', label: t('loans.allStatuses') },
  { value: 'for_sale', label: t('collaterals.statusForSale') },
  { value: 'sold', label: t('collaterals.statusSold') },
  { value: 'liquidated', label: t('collaterals.statusLiquidated') }
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

const getStatusClass = (status: string) => {
  switch(status) {
    case 'in_custody': return 'pill-upcoming'
    case 'returned': return 'pill-current'
    case 'for_sale': return 'pill-warning'
    case 'sold': return 'pill-current'
    case 'released': return 'pill-upcoming'
    case 'liquidated': return 'pill-overdue'
    default: return ''
  }
}

const getLoanStatusClass = (status: string) => {
  switch(status.toLowerCase()) {
    case 'active': return 'pill-current'
    case 'overdue': return 'pill-warning'
    case 'defaulted': return 'pill-overdue'
    case 'closed': return ''
    default: return ''
  }
}

const getStatusLabel = (status: string) => {
  switch(status) {
    case 'in_custody': return t('collaterals.statusInCustody')
    case 'returned': return t('collaterals.statusReturned')
    case 'for_sale': return t('collaterals.statusForSale')
    case 'sold': return t('collaterals.statusSold')
    case 'released': return t('collaterals.statusReleased')
    case 'liquidated': return t('collaterals.statusLiquidated')
    default: return status
  }
}



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

const tabItems = computed(() => {
  if (activeTab.value === 'custody') {
    return items.value.filter(i => ['in_custody', 'returned', 'released'].includes(i.status))
  } else {
    return items.value.filter(i => ['for_sale', 'sold', 'liquidated'].includes(i.status))
  }
})

const filteredItems = computed(() => {
  let result = tabItems.value

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
  
  return result.sort((a, b) => b.id - a.id)
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
      alert(t('collaterals.invalidPrice'))
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
    alert(err.message || t('collaterals.sellError'))
    confirmStep.value = 1
  } finally {
    isSubmitting.value = false
  }
}
</script>

