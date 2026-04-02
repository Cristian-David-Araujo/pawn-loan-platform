<template>
  <section>
    <PageHeader :title="t('loans.title')" :subtitle="t('loans.subtitle')">
      <template #icon>
        <HandCoins :size="18" />
      </template>
    </PageHeader>

    <form class="card form mt-16" @submit.prevent="handleCreateLoan">
      <div class="form-section">
        <div class="form-section-head">
          <h3 class="form-section-title">{{ t('loans.loanDataSection') }}</h3>
        </div>
        <div class="grid grid-3">
        <label>
          {{ t('common.customer') }}
          <select v-model.number="form.customerId" required>
            <option v-for="customer in sortedCustomers" :key="customer.id" :value="customer.id">
              {{ customer.fullName }}
            </option>
          </select>
        </label>
        <label>
          {{ t('loans.loanType') }}
          <select v-model="form.loanType" required>
            <option value="pawn">{{ t('common.pawn') }}</option>
            <option value="personal">{{ t('common.personal') }}</option>
          </select>
        </label>
        <label>
          {{ t('loans.principalAmount') }}
          <input v-model.number="form.principalAmount" type="number" min="1" required />
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
          <input
            v-model="form.disbursementDate"
            :placeholder="datePlaceholder"
            required
            :title="t('loans.disbursementDateHelp')"
          />
        </label>
        </div>
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
        <div v-if="applyLatePenalty" class="grid grid-3">
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
          <label :title="t('loans.graceDaysHelp')">
            <span class="field-label-row">
              {{ t('loans.dueDay') }}
              <span class="field-help" aria-hidden="true">ⓘ</span>
            </span>
            <input
              v-model.number="form.dueDay"
              type="number"
              min="0"
              max="60"
              required
              :title="t('loans.graceDaysHelp')"
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
          <input v-model.number="collateralForm.appraisedValue" type="number" min="1" required />
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
                {{ t('loans.removeCollateralFromQueue') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <div class="form-actions">
        <button class="btn" type="submit">
          <FilePlus2 :size="16" />
          {{ t('loans.createLoan') }}
        </button>
      </div>
    </form>

    <div class="card mt-16">
      <div class="table-toolbar">
        <input v-model="search" class="table-search" type="text" :placeholder="t('loans.searchPlaceholder')" />
        <select v-model="statusFilter" class="table-select">
          <option value="all">{{ t('loans.allStatuses') }}</option>
          <option value="active">{{ t('common.active') }}</option>
          <option value="overdue">{{ t('common.overdue') }}</option>
          <option value="closed">{{ t('common.closed') }}</option>
        </select>
        <span class="table-count">{{ t('loans.totalLoans', { count: filteredLoans.length }) }}</span>
      </div>
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
            <th>{{ t('common.collateral') }}</th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleLoanSort('status')">
                {{ t('common.status') }}
                <span v-if="getLoanSortBadge('status')" class="sort-indicator">{{ getLoanSortBadge('status') }}</span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="loan in filteredLoans" :key="loan.id" class="clickable-row" @click="openLoanDetail(loan.id)">
            <td>{{ loan.id }}</td>
            <td>{{ getCustomerLabel(loan.customerId) }}</td>
            <td>{{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
            <td>{{ formatDateDMY(loan.disbursementDate) }}</td>
            <td>{{ formatCurrency(loan.principalAmount) }}</td>
            <td>{{ formatCurrency(loan.outstandingPrincipal) }}</td>
            <td>{{ loan.monthlyInterestRate }}%</td>
            <td>{{ getLoanCollateralLabel(loan.id, loan.loanType) }}</td>
            <td>{{ t(`common.${loan.status}`) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="message" class="notice mt-16">{{ message }}</p>

    <div v-if="showLoanDetailModal && selectedLoan" class="modal-backdrop" @click.self="closeLoanDetail">
      <div class="modal-panel card modal-panel-lg">
        <div class="modal-header">
          <h3>{{ t('loans.loanDetail') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closeLoanDetail">{{ t('common.close') }}</button>
        </div>

        <p class="muted mt-16">{{ t('loans.selectedLoan', { id: selectedLoan.id }) }}</p>

        <div class="grid grid-4 mt-16">
          <div class="card stat-card stat-accent-indigo">
            <p class="stat-label">{{ t('common.customer') }}</p>
            <p class="stat-value">{{ getCustomerLabel(selectedLoan.customerId) }}</p>
          </div>
          <div class="card stat-card stat-accent-blue">
            <p class="stat-label">{{ t('common.type') }}</p>
            <p class="stat-value">{{ selectedLoan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</p>
          </div>
          <div class="card stat-card stat-accent-green">
            <p class="stat-label">{{ t('common.principal') }}</p>
            <p class="stat-value">{{ formatCurrency(selectedLoan.principalAmount) }}</p>
          </div>
          <div class="card stat-card stat-accent-amber">
            <p class="stat-label">{{ t('loans.outstanding') }}</p>
            <p class="stat-value">{{ formatCurrency(selectedLoan.outstandingPrincipal) }}</p>
          </div>
        </div>

        <div class="stats-inline mt-16">
          <span class="pill">{{ t('common.status') }}: {{ t(`common.${selectedLoan.status}`) }}</span>
          <span class="pill" :title="t('loans.graceDaysHelp')">{{ t('loans.dueDay') }}: {{ selectedLoan.dueDay }}</span>
          <span class="pill">{{ t('loans.rate') }}: {{ selectedLoan.monthlyInterestRate }}%</span>
          <span class="pill">{{ t('loans.latePenaltyRate') }}: {{ selectedLoan.latePenaltyRate }}%</span>
          <span class="pill">{{ t('common.date') }}: {{ formatDateDMY(selectedLoan.disbursementDate) }}</span>
        </div>

        <div class="mt-16">
          <h3>{{ t('loans.loanPayments') }}</h3>
          <p class="muted" v-if="!selectedLoanPayments.length">{{ t('loans.noLoanPayments') }}</p>
          <table v-else>
            <thead>
              <tr>
                <th>{{ t('common.id') }}</th>
                <th>{{ t('common.date') }}</th>
                <th>{{ t('common.total') }}</th>
                <th>{{ t('payments.penalty') }}</th>
                <th>{{ t('common.interest') }}</th>
                <th>{{ t('common.fees') }}</th>
                <th>{{ t('common.principal') }}</th>
                <th>{{ t('common.method') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="payment in selectedLoanPayments" :key="payment.id">
                <td>#{{ payment.id }}</td>
                <td>{{ formatDateDMY(payment.paymentDate) }}</td>
                <td>{{ formatCurrency(payment.totalAmount) }}</td>
                <td>{{ formatCurrency(payment.allocatedToPenalty) }}</td>
                <td>{{ formatCurrency(payment.allocatedToInterest) }}</td>
                <td>{{ formatCurrency(payment.allocatedToFees) }}</td>
                <td>{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
                <td>
                  {{
                    payment.paymentMethod === 'cash'
                      ? t('common.cash')
                      : payment.paymentMethod === 'bank-transfer'
                        ? t('common.bankTransfer')
                        : t('common.other')
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-16">
          <h3>{{ t('loans.loanCollateral') }}</h3>
          <p class="muted" v-if="!selectedLoanCollateral.length">{{ t('loans.noLoanCollateral') }}</p>
          <table v-else>
            <thead>
              <tr>
                <th>{{ t('common.id') }}</th>
                <th>{{ t('common.description') }}</th>
                <th>{{ t('collateral.appraisedValue') }}</th>
                <th>{{ t('collateral.custodyCode') }}</th>
                <th>{{ t('collateral.location') }}</th>
                <th>{{ t('common.status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in selectedLoanCollateral" :key="item.id">
                <td>#{{ item.id }}</td>
                <td>{{ item.description }}</td>
                <td>{{ formatCurrency(item.appraisedValue) }}</td>
                <td>{{ item.custodyCode }}</td>
                <td>{{ item.storageLocation }}</td>
                <td>{{ item.status === 'in-custody' ? t('common.inCustody') : t(`common.${item.status}`) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { FilePlus2, HandCoins } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'
import { formatDateDMY, getGlobalDateFormat, toIsoDate } from '../utils/date'

type SortDirection = 'asc' | 'desc'
type LoanSortKey = 'date' | 'id' | 'customer' | 'principal' | 'outstanding' | 'rate' | 'status'

interface SortCriterion<T extends string> {
  key: T
  direction: SortDirection
}

interface CollateralQueueItem {
  description: string
  appraisedValue: number
  storageLocation: string
}

const { state, createLoan, createCollateral, getCustomerName, ensureInitialized } = useMockPlatformStore()
const { t, locale } = useI18n()
const search = ref('')
const message = ref('')
const applyLatePenalty = ref(true)
const applyCollateralAssociation = ref(false)
const statusFilter = ref<'all' | 'active' | 'overdue' | 'closed'>('all')
const loanSortPriority = ref<SortCriterion<LoanSortKey>[]>([{ key: 'date', direction: 'desc' }])
const selectedLoanId = ref<number | null>(null)
const showLoanDetailModal = ref(false)
const collateralQueue = ref<CollateralQueueItem[]>([])
const currencyCode = computed(() => state.globalSettings?.currencyCode ?? 'COP')
const datePlaceholder = computed(() => getGlobalDateFormat())
const todayIso = new Date().toISOString().slice(0, 10)
const sortedCustomers = computed(() => [...state.customers].sort((a, b) => a.fullName.localeCompare(b.fullName)))

onMounted(async () => {
  await ensureInitialized()
  if (sortedCustomers.value.length) {
    form.customerId = sortedCustomers.value[0].id
  }
  if (state.globalSettings) {
    form.latePenaltyRate = state.globalSettings.defaultLatePenaltyRate
  }
})

const form = reactive({
  customerId: 0,
  loanType: 'pawn' as 'pawn' | 'personal',
  principalAmount: 1000,
  monthlyInterestRate: 8,
  latePenaltyRate: 0,
  dueDay: 5,
  disbursementDate: formatDateDMY(todayIso)
})

const handleCreateLoan = async () => {
  const disbursementDate = toIsoDate(form.disbursementDate)
  if (!disbursementDate) {
    message.value = t('messages.invalidDateFormat')
    return
  }

  const payload = {
    ...form,
    disbursementDate,
    latePenaltyRate: applyLatePenalty.value ? form.latePenaltyRate : 0,
    dueDay: applyLatePenalty.value ? form.dueDay : 0
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
  message.value = ''
  collateralQueue.value = []
  collateralForm.description = ''
  collateralForm.appraisedValue = 1000
  collateralForm.storageLocation = 'Vault A-01'
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

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    style: 'currency',
    currency: currencyCode.value
  }).format(
    amount
  )

const getCustomerLabel = (customerId: number) => {
  const value = getCustomerName(customerId)
  return value === '__UNKNOWN_CUSTOMER__' ? t('messages.unknownCustomer') : value
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

const openLoanDetail = (loanId: number) => {
  selectedLoanId.value = loanId
  showLoanDetailModal.value = true
}

const closeLoanDetail = () => {
  showLoanDetailModal.value = false
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

const collateralCountByLoanId = computed(() => {
  const counts = new Map<number, number>()
  for (const item of state.collateralItems) {
    if (item.status !== 'in-custody') {
      continue
    }
    counts.set(item.loanId, (counts.get(item.loanId) ?? 0) + 1)
  }
  return counts
})

const getLoanCollateralLabel = (loanId: number, loanType: 'pawn' | 'personal') => {
  if (loanType !== 'pawn') {
    return '—'
  }

  const count = collateralCountByLoanId.value.get(loanId) ?? 0
  if (!count) {
    return t('loans.noCollateralLinked')
  }

  return t('loans.collateralLinkedCount', { count })
}

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
</script>
