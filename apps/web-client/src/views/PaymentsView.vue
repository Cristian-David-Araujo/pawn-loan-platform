<template>
  <section>
    <PageHeader :title="t('payments.title')" :subtitle="t('payments.subtitle')">
      <template #icon>
        <ReceiptText :size="18" />
      </template>
    </PageHeader>

    <div class="card mt-16 form-inline">
      <label>
        {{ t('common.customer') }}
        <CustomerAutocomplete v-model="selectedCustomerId" :customers="sortedCustomers" :placeholder="t('common.searchPlaceholder')" />
      </label>
      <span v-if="selectedCustomer" class="pill">{{ selectedCustomer.fullName }}</span>
    </div>

    <div class="tabs mt-16">
      <button class="tab-btn" :class="{ active: activeTab === 'interest' }" @click="activeTab = 'interest'" type="button">
        {{ t('payments.interestTab') }}
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'principal' }" @click="activeTab = 'principal'" type="button">
        {{ t('payments.principalTab') }}
      </button>
    </div>

    <div v-if="activeTab === 'interest'" class="card mt-16">
      <h3>{{ t('payments.pendingInterestTitle') }}</h3>

      <div class="form-inline mt-16">
        <label>
          {{ t('payments.paymentMethod') }}
          <select v-model="interestPaymentMethod">
            <option value="cash">{{ t('common.cash') }}</option>
            <option value="bank-transfer">{{ t('common.bankTransfer') }}</option>
            <option value="other">{{ t('common.other') }}</option>
          </select>
        </label>
        <label>
          {{ t('payments.totalAmount') }}
          <input v-model.number="interestEnteredAmount" type="number" min="0.01" step="0.01" @input="interestAmountTouched = true" />
        </label>
        <button class="btn btn-secondary" type="button" @click="useSuggestedAmount">
          <Sparkles :size="16" />
          {{ t('payments.useSuggested') }}
        </button>
      </div>

      <div class="table-toolbar mt-16">
        <span class="table-count">{{ t('payments.totalPending', { amount: formatCurrency(totalPendingOutstanding) }) }}</span>
        <span class="pill">{{ t('payments.suggestedForSelected', { amount: formatCurrency(suggestedSelectedAmount) }) }}</span>
      </div>

      <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{{ t('common.actions') }}</th>
            <th>{{ t('common.loan') }}</th>
            <th>{{ t('common.type') }}</th>
            <th>{{ t('payments.period') }}</th>
            <th>{{ t('payments.dueDate') }}</th>
            <th>{{ t('payments.originalInterest') }}</th>
            <th>{{ t('payments.pendingInterest') }}</th>
            <th>{{ t('payments.penalty') }}</th>
            <th>{{ t('payments.outstandingPeriod') }}</th>
            <th>{{ t('common.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in flatPendingItems" :key="item.interest_charge_id">
            <td>
              <input
                type="checkbox"
                :checked="selectedChargeIds.has(item.interest_charge_id)"
                @change="toggleCharge(item.interest_charge_id)"
              />
            </td>
            <td>#{{ item.loan_id }}</td>
            <td>{{ item.loan_type === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
            <td>{{ item.billing_period }}</td>
            <td>{{ formatDateDMY(item.due_date) }}</td>
            <td>{{ formatCurrency(item.original_interest_amount) }}</td>
            <td>{{ formatCurrency(item.remaining_pending_amount) }}</td>
            <td>{{ formatCurrency(item.penalty_amount) }}</td>
            <td>{{ formatCurrency(item.current_outstanding_balance) }}</td>
            <td>
              <span class="pill" :class="getPendingStatusClass(item)">
                {{ t(getPendingStatusKey(item)) }}
              </span>
            </td>
          </tr>
          <tr v-if="!flatPendingItems.length">
            <td colspan="10">{{ t('payments.noPendingInterest') }}</td>
          </tr>
        </tbody>
      </table>
      </div>

      <div class="card mt-16">
        <p>{{ t('payments.selectedItems', { count: selectedChargeIds.size }) }}</p>
        <p>{{ t('payments.amountEntered', { amount: formatCurrency(interestAmountToPay) }) }}</p>
        <p>{{ t('payments.remainingAfterPayment', { amount: formatCurrency(remainingAfterInterestPayment) }) }}</p>
        <p>{{ t('payments.partialDetected', { amount: formatCurrency(partialAmount) }) }}</p>
        <p>{{ t('payments.advanceDetected', { amount: formatCurrency(advanceAmount) }) }}</p>
        <label class="mt-16">
          {{ t('payments.notes') }}
          <input v-model="interestNotes" />
        </label>
        <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;" class="mt-16">
          <label class="checkbox-row" style="margin-bottom: 0;">
            <input v-model="printReceiptOnSave" type="checkbox" />
            {{ t('common.printReceiptOnSave') }}
          </label>
          <button class="btn" type="button" @click="submitInterestPayment" :disabled="interestAmountToPay <= 0 || processing">
            <CircleDollarSign :size="16" />
            {{ t('payments.registerInterestPayment') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'principal'" class="card mt-16">
      <h3>{{ t('payments.principalTitle') }}</h3>

      <label class="mt-16">
        {{ t('common.loan') }}
        <select v-model.number="selectedPrincipalLoanId">
          <option v-for="item in principalContextItems" :key="item.loan_id" :value="item.loan_id">
            #{{ item.loan_id }} - {{ item.loan_type }}
          </option>
        </select>
      </label>

      <div v-if="selectedPrincipalLoan" class="grid grid-3 mt-16">
        <div class="card">
          <p>{{ t('payments.originalPrincipal') }}</p>
          <strong>{{ formatCurrency(selectedPrincipalLoan.original_principal) }}</strong>
        </div>
        <div class="card">
          <p>{{ t('payments.outstandingPrincipal') }}</p>
          <strong>{{ formatCurrency(selectedPrincipalLoan.outstanding_principal) }}</strong>
        </div>
        <div class="card">
          <p>{{ t('payments.accruedUnpaidInterest') }}</p>
          <strong>{{ formatCurrency(selectedPrincipalLoan.accrued_unpaid_interest) }}</strong>
        </div>
        <div class="card">
          <p>{{ t('payments.penalty') }}</p>
          <strong>{{ formatCurrency(selectedPrincipalLoan.penalties) }}</strong>
        </div>
        <div class="card">
          <p>{{ t('payments.totalPayoff') }}</p>
          <strong>{{ formatCurrency(selectedPrincipalLoan.total_payoff_amount) }}</strong>
        </div>
        <div class="card">
          <p>{{ t('payments.nextDueDate') }}</p>
          <strong>{{ formatDateDMY(selectedPrincipalLoan.next_due_date) }}</strong>
        </div>
      </div>

      <div v-if="selectedPrincipalLoan" class="form mt-16">
        <label>
          {{ t('payments.totalAmount') }}
          <input v-model.number="principalAmount" type="number" min="0.01" step="0.01" />
        </label>
        <label>
          {{ t('payments.paymentMethod') }}
          <select v-model="principalPaymentMethod">
            <option value="cash">{{ t('common.cash') }}</option>
            <option value="bank-transfer">{{ t('common.bankTransfer') }}</option>
            <option value="other">{{ t('common.other') }}</option>
          </select>
        </label>
        <label class="checkbox-row">
          <input v-model="allowPrincipalWithUnpaidInterest" type="checkbox" />
          {{ t('payments.allowWithUnpaidInterest') }}
        </label>
        <label>
          {{ t('payments.notes') }}
          <input v-model="principalNotes" />
        </label>

        <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;" class="mt-16">
          <label class="checkbox-row" style="margin-bottom: 0;">
            <input v-model="printReceiptOnSave" type="checkbox" />
            {{ t('common.printReceiptOnSave') }}
          </label>
          <button class="btn" type="button" @click="submitPrincipalPayment" :disabled="!selectedPrincipalLoan || principalAmount <= 0 || processing">
            <WalletCards :size="16" />
            {{ t('payments.registerPrincipalPayment') }}
          </button>
        </div>
      </div>
    </div>

    <div class="card mt-16" v-if="selectedCustomerId">
      <h3>{{ t('payments.historyTitle') }}</h3>
      <div class="filter-grid mt-16">
        <label>
          {{ t('payments.filterFromDate') }}
          <DateInputField v-model="historyFromDate" :label="t('payments.filterFromDate')" :placeholder="t('settings.dateFormat')" />
        </label>
        <label>
          {{ t('payments.filterToDate') }}
          <DateInputField v-model="historyToDate" :label="t('payments.filterToDate')" :placeholder="t('settings.dateFormat')" />
        </label>
        <label>
          {{ t('payments.filterLoan') }}
          <select v-model="historyLoanFilter">
            <option value="all">{{ t('payments.allLoans') }}</option>
            <option v-for="loanId in paymentHistoryLoanOptions" :key="loanId" :value="loanId">#{{ loanId }}</option>
          </select>
        </label>
        <label>
          {{ t('payments.filterType') }}
          <select v-model="historyTypeFilter">
            <option value="all">{{ t('payments.allTypes') }}</option>
            <option value="interest">{{ t('payments.interestTab') }}</option>
            <option value="principal">{{ t('payments.principalTab') }}</option>
            <option value="advance">{{ t('customers.advancePayment') }}</option>
          </select>
        </label>
      </div>
      <div class="form-inline mt-16">
        <button class="btn btn-secondary" type="button" @click="resetHistoryFilters">
          <FilterX :size="16" />
          {{ t('payments.resetHistoryFilters') }}
        </button>
        <button class="btn btn-secondary" type="button" @click="printHistory">
          <Printer :size="16" />
          {{ t('common.printHistory') }}
        </button>
      </div>
      <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{{ t('common.date') }}</th>
            <th>{{ t('payments.paymentType') }}</th>
            <th>{{ t('common.loan') }}</th>
            <th>{{ t('payments.period') }}</th>
            <th>{{ t('common.total') }}</th>
            <th>{{ t('common.interest') }}</th>
            <th>{{ t('payments.penalty') }}</th>
            <th>{{ t('common.principal') }}</th>
            <th>{{ t('common.method') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in filteredPaymentHistory" :key="event.id">
            <td>{{ formatDateDMY(event.payment_date) }}</td>
            <td>{{ getPaymentTypeLabel(event.payment_type) }}</td>
            <td>#{{ event.loan_id }}</td>
            <td>{{ event.billing_period || '-' }}</td>
            <td>{{ formatCurrency(event.total_entered_amount) }}</td>
            <td>{{ formatCurrency(event.allocated_to_interest) }}</td>
            <td>{{ formatCurrency(event.allocated_to_penalty) }}</td>
            <td>{{ formatCurrency(event.allocated_to_principal) }}</td>
            <td>{{ getPaymentMethodLabel(event.payment_method) }}</td>
            <td>
              <a :href="'/print/invoice/payment/' + event.id" target="_blank" class="btn btn-secondary btn-icon" :title="t('common.printReceipt')" style="text-decoration: none;">
                <Printer :size="16" />
              </a>
            </td>
          </tr>
          <tr v-if="!filteredPaymentHistory.length">
            <td colspan="10">{{ t('payments.noHistory') }}</td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <div class="card mt-16" v-if="selectedCustomerId">
      <h3>{{ t('payments.registeredPaymentsTitle') }}</h3>
      <p class="muted" v-if="!selectedCustomerPayments.length">{{ t('payments.noRegisteredPayments') }}</p>
      <table v-else>
        <thead>
          <tr>
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.loan') }}</th>
            <th>{{ t('common.date') }}</th>
            <th>{{ t('common.total') }}</th>
            <th>{{ t('common.interest') }}</th>
            <th>{{ t('payments.penalty') }}</th>
            <th>{{ t('common.principal') }}</th>
            <th>{{ t('common.method') }}</th>
            <th>{{ t('payments.notes') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="payment in selectedCustomerPayments" :key="payment.id">
            <td>#{{ payment.id }}</td>
            <td>#{{ payment.loanId }}</td>
            <td>{{ formatDateDMY(payment.paymentDate) }}</td>
            <td>{{ formatCurrency(payment.totalAmount) }}</td>
            <td>{{ formatCurrency(payment.allocatedToInterest) }}</td>
            <td>{{ formatCurrency(payment.allocatedToPenalty) }}</td>
            <td>{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
            <td>{{ getPaymentMethodLabel(payment.paymentMethod) }}</td>
            <td class="muted">{{ payment.notes || '-' }}</td>
            <td>{{ payment.isReversed ? t('payments.reversed') : t('common.active') }}</td>
            <td>
              <div class="form-inline">
                <a :href="'/print/invoice/payment/' + payment.id" target="_blank" class="btn btn-secondary btn-icon" :title="t('common.printReceipt')" style="text-decoration: none;">
                  <Printer :size="16" />
                </a>
                <button class="btn btn-secondary btn-icon" type="button" :title="t('payments.editPayment')" :disabled="payment.isReversed || processing" @click="openPaymentEditModal(payment)">
                  <Pencil :size="16" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showPaymentEditModal" class="modal-backdrop" @click.self="closePaymentEditModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ t('payments.editPayment') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closePaymentEditModal">{{ t('common.close') }}</button>
        </div>

        <form class="form mt-16" @submit.prevent="handleUpdatePayment">
          <div class="grid grid-2">
            <label>
              {{ t('common.date') }}
              <DateInputField
                v-model="paymentEditForm.paymentDate"
                :label="t('common.date')"
                :placeholder="t('settings.dateFormat')"
                :required="true"
              />
            </label>
            <label>
              {{ t('payments.paymentMethod') }}
              <select v-model="paymentEditForm.paymentMethod">
                <option value="cash">{{ t('common.cash') }}</option>
                <option value="bank-transfer">{{ t('common.bankTransfer') }}</option>
                <option value="other">{{ t('common.other') }}</option>
              </select>
            </label>
            <label>
              {{ t('common.total') }}
              <input v-model.number="paymentEditForm.totalAmount" type="number" min="0.01" step="0.01" required />
            </label>
            <label>
              {{ t('common.interest') }}
              <input v-model.number="paymentEditForm.allocatedToInterest" type="number" min="0" step="0.01" required />
            </label>
            <label>
              {{ t('payments.penalty') }}
              <input v-model.number="paymentEditForm.allocatedToPenalty" type="number" min="0" step="0.01" required />
            </label>
            <label>
              {{ t('common.fees') }}
              <input v-model.number="paymentEditForm.allocatedToFees" type="number" min="0" step="0.01" required />
            </label>
            <label>
              {{ t('common.principal') }}
              <input v-model.number="paymentEditForm.allocatedToPrincipal" type="number" min="0" step="0.01" required />
            </label>
          </div>
          <label class="mt-8">
            {{ t('payments.notes') }}
            <textarea v-model="paymentEditForm.notes" rows="2" :placeholder="t('payments.notesPlaceholder')" />
          </label>
          <button class="btn" type="submit" :disabled="processing">
            <Save :size="16" />
            {{ t('customers.saveChanges') }}
          </button>
        </form>
      </div>
    </div>

    <p v-if="message" class="notice mt-16">{{ message }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { CircleDollarSign, FilterX, Pencil, ReceiptText, Save, Sparkles, WalletCards, Printer } from 'lucide-vue-next'
import CustomerAutocomplete from '../components/CustomerAutocomplete.vue'
import DateInputField from '../components/DateInputField.vue'
import PageHeader from '../components/PageHeader.vue'
import { apiClient } from '../services/api'
import { usePlatformStore } from '../stores/platformStore'
import { formatDateDMY, toIsoDate } from '../utils/date'

interface InterestPendingItem {
  interest_charge_id: number
  loan_id: number
  loan_type: 'pawn' | 'personal'
  disbursement_date: string
  billing_period: string
  due_date: string
  original_interest_amount: number
  remaining_pending_amount: number
  overdue: boolean
  penalty_amount: number
  current_outstanding_balance: number
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

interface PrincipalContextItem {
  loan_id: number
  loan_type: 'pawn' | 'personal'
  disbursement_date: string
  next_due_date: string
  original_principal: number
  outstanding_principal: number
  accrued_unpaid_interest: number
  penalties: number
  total_payoff_amount: number
}

interface PrincipalContextResponse {
  customer_id: number
  items: PrincipalContextItem[]
}

interface PaymentEvent {
  id: number
  payment_type: string
  loan_id: number
  interest_charge_id: number | null
  billing_period: string
  total_entered_amount: number
  allocated_to_interest: number
  allocated_to_penalty: number
  allocated_to_principal: number
  payment_date: string
  operator_user_id: number | null
  payment_method: string
  notes: string
}

const { state, ensureInitialized, refreshAll, updatePayment } = usePlatformStore()
const router = useRouter()
const { t, locale } = useI18n()
const currencyCode = computed(() => state.globalSettings?.currencyCode ?? 'COP')

const activeTab = ref<'interest' | 'principal'>('interest')
const printReceiptOnSave = ref(true)
const selectedCustomerId = ref<number | null>(null)

watch(selectedCustomerId, (newId) => {
  if (newId) {
    loadCustomerPaymentData()
  } else {
    pendingInterest.value = null
    principalContext.value = null
    paymentHistory.value = []
  }
})
const selectedPrincipalLoanId = ref<number | null>(null)
const principalAmount = ref(0)
const principalPaymentMethod = ref<'cash' | 'bank-transfer' | 'other'>('cash')
const allowPrincipalWithUnpaidInterest = ref(false)
const principalNotes = ref('')

const interestPaymentMethod = ref<'cash' | 'bank-transfer' | 'other'>('cash')
const interestNotes = ref('')
const interestEnteredAmount = ref(0)
const interestAmountTouched = ref(false)
const selectedChargeIds = ref(new Set<number>())

const pendingInterest = ref<InterestPendingResponse | null>(null)
const principalContext = ref<PrincipalContextResponse | null>(null)
const paymentHistory = ref<PaymentEvent[]>([])
const historyFromDate = ref('')
const historyToDate = ref('')
const historyLoanFilter = ref('all')
const historyTypeFilter = ref('all')
const processing = ref(false)
const message = ref('')
const showPaymentEditModal = ref(false)
const selectedPaymentEditId = ref<number | null>(null)

const paymentEditForm = ref({
  paymentDate: '',
  totalAmount: 0,
  allocatedToPenalty: 0,
  allocatedToInterest: 0,
  allocatedToFees: 0,
  allocatedToPrincipal: 0,
  paymentMethod: 'cash' as 'cash' | 'bank-transfer' | 'other',
  notes: ''
})

const selectedCustomer = computed(() =>
  selectedCustomerId.value === null ? null : state.customers.find((item) => item.id === selectedCustomerId.value) ?? null
)

const sortedCustomers = computed(() => [...state.customers].sort((a, b) => a.fullName.localeCompare(b.fullName)))

const selectedCustomerLoanIds = computed(() => {
  if (selectedCustomerId.value === null) {
    return new Set<number>()
  }

  return new Set(state.loans.filter((loan) => loan.customerId === selectedCustomerId.value).map((loan) => loan.id))
})

const selectedCustomerPayments = computed(() =>
  state.payments
    .filter((payment) => selectedCustomerLoanIds.value.has(payment.loanId))
    .sort((a, b) => {
      const dateDelta = new Date(b.paymentDate).getTime() - new Date(a.paymentDate).getTime()
      if (dateDelta !== 0) {
        return dateDelta
      }
      return b.id - a.id
    })
)

const flatPendingItems = computed(() =>
  [...(pendingInterest.value?.groups.flatMap((group) => group.items) ?? [])].sort(
    (a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
  )
)

const principalContextItems = computed(() =>
  [...(principalContext.value?.items ?? [])].sort((a, b) => new Date(b.next_due_date).getTime() - new Date(a.next_due_date).getTime())
)

const selectedPrincipalLoan = computed(
  () => principalContextItems.value.find((item) => item.loan_id === selectedPrincipalLoanId.value) ?? null
)

const sortedPaymentHistory = computed(() =>
  [...paymentHistory.value].sort((a, b) => new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime())
)

const paymentHistoryLoanOptions = computed(() => {
  const values = new Set(sortedPaymentHistory.value.map((event) => String(event.loan_id)))
  return [...values].sort((a, b) => Number(a) - Number(b))
})

const normalizeIso = (value: string) => {
  const match = value.match(/^(\d{4}-\d{2}-\d{2})/)
  if (match) {
    return match[1]
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  return parsed.toISOString().slice(0, 10)
}

const filteredPaymentHistory = computed(() => {
  const fromIso = toIsoDate(historyFromDate.value)
  const toIso = toIsoDate(historyToDate.value)

  return sortedPaymentHistory.value.filter((event) => {
    if (historyLoanFilter.value !== 'all' && String(event.loan_id) !== historyLoanFilter.value) {
      return false
    }

    if (historyTypeFilter.value !== 'all' && event.payment_type !== historyTypeFilter.value) {
      return false
    }

    const eventIso = normalizeIso(event.payment_date)
    if (!eventIso) {
      return false
    }

    if (fromIso && eventIso < fromIso) {
      return false
    }

    if (toIso && eventIso > toIso) {
      return false
    }

    return true
  })
})

const totalPendingOutstanding = computed(() =>
  flatPendingItems.value.reduce((sum, item) => sum + item.current_outstanding_balance, 0)
)

const selectedPendingItems = computed(() =>
  flatPendingItems.value.filter((item) => selectedChargeIds.value.has(item.interest_charge_id))
)

const suggestedSelectedAmount = computed(() =>
  selectedPendingItems.value.reduce((sum, item) => sum + item.current_outstanding_balance, 0)
)

const interestAmountToPay = computed(() => Math.max(0, interestEnteredAmount.value || 0))

const remainingAfterInterestPayment = computed(() => Math.max(0, totalPendingOutstanding.value - interestAmountToPay.value))
const partialAmount = computed(() => Math.max(0, suggestedSelectedAmount.value - interestAmountToPay.value))
const advanceAmount = computed(() => Math.max(0, interestAmountToPay.value - suggestedSelectedAmount.value))

const getPendingStatusKey = (item: InterestPendingItem) => {
  if (item.overdue) {
    return 'common.overdue'
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const dueDate = new Date(item.due_date)
  dueDate.setHours(0, 0, 0, 0)

  return dueDate.getTime() === today.getTime() ? 'payments.current' : 'payments.upcoming'
}

const getPendingStatusClass = (item: InterestPendingItem) => {
  if (item.overdue) {
    return 'pill-overdue'
  }

  return getPendingStatusKey(item) === 'payments.current' ? 'pill-current' : 'pill-upcoming'
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    style: 'currency',
    currency: currencyCode.value
  }).format(
    amount
  )

const getPaymentTypeLabel = (paymentType: string) => {
  if (paymentType === 'partial_principal_payment') return t('payments.typePartialPrincipal')
  if (paymentType === 'interest_payment' || paymentType === 'interest') return t('payments.typeInterest')
  if (paymentType === 'penalty_payment') return t('payments.typePenalty')
  if (paymentType === 'full_payoff') return t('payments.typeFullPayoff')
  if (paymentType === 'advance_payment' || paymentType === 'advance') return t('payments.typeAdvance')
  if (paymentType === 'interest_advance_payment') return t('payments.typeInterestAdvance')
  if (paymentType === 'mixed_payment') return t('payments.typeMixed')
  if (paymentType === 'principal') return t('payments.principalTab')
  return paymentType
}

const getPaymentMethodLabel = (method: string) => {
  const m = method.toLowerCase()
  if (m === 'cash') {
    return t('common.cash')
  }
  if (m === 'bank-transfer' || m === 'bank_transfer') {
    return t('common.bankTransfer')
  }
  return t('common.other')
}

const resetHistoryFilters = () => {
  historyFromDate.value = ''
  historyToDate.value = ''
  historyLoanFilter.value = 'all'
  historyTypeFilter.value = 'all'
}

const printHistory = () => {
  window.print()
}

const openPaymentEditModal = (payment: {
  id: number
  paymentDate: string
  totalAmount: number
  allocatedToPenalty: number
  allocatedToInterest: number
  allocatedToFees: number
  allocatedToPrincipal: number
  paymentMethod: 'cash' | 'bank-transfer' | 'other'
  notes: string
}) => {
  selectedPaymentEditId.value = payment.id
  paymentEditForm.value = {
    paymentDate: formatDateDMY(payment.paymentDate),
    totalAmount: payment.totalAmount,
    allocatedToPenalty: payment.allocatedToPenalty,
    allocatedToInterest: payment.allocatedToInterest,
    allocatedToFees: payment.allocatedToFees,
    allocatedToPrincipal: payment.allocatedToPrincipal,
    paymentMethod: payment.paymentMethod,
    notes: payment.notes
  }
  showPaymentEditModal.value = true
}

const closePaymentEditModal = () => {
  showPaymentEditModal.value = false
  selectedPaymentEditId.value = null
}

const handleUpdatePayment = async () => {
  if (selectedPaymentEditId.value === null || processing.value) {
    return
  }

  const paymentDate = toIsoDate(paymentEditForm.value.paymentDate)
  if (!paymentDate) {
    message.value = t('messages.invalidDateFormat')
    return
  }

  processing.value = true
  try {
    const result = await updatePayment({
      id: selectedPaymentEditId.value,
      paymentDate,
      totalAmount: paymentEditForm.value.totalAmount,
      allocatedToPenalty: paymentEditForm.value.allocatedToPenalty,
      allocatedToInterest: paymentEditForm.value.allocatedToInterest,
      allocatedToFees: paymentEditForm.value.allocatedToFees,
      allocatedToPrincipal: paymentEditForm.value.allocatedToPrincipal,
      paymentMethod: paymentEditForm.value.paymentMethod,
      notes: paymentEditForm.value.notes
    })

    message.value = t(result.messageKey)
    if (result.ok) {
      closePaymentEditModal()
      await loadCustomerPaymentData()
    }
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    processing.value = false
  }
}

const useSuggestedAmount = () => {
  interestEnteredAmount.value = suggestedSelectedAmount.value
  interestAmountTouched.value = false
}

const toggleCharge = (chargeId: number) => {
  const next = new Set(selectedChargeIds.value)
  if (next.has(chargeId)) {
    next.delete(chargeId)
  } else {
    next.add(chargeId)
  }
  selectedChargeIds.value = next

  if (!interestAmountTouched.value) {
    useSuggestedAmount()
  }
}

const loadCustomerPaymentData = async () => {
  if (selectedCustomerId.value === null) {
    return
  }

  const [pending, principal, history] = await Promise.all([
    apiClient.request<InterestPendingResponse>(`/payments/customers/${selectedCustomerId.value}/interest-pending`),
    apiClient.request<PrincipalContextResponse>(`/payments/customers/${selectedCustomerId.value}/principal-context`),
    apiClient.request<PaymentEvent[]>(`/payments/customers/${selectedCustomerId.value}/history`)
  ])

  pendingInterest.value = pending
  principalContext.value = principal
  paymentHistory.value = history
  resetHistoryFilters()
  selectedChargeIds.value = new Set(flatPendingItems.value.map((item) => item.interest_charge_id))
  useSuggestedAmount()
  selectedPrincipalLoanId.value = principal.items[0]?.loan_id ?? null
  principalAmount.value = selectedPrincipalLoan.value?.outstanding_principal ?? 0
}

const submitInterestPayment = async () => {
  if (!selectedCustomerId.value || interestAmountToPay.value <= 0 || processing.value) {
    return
  }

  const firstConfirmation = window.confirm(t('payments.confirmRegisterInterestStepOne', { amount: formatCurrency(interestAmountToPay.value) }))
  if (!firstConfirmation) {
    return
  }

  const secondConfirmation = window.confirm(t('payments.confirmRegisterInterestStepTwo'))
  if (!secondConfirmation) {
    return
  }

  processing.value = true
  try {
    await apiClient.request('/payments/interest', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: selectedCustomerId.value,
        pay_all_pending: true,
        selected_charge_ids: [],
        total_amount: interestAmountToPay.value,
        payment_method: interestPaymentMethod.value,
        notes: interestNotes.value
      })
    })

    await refreshAll()
    await loadCustomerPaymentData()
    interestNotes.value = ''
    message.value = t('messages.paymentRegistered')

    if (printReceiptOnSave.value && selectedCustomerPayments.value.length > 0) {
      router.push(`/print/invoice/payment/${selectedCustomerPayments.value[0].id}`)
    }
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    processing.value = false
  }
}

const submitPrincipalPayment = async () => {
  if (!selectedPrincipalLoan.value || principalAmount.value <= 0 || processing.value) {
    return
  }

  const firstConfirmation = window.confirm(t('payments.confirmRegisterPrincipalStepOne', { amount: formatCurrency(principalAmount.value) }))
  if (!firstConfirmation) {
    return
  }

  const secondConfirmation = window.confirm(t('payments.confirmRegisterPrincipalStepTwo'))
  if (!secondConfirmation) {
    return
  }

  processing.value = true
  try {
    await apiClient.request('/payments/principal', {
      method: 'POST',
      body: JSON.stringify({
        loan_id: selectedPrincipalLoan.value.loan_id,
        total_amount: principalAmount.value,
        payment_method: principalPaymentMethod.value,
        allow_with_unpaid_interest: allowPrincipalWithUnpaidInterest.value,
        notes: principalNotes.value
      })
    })

    await refreshAll()
    await loadCustomerPaymentData()
    principalAmount.value = selectedPrincipalLoan.value?.outstanding_principal ?? 0
    message.value = t('messages.paymentRegistered')

    if (printReceiptOnSave.value && selectedCustomerPayments.value.length > 0) {
      router.push(`/print/invoice/payment/${selectedCustomerPayments.value[0].id}`)
    }
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    processing.value = false
  }
}

onMounted(async () => {
  await ensureInitialized()
})
</script>
