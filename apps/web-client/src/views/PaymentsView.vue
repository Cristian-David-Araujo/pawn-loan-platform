<template>
  <section>
    <h2>{{ t('payments.title') }}</h2>
    <p class="muted">{{ t('payments.subtitle') }}</p>

    <div class="card mt-16 form-inline">
      <label>
        {{ t('common.customer') }}
        <select v-model.number="selectedCustomerId" @change="loadCustomerPaymentData" required>
          <option v-for="customer in state.customers" :key="customer.id" :value="customer.id">
            {{ customer.fullName }} (#{{ customer.id }})
          </option>
        </select>
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
          {{ t('payments.operationType') }}
          <select v-model="interestMode">
            <option value="selected">{{ t('payments.paySelected') }}</option>
            <option value="all">{{ t('payments.payAllPending') }}</option>
          </select>
        </label>
        <label v-if="interestMode === 'all'">
          {{ t('payments.totalAmount') }}
          <input v-model.number="interestAllAmount" type="number" min="0.01" step="0.01" />
        </label>
      </div>

      <div class="table-toolbar mt-16">
        <span class="table-count">{{ t('payments.totalPending', { amount: formatCurrency(totalPendingOutstanding) }) }}</span>
      </div>

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
            <th>{{ t('payments.partialPayAmount') }}</th>
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
                :disabled="interestMode === 'all'"
              />
            </td>
            <td>#{{ item.loan_id }}</td>
            <td>{{ item.loan_type === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
            <td>{{ item.billing_period }}</td>
            <td>{{ item.due_date }}</td>
            <td>{{ formatCurrency(item.original_interest_amount) }}</td>
            <td>{{ formatCurrency(item.remaining_pending_amount) }}</td>
            <td>{{ formatCurrency(item.penalty_amount) }}</td>
            <td>{{ formatCurrency(item.current_outstanding_balance) }}</td>
            <td>
              <input
                v-model.number="partialAmounts[item.interest_charge_id]"
                type="number"
                min="0"
                step="0.01"
                :max="item.current_outstanding_balance"
                :disabled="interestMode === 'all' || !selectedChargeIds.has(item.interest_charge_id)"
              />
            </td>
            <td>
              <span class="pill" :class="item.overdue ? 'pill-overdue' : 'pill-current'">
                {{ item.overdue ? t('common.overdue') : t('payments.currentOrUpcoming') }}
              </span>
            </td>
          </tr>
          <tr v-if="!flatPendingItems.length">
            <td colspan="11">{{ t('payments.noPendingInterest') }}</td>
          </tr>
        </tbody>
      </table>

      <div class="card mt-16">
        <p>{{ t('payments.selectedItems', { count: selectedChargeIds.size }) }}</p>
        <p>{{ t('payments.amountEntered', { amount: formatCurrency(interestAmountToPay) }) }}</p>
        <p>{{ t('payments.remainingAfterPayment', { amount: formatCurrency(remainingAfterInterestPayment) }) }}</p>
        <label class="mt-16">
          {{ t('payments.notes') }}
          <input v-model="interestNotes" />
        </label>
        <button class="btn mt-16" type="button" @click="submitInterestPayment" :disabled="interestAmountToPay <= 0 || processing">
          {{ t('payments.registerInterestPayment') }}
        </button>
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
          <strong>{{ selectedPrincipalLoan.next_due_date }}</strong>
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

        <button class="btn" type="button" @click="submitPrincipalPayment" :disabled="!selectedPrincipalLoan || principalAmount <= 0 || processing">
          {{ t('payments.registerPrincipalPayment') }}
        </button>
      </div>
    </div>

    <div class="card mt-16" v-if="selectedCustomerId">
      <h3>{{ t('payments.historyTitle') }}</h3>
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
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in paymentHistory" :key="event.id">
            <td>{{ event.payment_date }}</td>
            <td>{{ event.payment_type }}</td>
            <td>#{{ event.loan_id }}</td>
            <td>{{ event.billing_period || '-' }}</td>
            <td>{{ formatCurrency(event.total_entered_amount) }}</td>
            <td>{{ formatCurrency(event.allocated_to_interest) }}</td>
            <td>{{ formatCurrency(event.allocated_to_penalty) }}</td>
            <td>{{ formatCurrency(event.allocated_to_principal) }}</td>
            <td>{{ event.payment_method }}</td>
          </tr>
          <tr v-if="!paymentHistory.length">
            <td colspan="9">{{ t('payments.noHistory') }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="message" class="notice mt-16">{{ message }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiClient } from '../services/api'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

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

const { state, ensureInitialized, refreshAll } = useMockPlatformStore()
const { t, locale } = useI18n()

const activeTab = ref<'interest' | 'principal'>('interest')
const selectedCustomerId = ref<number | null>(null)
const selectedPrincipalLoanId = ref<number | null>(null)
const principalAmount = ref(0)
const principalPaymentMethod = ref<'cash' | 'bank-transfer' | 'other'>('cash')
const allowPrincipalWithUnpaidInterest = ref(false)
const principalNotes = ref('')

const interestMode = ref<'selected' | 'all'>('selected')
const interestPaymentMethod = ref<'cash' | 'bank-transfer' | 'other'>('cash')
const interestNotes = ref('')
const interestAllAmount = ref(0)
const selectedChargeIds = ref(new Set<number>())
const partialAmounts = ref<Record<number, number>>({})

const pendingInterest = ref<InterestPendingResponse | null>(null)
const principalContext = ref<PrincipalContextResponse | null>(null)
const paymentHistory = ref<PaymentEvent[]>([])
const processing = ref(false)
const message = ref('')

const selectedCustomer = computed(() =>
  selectedCustomerId.value === null ? null : state.customers.find((item) => item.id === selectedCustomerId.value) ?? null
)

const flatPendingItems = computed(() => pendingInterest.value?.groups.flatMap((group) => group.items) ?? [])

const principalContextItems = computed(() => principalContext.value?.items ?? [])

const selectedPrincipalLoan = computed(
  () => principalContextItems.value.find((item) => item.loan_id === selectedPrincipalLoanId.value) ?? null
)

const totalPendingOutstanding = computed(() =>
  flatPendingItems.value.reduce((sum, item) => sum + item.current_outstanding_balance, 0)
)

const interestAmountToPay = computed(() => {
  if (interestMode.value === 'all') {
    return Math.max(0, interestAllAmount.value)
  }

  return [...selectedChargeIds.value].reduce((sum, chargeId) => {
    const value = partialAmounts.value[chargeId] ?? 0
    return sum + Math.max(0, value)
  }, 0)
})

const remainingAfterInterestPayment = computed(() => Math.max(0, totalPendingOutstanding.value - interestAmountToPay.value))

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )

const initializePartialAmounts = () => {
  const next: Record<number, number> = {}
  for (const item of flatPendingItems.value) {
    next[item.interest_charge_id] = item.current_outstanding_balance
  }
  partialAmounts.value = next
  interestAllAmount.value = totalPendingOutstanding.value
}

const toggleCharge = (chargeId: number) => {
  const next = new Set(selectedChargeIds.value)
  if (next.has(chargeId)) {
    next.delete(chargeId)
  } else {
    next.add(chargeId)
  }
  selectedChargeIds.value = next
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
  selectedChargeIds.value = new Set(flatPendingItems.value.map((item) => item.interest_charge_id))
  initializePartialAmounts()
  selectedPrincipalLoanId.value = principal.items[0]?.loan_id ?? null
  principalAmount.value = selectedPrincipalLoan.value?.outstanding_principal ?? 0
}

const submitInterestPayment = async () => {
  if (!selectedCustomerId.value || interestAmountToPay.value <= 0 || processing.value) {
    return
  }

  processing.value = true
  try {
    if (interestMode.value === 'all') {
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
    } else {
      const selectedIds = [...selectedChargeIds.value]
      for (const chargeId of selectedIds) {
        const amount = Math.max(0, partialAmounts.value[chargeId] ?? 0)
        if (!amount) {
          continue
        }

        await apiClient.request('/payments/interest', {
          method: 'POST',
          body: JSON.stringify({
            customer_id: selectedCustomerId.value,
            pay_all_pending: false,
            selected_charge_ids: [chargeId],
            total_amount: amount,
            payment_method: interestPaymentMethod.value,
            notes: interestNotes.value
          })
        })
      }
    }

    await refreshAll()
    await loadCustomerPaymentData()
    message.value = t('messages.paymentRegistered')
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
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    processing.value = false
  }
}

onMounted(async () => {
  await ensureInitialized()
  if (state.customers.length) {
    selectedCustomerId.value = state.customers[0].id
    await loadCustomerPaymentData()
  }
})
</script>
