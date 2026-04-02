<template>
  <section>
    <PageHeader :title="t('loans.title')" :subtitle="t('loans.subtitle')">
      <template #icon>
        <HandCoins :size="18" />
      </template>
    </PageHeader>

    <form class="card form mt-16" @submit.prevent="handleCreateLoan">
      <div class="grid grid-3">
        <label>
          {{ t('common.customer') }}
          <select v-model.number="form.customerId" required>
            <option v-for="customer in state.customers" :key="customer.id" :value="customer.id">
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
        <label>
          {{ t('loans.monthlyInterestRate') }}
          <input v-model.number="form.monthlyInterestRate" type="number" min="0" step="0.1" required />
        </label>
        <label>
          {{ t('loans.dueDay') }}
          <input v-model.number="form.dueDay" type="number" min="1" max="28" required />
        </label>
      </div>
      <button class="btn" type="submit">
        <FilePlus2 :size="16" />
        {{ t('loans.createLoan') }}
      </button>
    </form>

    <form class="card form mt-16" @submit.prevent="handleCreateCollateral">
      <div class="grid grid-3">
        <label>
          {{ t('common.loan') }}
          <select v-model.number="collateralForm.loanId" required>
            <option v-for="loan in collateralEligibleLoans" :key="loan.id" :value="loan.id">
              {{ getLoanOptionLabel(loan.id, loan.customerId) }}
            </option>
          </select>
        </label>
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
      <button class="btn" type="submit">
        <FilePlus2 :size="16" />
        {{ t('collateral.registerCollateralItem') }}
      </button>
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
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.customer') }}</th>
            <th>{{ t('common.type') }}</th>
            <th>{{ t('common.principal') }}</th>
            <th>{{ t('loans.outstanding') }}</th>
            <th>{{ t('loans.rate') }}</th>
            <th>{{ t('common.collateral') }}</th>
            <th>{{ t('common.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="loan in filteredLoans" :key="loan.id">
            <td>{{ loan.id }}</td>
            <td>{{ getCustomerLabel(loan.customerId) }}</td>
            <td>{{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
            <td>{{ formatCurrency(loan.principalAmount) }}</td>
            <td>{{ formatCurrency(loan.outstandingPrincipal) }}</td>
            <td>{{ loan.monthlyInterestRate }}%</td>
            <td>{{ getLoanCollateralLabel(loan.id, loan.loanType) }}</td>
            <td>{{ t(`common.${loan.status}`) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { FilePlus2, HandCoins } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, createLoan, createCollateral, getCustomerName, ensureInitialized } = useMockPlatformStore()
const { t, locale } = useI18n()
const search = ref('')
const statusFilter = ref<'all' | 'active' | 'overdue' | 'closed'>('all')

const collateralEligibleLoans = computed(() =>
  state.loans.filter((loan) => loan.loanType === 'pawn' && loan.status !== 'closed')
)

onMounted(async () => {
  await ensureInitialized()
  if (state.customers.length) {
    form.customerId = state.customers[0].id
  }
  if (collateralEligibleLoans.value.length) {
    collateralForm.loanId = collateralEligibleLoans.value[0].id
  }
})

const form = reactive({
  customerId: state.customers[0]?.id ?? 1,
  loanType: 'pawn' as 'pawn' | 'personal',
  principalAmount: 1000,
  monthlyInterestRate: 8,
  dueDay: 5
})

const handleCreateLoan = async () => {
  await createLoan({ ...form })

  if (!collateralForm.loanId && collateralEligibleLoans.value.length) {
    collateralForm.loanId = collateralEligibleLoans.value[0].id
  }
}

const collateralForm = reactive({
  loanId: 0,
  description: '',
  appraisedValue: 1000,
  storageLocation: 'Vault A-01'
})

const handleCreateCollateral = async () => {
  if (!collateralEligibleLoans.value.length) {
    return
  }

  if (!collateralForm.loanId) {
    collateralForm.loanId = collateralEligibleLoans.value[0].id
  }

  await createCollateral({ ...collateralForm })
  collateralForm.description = ''
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )

const getCustomerLabel = (customerId: number) => {
  const value = getCustomerName(customerId)
  return value === '__UNKNOWN_CUSTOMER__' ? t('messages.unknownCustomer') : value
}

const getLoanOptionLabel = (loanId: number, customerId: number) =>
  t('collateral.loanOption', { id: loanId, customer: getCustomerLabel(customerId) })

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

  return state.loans.filter((loan) => {
    const statusMatches = statusFilter.value === 'all' || loan.status === statusFilter.value
    const customer = getCustomerLabel(loan.customerId).toLowerCase()
    const textMatches = !query || `${loan.id} ${customer}`.includes(query)
    return statusMatches && textMatches
  })
})
</script>
