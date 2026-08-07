<template>
  <section>
    <PageHeader :title="t('loans.title')" :subtitle="t('loans.subtitle')">
      <template #icon>
        <HandCoins :size="18" />
      </template>
      <template #actions>
        <button v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])" class="btn" type="button" @click="openCreateLoanModal">
          <FilePlus2 :size="16" />
          {{ t('loans.createLoan') }}
        </button>
      </template>
    </PageHeader>

    <!-- ── Create Loan Modal ──────────────────────────── -->
    <div v-if="showCreateLoanModal" class="modal-backdrop" @click.self="closeCreateLoanModal">
      <div class="modal-panel card modal-panel-lg">
        <div class="modal-header">
          <h3>{{ t('loans.createLoan') }}</h3>
          <button class="btn btn-secondary btn-icon" type="button" @click="closeCreateLoanModal">
            <X :size="16" />
          </button>
        </div>

        <form class="form mt-16" @submit.prevent="handleCreateLoan">
      <div class="form-section">
        <div class="form-section-head">
          <h3 class="form-section-title">{{ t('loans.loanDataSection') }}</h3>
        </div>
        <div class="grid grid-3">
        <label>
          {{ t('common.customer') }}
          <CustomerAutocomplete v-model="form.customerId" :customers="sortedCustomers" :placeholder="t('common.searchPlaceholder')" />
        </label>
        <label>
          {{ t('loans.loanType') }}
          <CustomSelect v-model="form.loanType" :options="loanTypeOptions" />
        </label>
        <label>
          {{ t('loans.principalAmount') }}
          <CurrencyInput v-model="form.principalAmount" :required="true" />
        </label>
        <label :title="t('loans.monthlyInterestRateHelp')">
          <span class="field-label-row">
            {{ t('loans.monthlyInterestRate') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
          <input
            v-model.number="form.monthlyInterestRate"
            type="number"
            min="0"
            step="0.1"
            required
            :title="t('loans.monthlyInterestRateHelp')"
          />
        </label>
        <label :title="t('loans.disbursementDateHelp')">
          <span class="field-label-row">
            {{ t('loans.disbursementDate') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
          <DateInputField
            v-model="form.disbursementDate"
            :label="t('loans.disbursementDate')"
            :placeholder="datePlaceholder"
            :required="true"
            :title="t('loans.disbursementDateHelp')"
          />
        </label>
        </div>
        <label class="mt-8">
          {{ t('loans.description') }}
          <textarea v-model="form.description" rows="2" :placeholder="t('loans.descriptionPlaceholder')" />
        </label>
      </div>

      <div class="form-section">
        <div class="form-section-head">
          <h3 class="form-section-title">{{ t('loans.latePenaltySection') }}</h3>
        </div>
        <label class="checkbox-row" :title="t('loans.applyLatePenaltyHelp')">
          <input v-model="applyLatePenalty" type="checkbox" />
          <span class="field-label-row">
            {{ t('loans.applyLatePenalty') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
        </label>
        <div v-if="applyLatePenalty">
          <label :title="t('loans.latePenaltyRateHelp')">
            <span class="field-label-row">
              {{ t('loans.latePenaltyRate') }}
              <span class="field-help" aria-hidden="true">ⓘ</span>
            </span>
            <input
              v-model.number="form.latePenaltyRate"
              type="number"
              min="0"
              step="0.1"
              required
              :title="t('loans.latePenaltyRateHelp')"
            />
          </label>
        </div>
      </div>

      <div class="form-section">
        <div class="form-section-head">
          <h3 class="form-section-title">{{ t('loans.collateralSection') }}</h3>
          <p class="muted">{{ t('loans.collateralSectionHint') }}</p>
        </div>
        <label class="checkbox-row" :title="t('loans.applyCollateralHelp')">
        <input v-model="applyCollateralAssociation" type="checkbox" />
        <span class="field-label-row">
          {{ t('loans.applyCollateral') }}
          <span class="field-help" aria-hidden="true">ⓘ</span>
        </span>
      </label>

      <div v-if="applyCollateralAssociation" class="grid grid-3">
        <label>
          {{ t('common.description') }}
          <input v-model="collateralForm.description" required />
        </label>
        <label>
          {{ t('collateral.appraisedValue') }}
          <CurrencyInput v-model="collateralForm.appraisedValue" :required="true" />
        </label>
        <label>
          {{ t('collateral.storageLocation') }}
          <input v-model="collateralForm.storageLocation" required />
        </label>
      </div>

      <div v-if="applyCollateralAssociation" class="form-inline">
        <button class="btn btn-secondary" type="button" @click="addCollateralToQueue">
          <FilePlus2 :size="16" />
          {{ t('loans.addCollateralToQueue') }}
        </button>
        <span class="pill">{{ t('loans.collateralQueueCount', { count: collateralQueue.length }) }}</span>
      </div>

      <table v-if="applyCollateralAssociation && collateralQueue.length">
        <thead>
          <tr>
            <th>{{ t('common.description') }}</th>
            <th>{{ t('collateral.appraisedValue') }}</th>
            <th>{{ t('collateral.storageLocation') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in collateralQueue" :key="`${item.description}-${index}`">
            <td>{{ item.description }}</td>
            <td>{{ formatCurrency(item.appraisedValue) }}</td>
            <td>{{ item.storageLocation }}</td>
            <td>
              <button class="btn btn-secondary" type="button" @click="removeCollateralFromQueue(index)">
                <Trash2 :size="16" />
                {{ t('loans.removeCollateralFromQueue') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <p v-if="formError" class="notice notice-warning mt-16">{{ formError }}</p>
      <div class="form-actions form-actions-split">
        <label class="checkbox-row">
          <input v-model="printInvoiceOnSave" type="checkbox" />
          {{ t('common.printInvoiceOnSave') }}
        </label>
        <button class="btn" type="submit">
          <FilePlus2 :size="16" />
          {{ t('loans.createLoan') }}
        </button>
      </div>
    </form>
      </div>
    </div>

    <div class="grid grid-4 mt-16">
      <StatCard :label="t('loans.summaryOutstanding')" :value="formatCurrency(loanSummary.outstanding)" :icon="HandCoins" tone="amber" />
      <StatCard :label="t('loans.summaryPendingInterest')" :value="formatCurrency(loanSummary.pendingInterest)" :icon="TrendingUp" tone="indigo" />
      <StatCard :label="t('loans.summaryActiveLoans')" :value="loanSummary.activeCount" :icon="BadgeDollarSign" tone="green" />
      <StatCard :label="t('loans.summaryOverdueLoans')" :value="loanSummary.overdueCount" :icon="ClockAlert" tone="amber" />
    </div>

    <div class="card mt-16">
      <div class="table-toolbar">
        <input v-model="search" class="table-search" type="text" :placeholder="t('loans.searchPlaceholder')" />
        <CustomSelect v-model="statusFilter" inputClass="table-select" :options="statusFilterOptions" />
        <button class="btn btn-secondary" type="button" @click="resetLoanFilters">
          <FilterX :size="16" />
          {{ t('loans.resetFilters') }}
        </button>
        <span class="table-count">{{ t('loans.totalLoans', { count: filteredLoans.length }) }}</span>
      </div>
      <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleLoanSort('id')">
                {{ t('common.id') }}
                <span v-if="getLoanSortBadge('id')" class="sort-indicator">{{ getLoanSortBadge('id') }}</span>
              </button>
            </th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleLoanSort('customer')">
                {{ t('common.customer') }}
                <span v-if="getLoanSortBadge('customer')" class="sort-indicator">{{ getLoanSortBadge('customer') }}</span>
              </button>
            </th>
            <th>{{ t('common.type') }}</th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleLoanSort('date')">
                {{ t('common.date') }}
                <span v-if="getLoanSortBadge('date')" class="sort-indicator">{{ getLoanSortBadge('date') }}</span>
              </button>
            </th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleLoanSort('principal')">
                {{ t('common.principal') }}
                <span v-if="getLoanSortBadge('principal')" class="sort-indicator">{{ getLoanSortBadge('principal') }}</span>
              </button>
            </th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleLoanSort('outstanding')">
                {{ t('loans.outstanding') }}
                <span v-if="getLoanSortBadge('outstanding')" class="sort-indicator">{{ getLoanSortBadge('outstanding') }}</span>
              </button>
            </th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleLoanSort('rate')">
                {{ t('loans.rate') }}
                <span v-if="getLoanSortBadge('rate')" class="sort-indicator">{{ getLoanSortBadge('rate') }}</span>
              </button>
            </th>
            <th class="text-right">
              <button class="sort-header-btn sort-header-end" type="button" @click="toggleLoanSort('interest')">
                {{ t('common.interest', 'Interés') }}
                <span v-if="getLoanSortBadge('interest')" class="sort-indicator">{{ getLoanSortBadge('interest') }}</span>
              </button>
            </th>
            <th class="text-center">{{ t('common.collaterals') }}</th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleLoanSort('status')">
                {{ t('common.status') }}
                <span v-if="getLoanSortBadge('status')" class="sort-indicator">{{ getLoanSortBadge('status') }}</span>
              </button>
            </th>
            <th>{{ t('common.createdBy', 'Generated by') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="loan in paginatedLoans" :key="loan.id" class="clickable-row" @click="openLoanDetail(loan.id)">
            <td>{{ loan.id }}</td>
            <td>{{ getCustomerLabel(loan.customerId) }}</td>
            <td>{{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
            <td>{{ formatDateDMY(loan.disbursementDate) }}</td>
            <td class="text-right">{{ formatCurrency(loan.principalAmount) }}</td>
            <td class="text-right">{{ formatCurrency(loan.outstandingPrincipal) }}</td>
            <td class="text-center">{{ loan.monthlyInterestRate }}%</td>
            <td class="text-right">
              <span v-if="loan.interestDue !== undefined && loan.interestDue !== null" class="text-warning-dark fw-bold">
                {{ formatCurrency(loan.interestDue) }}
              </span>
              <span v-else>-</span>
            </td>
            <td class="text-center">{{ loan.collateralsCount ?? (loan.loanType === 'personal' ? '-' : 0) }}</td>
            <td>
              <span :class="['pill', getLoanStatusClass(loan.status)]">
                {{ t(`common.${loan.status}`) }}
              </span>
            </td>
            <td>{{ loan?.created_by?.full_name || loan?.created_by?.username || '-' }}</td>
            <td>
              <a :href="'/print/invoice/loan/' + loan.id" target="_blank" class="btn btn-secondary btn-icon" :title="t('common.printInvoice')" @click.stop>
                <Printer :size="16" />
              </a>
            </td>
          </tr>
          <tr v-if="!filteredLoans.length">
            <td colspan="10">{{ t('loans.noLoansForFilter') }}</td>
          </tr>
        </tbody>
      </table>
      <Pagination v-model="loansCurrentPage" :totalItems="filteredLoans.length" :itemsPerPage="10" />
      </div>
    </div>

    <p v-if="message" class="notice mt-16">{{ message }}</p>

    <!-- ── Loan Detail Modal ──────────────────────────── -->
    <LoanDetailModal
      :show="showLoanDetailModal"
      :loan="selectedLoan"
      :customerName="selectedLoan ? getCustomerLabel(selectedLoan.customerId) : ''"
      :payments="selectedLoanPayments"
      :collaterals="selectedLoanCollateral"
      :financialDataLoading="financialDataLoading"
      :totalPendingInterest="totalPendingInterest"
      :totalPendingPenalty="totalPendingPenalty"
      @close="closeLoanDetail"
      @payments-changed="reloadLoanDetailFinancials"
    />
  </section>
</template>

<script setup lang="ts">
import CustomSelect from '../components/CustomSelect.vue'
import Pagination from '../components/Pagination.vue'
import { usePagination } from '../composables/usePagination'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useConfirmDialog } from '../composables/useConfirmDialog'
import LoanDetailModal from '../components/LoanDetailModal.vue'
import { BadgeDollarSign, ClockAlert, FilePlus2, FilterX, HandCoins, Trash2, TrendingUp, X, Printer } from 'lucide-vue-next'
import CustomerAutocomplete from '../components/CustomerAutocomplete.vue'
import DateInputField from '../components/DateInputField.vue'
import CurrencyInput from '../components/CurrencyInput.vue'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { usePlatformStore } from '../stores/platformStore'
import { useAuthState, UserRole } from '../modules/authentication/authState'
import { useCustomerLabel } from '../composables/useCustomerLabel'
import { formatCurrency } from '../utils/currency'
import { formatDateDMY, getGlobalDateFormat, toIsoDate } from '../utils/date'
import { apiClient } from '../services/api'

type SortDirection = 'asc' | 'desc'
type LoanSortKey = 'date' | 'id' | 'customer' | 'principal' | 'outstanding' | 'rate' | 'interest' | 'status'

interface SortCriterion<T extends string> {
  key: T
  direction: SortDirection
}

interface CollateralQueueItem {
  description: string
  appraisedValue: number
  storageLocation: string
}

interface InterestPendingItem {
  interest_charge_id: number
  loan_id: number
  remaining_pending_amount: number
  overdue: boolean
  penalty_amount: number
}

interface InterestPendingGroup {
  billing_period: string
  items: InterestPendingItem[]
}

interface InterestPendingResponse {
  customer_id: number
  groups: InterestPendingGroup[]
  total_pending_interest: number
  total_pending_penalty: number
  total_outstanding: number
}


const { state, createLoan, createCollateral, ensureInitialized } = usePlatformStore()
const { customerLabel: getCustomerLabel } = useCustomerLabel()
const { hasRole } = useAuthState()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
  const { confirm } = useConfirmDialog()

const loanTypeOptions = computed(() => [
  { value: 'pawn', label: t('common.pawn') },
  { value: 'personal', label: t('common.personal') }
])

const statusFilterOptions = computed(() => [
  { value: 'all', label: t('loans.allStatuses') },
  { value: 'active', label: t('common.active') },
  { value: 'overdue', label: t('common.overdue') },
  { value: 'closed', label: t('common.closed') }
])
const search = ref('')
const message = ref('')
const formError = ref('')

const getLoanStatusClass = (status: string) => {
  switch(status.toLowerCase()) {
    case 'active': return 'pill-current'
    case 'overdue': return 'pill-warning'
    case 'defaulted': return 'pill-overdue'
    case 'closed': return ''
    default: return ''
  }
}

const applyLatePenalty = ref(false)
const applyCollateralAssociation = ref(false)
const printInvoiceOnSave = ref(true)
/* Seeded from `?status=`, so the dashboard's overdue tile lands on the overdue loans rather
   than on the full list with the operator left to filter it themselves. Only the values the
   filter actually offers are honoured; anything else falls back to "all". */
const STATUS_FILTERS = ['all', 'active', 'overdue', 'closed'] as const
type StatusFilter = (typeof STATUS_FILTERS)[number]

const statusFromQuery = (): StatusFilter => {
  const value = route.query.status
  return typeof value === 'string' && (STATUS_FILTERS as readonly string[]).includes(value)
    ? (value as StatusFilter)
    : 'all'
}

const statusFilter = ref<StatusFilter>(statusFromQuery())
const loanSortPriority = ref<SortCriterion<LoanSortKey>[]>([{ key: 'date', direction: 'desc' }])
const selectedLoanId = ref<number | null>(null)
const showLoanDetailModal = ref(false)
const showCreateLoanModal = ref(false)
const openCreateLoanModal = () => { formError.value = ''; showCreateLoanModal.value = true }
const closeCreateLoanModal = () => { showCreateLoanModal.value = false }
const financialDataLoading = ref(false)
const financialDataError = ref(false)
const pendingInterestData = ref<InterestPendingResponse | null>(null)

const totalPendingInterest = computed(() => {
  if (!pendingInterestData.value) return 0
  let total = 0
  for (const group of pendingInterestData.value.groups) {
    for (const item of group.items) {
      if (item.loan_id === selectedLoanId.value) {
        total += item.remaining_pending_amount
      }
    }
  }
  return total
})

const totalPendingPenalty = computed(() => {
  if (!pendingInterestData.value) return 0
  let total = 0
  for (const group of pendingInterestData.value.groups) {
    for (const item of group.items) {
      if (item.loan_id === selectedLoanId.value) {
        total += item.penalty_amount
      }
    }
  }
  return total
})

const collateralQueue = ref<CollateralQueueItem[]>([])
const datePlaceholder = computed(() => getGlobalDateFormat())
const todayIso = new Date().toISOString().slice(0, 10)
const sortedCustomers = computed(() => [...state.customers].sort((a, b) => a.fullName.localeCompare(b.fullName)))

onMounted(async () => {
  await ensureInitialized()
  if (state.globalSettings) {
    form.latePenaltyRate = state.globalSettings.defaultLatePenaltyRate
  }
})

const form = reactive({
  customerId: null as number | null,
  loanType: 'pawn' as 'pawn' | 'personal',
  description: '',
  principalAmount: 1000,
  monthlyInterestRate: 8,
  latePenaltyRate: 0,
  disbursementDate: formatDateDMY(todayIso)
})

const handleCreateLoan = async () => {
  if (!form.customerId) {
    formError.value = 'Por favor selecciona un cliente.'
    return
  }

  const disbursementDate = toIsoDate(form.disbursementDate)
  if (!disbursementDate) {
    formError.value = t('messages.invalidDateFormat')
    return
  }

    if (form.loanType === 'pawn' && (!applyCollateralAssociation.value || collateralQueue.value.length === 0)) {
      formError.value = t('messages.pawnMustHaveCollateral')
      return
    }


  const payload = {
    ...form,
    customerId: form.customerId as number,
    disbursementDate,
    latePenaltyRate: applyLatePenalty.value ? form.latePenaltyRate : 0
  }

  const firstConfirmation = await confirm(
    t('loans.confirmRegisterLoanStepOne', {
      customer: getCustomerLabel(payload.customerId),
      amount: formatCurrency(payload.principalAmount)
    })
  )
  if (!firstConfirmation) {
    return
  }

  const secondConfirmation = await confirm(t('loans.confirmRegisterLoanStepTwo'))
  if (!secondConfirmation) {
    return
  }

  const createdLoan = await createLoan(payload)

  if (applyCollateralAssociation.value && collateralQueue.value.length) {
    for (const item of collateralQueue.value) {
      await createCollateral({
        loanId: createdLoan.id,
        description: item.description,
        appraisedValue: item.appraisedValue,
        storageLocation: item.storageLocation
      })
    }
  }

  form.disbursementDate = formatDateDMY(todayIso)
  form.loanType = 'pawn'
  form.description = ''
  message.value = t('messages.loanRegistered')
  collateralQueue.value = []
  collateralForm.description = ''
  collateralForm.appraisedValue = 1000
  collateralForm.storageLocation = 'Vault A-01'

  if (printInvoiceOnSave.value) {
    router.push(`/print/invoice/loan/${createdLoan.id}`)
  }
  closeCreateLoanModal()
}

const collateralForm = reactive({
  description: '',
  appraisedValue: 1000,
  storageLocation: 'Vault A-01'
})

const addCollateralToQueue = () => {
  if (!collateralForm.description.trim()) {
    return
  }

  collateralQueue.value = [
    ...collateralQueue.value,
    {
      description: collateralForm.description.trim(),
      appraisedValue: collateralForm.appraisedValue,
      storageLocation: collateralForm.storageLocation.trim()
    }
  ]

  collateralForm.description = ''
  collateralForm.appraisedValue = 1000
  collateralForm.storageLocation = 'Vault A-01'
}

const removeCollateralFromQueue = (index: number) => {
  collateralQueue.value = collateralQueue.value.filter((_, itemIndex) => itemIndex !== index)
}

const getSortDirectionSymbol = (direction: SortDirection) => (direction === 'asc' ? '↑' : '↓')

const getLoanSortMeta = (key: LoanSortKey) => {
  const index = loanSortPriority.value.findIndex((item) => item.key === key)
  if (index === -1) {
    return null
  }

  return {
    direction: loanSortPriority.value[index].direction,
    priority: index + 1
  }
}

const getLoanSortBadge = (key: LoanSortKey) => {
  const meta = getLoanSortMeta(key)
  if (!meta) {
    return ''
  }

  return `${getSortDirectionSymbol(meta.direction)}${meta.priority}`
}

const toggleLoanSort = (key: LoanSortKey) => {
  const index = loanSortPriority.value.findIndex((item) => item.key === key)

  if (index === -1) {
    loanSortPriority.value = [{ key, direction: 'asc' }, ...loanSortPriority.value]
    return
  }

  const current = loanSortPriority.value[index]
  const next = [...loanSortPriority.value]

  if (current.direction === 'asc') {
    const updated = { key, direction: 'desc' as SortDirection }
    next.splice(index, 1)
    loanSortPriority.value = [updated, ...next]
    return
  }

  next.splice(index, 1)
  loanSortPriority.value = next.length ? next : [{ key: 'date', direction: 'desc' }]
}

const resetLoanFilters = () => {
  search.value = ''
  statusFilter.value = 'all'
  loanSortPriority.value = [{ key: 'date', direction: 'desc' }]
}

const openLoanDetail = async (loanId: number) => {
  selectedLoanId.value = loanId
  showLoanDetailModal.value = true

  
  const loan = state.loans.find((l) => l.id === loanId)
  if (!loan) return
  
  financialDataLoading.value = true
  financialDataError.value = false
  
  try {
    const pending = await apiClient.request<InterestPendingResponse>(`/payments/customers/${loan.customerId}/interest-pending`)
    pendingInterestData.value = pending
  } catch (err) {
    financialDataError.value = true
    pendingInterestData.value = null
  } finally {
    financialDataLoading.value = false
  }
}

const closeLoanDetail = () => {
  showLoanDetailModal.value = false
}

/**
 * The detail modal can delete a payment, which changes the pending interest behind it.
 * `selectedLoanPayments` reads the store and the modal already refreshed it, so only the
 * pending-interest fetch has to be repeated here.
 */
const reloadLoanDetailFinancials = async () => {
  if (selectedLoanId.value !== null) {
    await openLoanDetail(selectedLoanId.value)
  }
}



const selectedLoan = computed(() => {
  if (selectedLoanId.value === null) {
    return null
  }

  return state.loans.find((loan) => loan.id === selectedLoanId.value) ?? null
})

const selectedLoanPayments = computed(() => {
  if (!selectedLoan.value) {
    return []
  }

  return state.payments
    .filter((payment) => payment.loanId === selectedLoan.value?.id)
    .sort((a, b) => new Date(b.paymentDate).getTime() - new Date(a.paymentDate).getTime())
})

const selectedLoanCollateral = computed(() => {
  if (!selectedLoan.value) {
    return []
  }

  return state.collateralItems.filter((item) => item.loanId === selectedLoan.value?.id)
})

const loanSummary = computed(() => {
  const openLoans = state.loans.filter((loan) => loan.status === 'active' || loan.status === 'overdue')

  return {
    outstanding: openLoans.reduce((sum, loan) => sum + loan.outstandingPrincipal, 0),
    pendingInterest: openLoans.reduce((sum, loan) => sum + (loan.interestDue ?? 0), 0),
    activeCount: state.loans.filter((loan) => loan.status === 'active').length,
    overdueCount: state.loans.filter((loan) => loan.status === 'overdue').length
  }
})

const filteredLoans = computed(() => {
  const query = search.value.trim().toLowerCase()

  const filtered = state.loans.filter((loan) => {
    const statusMatches = statusFilter.value === 'all' || loan.status === statusFilter.value
    const customer = getCustomerLabel(loan.customerId).toLowerCase()
    const textMatches = !query || `${loan.id} ${customer}`.includes(query)
    return statusMatches && textMatches
  })

  return [...filtered].sort((a, b) => {
    for (const criterion of loanSortPriority.value) {
      let result = 0

      if (criterion.key === 'id') {
        result = a.id - b.id
      } else if (criterion.key === 'customer') {
        result = getCustomerLabel(a.customerId).localeCompare(getCustomerLabel(b.customerId))
      } else if (criterion.key === 'principal') {
        result = a.principalAmount - b.principalAmount
      } else if (criterion.key === 'outstanding') {
        result = a.outstandingPrincipal - b.outstandingPrincipal
      } else if (criterion.key === 'rate') {
        result = a.monthlyInterestRate - b.monthlyInterestRate
      } else if (criterion.key === 'interest') {
        const valA = a.interestDue ?? 0
        const valB = b.interestDue ?? 0
        result = valA - valB
      } else if (criterion.key === 'status') {
        result = a.status.localeCompare(b.status)
      } else {
        result = new Date(a.disbursementDate).getTime() - new Date(b.disbursementDate).getTime()
      }

      if (result !== 0) {
        return criterion.direction === 'asc' ? result : -result
      }
    }

    return 0
  })
})

const { currentPage: loansCurrentPage, paginatedArray: paginatedLoans } = usePagination(filteredLoans)

</script>
