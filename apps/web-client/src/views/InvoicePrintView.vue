<template>
  <div class="print-container">
    <div class="actions-bar no-print">
      <button class="btn btn-secondary" @click="router.back()">← {{ t('common.returnToSystem') }}</button>
      <button class="btn" @click="printDocument()">{{ t('common.printAgain') }}</button>
    </div>
    <div class="invoice-box" v-if="ready">
      <div class="invoice-header">
        <div class="company-details">
          <h2>{{ globalSettings?.companyName || globalSettings?.appName || t('app.title') }}</h2>
          <p v-if="globalSettings?.companyDocumentNumber">
            {{ globalSettings.companyDocumentType || 'NIT/CC' }}: {{ globalSettings.companyDocumentNumber }}
          </p>
          <p v-if="globalSettings?.companyAddress">
            {{ globalSettings.companyAddress }}
          </p>
          <p v-if="globalSettings?.companyPhone">
            Tel: {{ globalSettings.companyPhone }}
          </p>
          <p v-if="globalSettings?.companyEmail">
            Email: {{ globalSettings.companyEmail }}
          </p>
        </div>
        <div class="invoice-meta">
          <h1 v-if="isPayment">{{ t('payments.receiptTitle', 'Recibo de Pago') }}</h1>
          <h1 v-else-if="isCustomer">{{ t('common.customerStatementTitle') }}</h1>
          <h1 v-else-if="isHistory">{{ t('common.paymentHistoryTitle') }}</h1>
          <h1 v-else>{{ t('loans.invoiceTitle', 'Factura de Préstamo') }}</h1>
          <p v-if="!isCustomer"><strong>Nº:</strong> {{ idString }}</p>
          <p><strong>Fecha:</strong> {{ dateString }}</p>
        </div>
      </div>

      <!-- Customer info -->
      <div class="customer-info" v-if="customer">
        <h3>{{ t('common.customerDataTitle') }}</h3>
        <p><strong>{{ t('common.name') }}:</strong> {{ customer.fullName }}</p>
        <p><strong>{{ customer.documentType }}:</strong> {{ customer.documentNumber }}</p>
        <p><strong>{{ t('common.phone') }}:</strong> {{ customer.phone }}</p>
      </div>

      <!-- Loan context (payment receipts) -->
      <div class="loan-info mt-16" v-if="isPayment && loan">
        <h3>{{ t('common.loanInfo') }}</h3>
        <div class="loan-info-grid">
          <p><strong>{{ t('common.loanNumber') }}:</strong> LN-{{ loan.id.toString().padStart(6, '0') }}</p>
          <p v-if="loan.description"><strong>{{ t('common.description') }}:</strong> {{ loan.description }}</p>
          <p><strong>{{ t('common.type') }}:</strong> {{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</p>
          <p v-if="payment"><strong>{{ t('common.receiptPaymentType') }}:</strong> {{ getPaymentTypeLabel(payment) }}</p>
        </div>
      </div>

      <!-- Payment details table -->
      <div class="invoice-details mt-16">
        <template v-if="isPayment && payment">
          <table class="print-table">
            <thead>
              <tr>
                <th>{{ t('common.concept') }}</th>
                <th class="text-right">{{ t('common.amount') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="payment.allocatedToPrincipal > 0">
                <td>{{ t('common.principalPayment') }}</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
              </tr>
              <tr v-if="payment.allocatedToInterest > 0">
                <td>{{ t('common.interestCharges') }}</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToInterest) }}</td>
              </tr>
              <tr v-if="payment.allocatedToPenalty > 0">
                <td>{{ t('common.penaltyCharge') }}</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToPenalty) }}</td>
              </tr>
              <tr v-if="payment.allocatedToFees > 0">
                <td>{{ t('common.feesCharge') }}</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToFees) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <th>{{ t('common.totalPaid') }}</th>
                <th class="text-right">{{ formatCurrency(payment.totalAmount) }}</th>
              </tr>
            </tfoot>
          </table>
          <div class="payment-notes mt-16">
            <p><strong>{{ t('common.method') }}:</strong> {{ paymentMethodLabel }}</p>
            <p v-if="payment.notes"><strong>{{ t('common.notes') }}:</strong> {{ payment.notes }}</p>
            <p v-if="payment.receiver"><strong>{{ t('common.receivedBy', 'Recibido por') }}:</strong> {{ payment.receiver.full_name || payment.receiver.username }}</p>
          </div>
        </template>

        <template v-else-if="isLoan && loan">
          <table class="print-table">
            <thead>
              <tr>
                <th>{{ t('common.loanDetailsTitle') }}</th>
                <th class="text-right">{{ t('common.value') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{{ t('common.principalAmount') }}</td>
                <td class="text-right">{{ formatCurrency(loan.principalAmount) }}</td>
              </tr>
              <tr>
                <td>{{ t('common.monthlyInterestRate') }}</td>
                <td class="text-right">{{ loan.monthlyInterestRate }}%</td>
              </tr>
              <tr v-if="loan.latePenaltyRate > 0">
                <td>{{ t('common.latePenaltyRate') }}</td>
                <td class="text-right">{{ loan.latePenaltyRate }}%</td>
              </tr>
              <tr>
                <td>{{ t('common.paymentDay') }}</td>
                <td class="text-right">{{ t('common.dayOfEachMonth', { day: loan.dueDay }) }}</td>
              </tr>
            </tbody>
          </table>
          <div class="payment-notes mt-16" v-if="loan.description || loan.created_by">
            <p v-if="loan.description"><strong>{{ t('common.description') }}:</strong> {{ loan.description }}</p>
            <p v-if="loan.created_by"><strong>{{ t('common.createdBy', 'Generado por') }}:</strong> {{ loan.created_by.full_name || loan.created_by.username }}</p>
          </div>
        </template>

        <!-- Customer Statement (Estado de Cuenta) -->
        <template v-else-if="isCustomer && customer">
          <h3>{{ t('common.loansSummaryTitle') }}</h3>
          <table class="print-table compact-table">
            <thead>
              <tr>
                <th>{{ t('common.loan') }}</th>
                <th>{{ t('common.type') }}</th>
                <th>{{ t('common.status') }}</th>
                <th class="text-right">{{ t('loans.rate') }}</th>
                <th class="text-right">{{ t('common.principalBalance') }}</th>
                <th class="text-right">{{ t('common.interest') }}</th>
                <th class="text-right">{{ t('common.penalty') }}</th>
                <th class="text-right">{{ t('common.totalOwed') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="l in customerLoans" :key="l.id">
                <td>{{ loanLabel(l.id) }}</td>
                <td>{{ l.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
                <td>
                  <span class="status-badge" :class="getLoanStatusClass(l)">
                    {{ getLoanStatusLabel(l) }}
                  </span>
                </td>
                <td class="text-right">{{ l.monthlyInterestRate }}%</td>
                <td class="text-right">{{ formatCurrency(l.outstandingPrincipal) }}</td>
                <td class="text-right">{{ formatCurrency(statementFor(l.id)?.accrued_unpaid_interest ?? 0) }}</td>
                <td class="text-right">{{ formatCurrency(statementFor(l.id)?.penalties ?? 0) }}</td>
                <td class="text-right balance-value">
                  {{ formatCurrency(statementFor(l.id)?.total_payoff_amount ?? l.outstandingPrincipal) }}
                </td>
              </tr>
              <tr v-if="!customerLoans.length">
                <td colspan="8" class="text-center">{{ t('common.noLoansForCustomer') }}</td>
              </tr>
            </tbody>
            <tfoot v-if="customerLoans.length">
              <tr>
                <th colspan="4">{{ t('common.totals') }}</th>
                <th class="text-right">{{ formatCurrency(customerTotalOutstanding) }}</th>
                <th class="text-right">{{ formatCurrency(customerOwed.interest) }}</th>
                <th class="text-right">{{ formatCurrency(customerOwed.penalties) }}</th>
                <th class="text-right">{{ formatCurrency(customerOwed.total) }}</th>
              </tr>
            </tfoot>
          </table>
          <p class="muted mt-8">{{ t('common.statementNote') }}</p>
        </template>

        <!-- Payment history -->
        <template v-else-if="isHistory">
          <h3>{{ t('common.paymentHistoryTitle') }}</h3>
          <table class="print-table compact-table">
            <thead>
              <tr>
                <th>{{ t('common.date') }}</th>
                <th>{{ t('common.loan') }}</th>
                <th>{{ t('common.concept') }}</th>
                <th>{{ t('payments.period') }}</th>
                <th class="text-right">{{ t('common.interest') }}</th>
                <th class="text-right">{{ t('common.penalty') }}</th>
                <th class="text-right">{{ t('common.principal') }}</th>
                <th class="text-right">{{ t('common.total') }}</th>
                <th>{{ t('common.receivedBy') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="event in historyEvents" :key="event.id" :class="{ 'row-reversed': event.is_reversed }">
                <td>{{ formatDateDMY(event.payment_date) }}</td>
                <td>{{ loanLabel(event.loan_id) }}</td>
                <td>
                  {{ eventTypeLabel(event.payment_type) }}
                  <strong v-if="event.is_reversed"> · {{ t('common.reversedFlag') }}</strong>
                </td>
                <td>{{ event.billing_period || '-' }}</td>
                <td class="text-right">{{ formatCurrency(event.allocated_to_interest) }}</td>
                <td class="text-right">{{ formatCurrency(event.allocated_to_penalty) }}</td>
                <td class="text-right">{{ formatCurrency(event.allocated_to_principal) }}</td>
                <td class="text-right">{{ formatCurrency(event.total_entered_amount) }}</td>
                <td>{{ event.operator?.full_name || event.operator?.username || '-' }}</td>
              </tr>
              <tr v-if="!historyEvents.length">
                <td colspan="9" class="text-center">{{ t('common.noPaymentsForCustomer') }}</td>
              </tr>
            </tbody>
            <tfoot v-if="historyEvents.length">
              <tr>
                <th colspan="4">{{ t('common.totals') }}</th>
                <th class="text-right">{{ formatCurrency(historyTotals.interest) }}</th>
                <th class="text-right">{{ formatCurrency(historyTotals.penalty) }}</th>
                <th class="text-right">{{ formatCurrency(historyTotals.principal) }}</th>
                <th class="text-right">{{ formatCurrency(historyTotals.total) }}</th>
                <th></th>
              </tr>
            </tfoot>
          </table>
          <p class="muted mt-8">{{ t('common.historyNote', { count: historyEvents.length }) }}</p>
        </template>
      </div>

      <!-- ── LOAN STATEMENT (estado de cuenta del préstamo) ── -->
      <div class="balances-section mt-16" v-if="isLoan && loan">
        <h3>{{ t('common.loanStatementTitle') }}</h3>
        <table class="print-table balances-table">
          <tbody>
            <tr>
              <td>{{ t('common.remainingPrincipal') }}</td>
              <td class="text-right balance-value" :class="{ 'balance-zero': loan.outstandingPrincipal === 0 }">
                {{ formatCurrency(loan.outstandingPrincipal) }}
              </td>
            </tr>
            <tr>
              <td>{{ t('common.accruedInterest') }}</td>
              <td class="text-right balance-value" :class="{ 'balance-zero': loanOwedInterest === 0 }">
                {{ formatCurrency(loanOwedInterest) }}
              </td>
            </tr>
            <tr v-if="loanOwedPenalty > 0">
              <td>{{ t('common.penalty') }}</td>
              <td class="text-right balance-value">{{ formatCurrency(loanOwedPenalty) }}</td>
            </tr>
            <tr class="balance-total-row">
              <td><strong>{{ t('common.totalToSettle') }}</strong></td>
              <td class="text-right balance-value">{{ formatCurrency(loanTotalOwed) }}</td>
            </tr>
            <tr v-if="loanStatement">
              <td>{{ t('common.nextDueDate') }}</td>
              <td class="text-right">{{ formatDateDMY(loanStatement.next_due_date) }}</td>
            </tr>
            <tr>
              <td><strong>{{ t('common.loanStatus') }}</strong></td>
              <td class="text-right">
                <span class="status-badge" :class="loanStatusClass">{{ loanStatusLabel }}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <template v-if="loanPendingItems.length">
          <h3 class="mt-16">{{ t('common.pendingPeriodsTitle') }}</h3>
          <table class="print-table compact-table">
            <thead>
              <tr>
                <th>{{ t('payments.period') }}</th>
                <th>{{ t('common.dueOn') }}</th>
                <th class="text-right">{{ t('common.periodInterest') }}</th>
                <th class="text-right">{{ t('common.pending') }}</th>
                <th class="text-right">{{ t('common.penalty') }}</th>
                <th class="text-right">{{ t('common.subtotal') }}</th>
                <th>{{ t('common.status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in loanPendingItems" :key="item.interest_charge_id">
                <td>{{ item.billing_period }}</td>
                <td>{{ formatDateDMY(item.due_date) }}</td>
                <td class="text-right">{{ formatCurrency(item.original_interest_amount) }}</td>
                <td class="text-right">{{ formatCurrency(item.remaining_pending_amount) }}</td>
                <td class="text-right">{{ formatCurrency(item.penalty_amount) }}</td>
                <td class="text-right balance-value">{{ formatCurrency(item.current_outstanding_balance) }}</td>
                <td>
                  <span class="status-badge" :class="item.overdue ? 'status-overdue' : 'status-active'">
                    {{ item.overdue ? t('common.overdue') : t('common.periodCurrent') }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </template>

        <div class="closed-notice" v-if="loan.status === 'closed'">
          {{ t('common.loanClosedNotice') }}
        </div>
      </div>

      <!-- ── POST-PAYMENT BALANCES (the main new section) ── -->
      <div class="balances-section mt-16" v-if="isPayment && loan">
        <h3>{{ t('common.remainingBalancesTitle') }}</h3>
        <table class="print-table balances-table">
          <tbody>
            <tr>
              <td>{{ t('common.remainingPrincipal') }}</td>
              <td class="text-right balance-value" :class="{ 'balance-zero': loan.outstandingPrincipal === 0 }">
                {{ formatCurrency(loan.outstandingPrincipal) }}
              </td>
            </tr>
            <tr v-if="pendingInterestAfterPayment !== null">
              <td>{{ t('common.remainingInterest') }}</td>
              <td class="text-right balance-value" :class="{ 'balance-zero': pendingInterestAfterPayment === 0 }">
                {{ formatCurrency(pendingInterestAfterPayment) }}
              </td>
            </tr>
            <tr v-if="pendingPenaltyAfterPayment !== null && pendingPenaltyAfterPayment > 0">
              <td>{{ t('common.remainingPenalty') }}</td>
              <td class="text-right balance-value">
                {{ formatCurrency(pendingPenaltyAfterPayment) }}
              </td>
            </tr>
            <tr class="balance-total-row">
              <td><strong>{{ t('common.loanStatus') }}</strong></td>
              <td class="text-right">
                <span class="status-badge" :class="loanStatusClass">{{ loanStatusLabel }}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Loan closed notice -->
        <div class="closed-notice" v-if="loan.status === 'closed'">
          {{ t('common.loanClosedNotice') }}
        </div>
      </div>

      <div class="invoice-footer">
        <p>{{ t('common.thanksNote') }}</p>
        <p class="muted">{{ t('common.generatedBy', { app: appDisplayName }) }}</p>
      </div>
    </div>

    <div v-else class="loading">
      {{ t('common.loadingDocument') }}
    </div>

    <!-- The user prints from the browser, we auto-trigger on load -->
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platformStore'
import { formatDateDMY } from '../utils/date'
import { apiClient } from '../services/api'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { state, ensureInitialized } = usePlatformStore()

const type = computed(() => route.params.type as string)
const id = computed(() => Number(route.params.id))

const isPayment = computed(() => type.value === 'payment')
const isCustomer = computed(() => type.value === 'customer')
const isHistory = computed(() => type.value === 'history')
const isLoan = computed(() => !isPayment.value && !isCustomer.value && !isHistory.value)
const ready = ref(false)

// Post-payment pending interest/penalty fetched from the API
const pendingInterestAfterPayment = ref<number | null>(null)
const pendingPenaltyAfterPayment = ref<number | null>(null)

interface LoanStatement {
  loan_id: number
  next_due_date: string
  original_principal: number
  outstanding_principal: number
  accrued_unpaid_interest: number
  penalties: number
  total_payoff_amount: number
}

interface PendingInterestItem {
  interest_charge_id: number
  loan_id: number
  billing_period: string
  due_date: string
  original_interest_amount: number
  remaining_pending_amount: number
  overdue: boolean
  penalty_amount: number
  current_outstanding_balance: number
}

interface PaymentEventRow {
  id: number
  payment_type: string
  loan_id: number
  billing_period: string
  total_entered_amount: number
  allocated_to_interest: number
  allocated_to_penalty: number
  allocated_to_principal: number
  payment_date: string
  payment_method: string
  notes: string
  is_reversed: boolean
  operator?: { full_name?: string; username?: string } | null
}

// Statement data: per-loan balances and the pending periods behind them.
const statements = ref<LoanStatement[]>([])
const pendingItems = ref<PendingInterestItem[]>([])
const historyEvents = ref<PaymentEventRow[]>([])

const printDocument = () => {
  window.print()
}

const payment = computed(() => state.payments.find(p => p.id === id.value))
const loan = computed(() => {
  if (isPayment.value && payment.value) {
    return state.loans.find(l => l.id === payment.value!.loanId)
  } else if (isLoan.value) {
    return state.loans.find(l => l.id === id.value)
  }
  return undefined
})

const customer = computed(() => {
  // For customer statements and payment history the route id is the customer.
  if (isCustomer.value || isHistory.value) {
    return state.customers.find(c => c.id === id.value)
  }
  if (loan.value) {
    return state.customers.find(c => c.id === loan.value!.customerId)
  }
  return undefined
})

const customerLoans = computed(() => {
  if (!isCustomer.value || !customer.value) return []
  return state.loans.filter(l => l.customerId === customer.value!.id)
})

const loanLabel = (loanId: number) => `LN-${loanId.toString().padStart(6, '0')}`

const customerTotalOutstanding = computed(() => {
  return customerLoans.value.reduce((sum, l) => sum + l.outstandingPrincipal, 0)
})

const statementFor = (loanId: number) => statements.value.find((item) => item.loan_id === loanId) ?? null

const loanStatement = computed(() => (loan.value ? statementFor(loan.value.id) : null))

const loanPendingItems = computed(() => {
  const current = loan.value
  if (!current) return []
  return pendingItems.value
    .filter((item) => item.loan_id === current.id)
    .sort((a, b) => a.due_date.localeCompare(b.due_date))
})

// Closed loans are absent from the statement endpoints because they owe nothing.
const loanOwedInterest = computed(() => loanStatement.value?.accrued_unpaid_interest ?? 0)
const loanOwedPenalty = computed(() => loanStatement.value?.penalties ?? 0)
const loanTotalOwed = computed(
  () => loanStatement.value?.total_payoff_amount ?? loan.value?.outstandingPrincipal ?? 0
)

const customerOwed = computed(() => ({
  interest: statements.value.reduce((sum, item) => sum + item.accrued_unpaid_interest, 0),
  penalties: statements.value.reduce((sum, item) => sum + item.penalties, 0),
  total: statements.value.reduce((sum, item) => sum + item.total_payoff_amount, 0)
}))

const activeHistoryEvents = computed(() => historyEvents.value.filter((event) => !event.is_reversed))

const historyTotals = computed(() => ({
  interest: activeHistoryEvents.value.reduce((sum, event) => sum + event.allocated_to_interest, 0),
  penalty: activeHistoryEvents.value.reduce((sum, event) => sum + event.allocated_to_penalty, 0),
  principal: activeHistoryEvents.value.reduce((sum, event) => sum + event.allocated_to_principal, 0),
  total: activeHistoryEvents.value.reduce((sum, event) => sum + event.total_entered_amount, 0)
}))

const globalSettings = computed(() => state.globalSettings)

// Per-instance name, so a white-labelled deployment prints its own brand.
const appDisplayName = computed(() => globalSettings.value?.appName || t('app.title'))

const idString = computed(() => {
  if (isCustomer.value || isHistory.value) return `CST-${id.value.toString().padStart(6, '0')}`
  if (isPayment.value) return `PAY-${id.value.toString().padStart(6, '0')}`
  return loanLabel(id.value)
})

const dateString = computed(() => {
  // Statements and histories are dated the day they are printed.
  if (isCustomer.value || isHistory.value) {
    return formatDateDMY(new Date().toISOString())
  }
  if (isPayment.value && payment.value) {
    return formatDateDMY(payment.value.paymentDate)
  }
  if (isLoan.value && loan.value) {
    return formatDateDMY(loan.value.disbursementDate)
  }
  return ''
})

const eventTypeKeys: Record<string, string> = {
  interest_payment: 'common.eventInterestPayment',
  partial_interest_payment: 'common.eventPartialInterestPayment',
  interest_advance_payment: 'common.eventInterestAdvance',
  partial_principal_payment: 'common.eventPartialPrincipalPayment',
  full_settlement: 'common.eventFullSettlement',
  mixed_payment: 'common.eventMixedPayment'
}

const eventTypeLabel = (value: string) => {
  const key = eventTypeKeys[value]
  return key ? t(key) : value.replace(/_/g, ' ')
}

const formatCurrency = (val: number) => {
  const code = globalSettings.value?.currencyCode || 'COP'
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: code }).format(val)
}

/**
 * Human-readable label for the payment type derived from the allocation breakdown.
 * We infer the type from what was allocated since Payment model doesn't carry an explicit type field.
 */
const getPaymentTypeLabel = (p: typeof payment.value) => {
  if (!p) return ''
  if (p.allocatedToPrincipal > 0 && p.allocatedToInterest === 0) return t('common.typePrincipalPayment')
  if (p.allocatedToInterest > 0 && p.allocatedToPrincipal === 0) return t('common.typeInterestPayment')
  if (p.allocatedToPenalty > 0 && p.allocatedToPrincipal === 0 && p.allocatedToInterest === 0) {
    return t('common.typePenaltyPayment')
  }
  return t('common.typeMixedPayment')
}

const getLoanStatusLabel = (l: { status: string }) => {
  const keys: Record<string, string> = {
    active: 'common.active',
    overdue: 'common.overdue',
    defaulted: 'common.defaulted',
    closed: 'common.closed'
  }
  const key = keys[l.status]
  return key ? t(key) : l.status
}

const loanStatusLabel = computed(() => {
  if (!loan.value) return ''
  return getLoanStatusLabel(loan.value)
})

const getLoanStatusClass = (l: { status: string }) => {
  return {
    'status-active': l.status === 'active',
    'status-overdue': l.status === 'overdue',
    'status-closed': l.status === 'closed'
  }
}

const loanStatusClass = computed(() => {
  if (!loan.value) return ''
  return getLoanStatusClass(loan.value)
})

const paymentMethodLabel = computed(() => {
  if (!payment.value) return ''
  if (payment.value.paymentMethod === 'cash') return t('common.cash')
  if (payment.value.paymentMethod === 'bank-transfer') return t('common.bankTransfer')
  return t('common.other')
})

const loadStatement = async (customerId: number) => {
  const [context, pending] = await Promise.all([
    apiClient.request<{ items: LoanStatement[] }>(`/payments/customers/${customerId}/principal-context`),
    apiClient.request<{
      groups: { items: PendingInterestItem[] }[]
      total_pending_interest: number
      total_pending_penalty: number
    }>(`/payments/customers/${customerId}/interest-pending`)
  ])

  statements.value = context.items
  pendingItems.value = pending.groups.flatMap((group) => group.items)
  return pending
}

onMounted(async () => {
  await ensureInitialized()

  try {
    if (isPayment.value && payment.value && loan.value) {
      // Balances remaining AFTER this payment, for the receipt.
      const pending = await loadStatement(loan.value.customerId)
      pendingInterestAfterPayment.value = pending.total_pending_interest
      pendingPenaltyAfterPayment.value = pending.total_pending_penalty
    } else if (isLoan.value && loan.value) {
      await loadStatement(loan.value.customerId)
    } else if (isCustomer.value && customer.value) {
      await loadStatement(customer.value.id)
    } else if (isHistory.value) {
      historyEvents.value = await apiClient.request<PaymentEventRow[]>(
        `/payments/customers/${id.value}/history`
      )
    }
  } catch {
    // Non-critical: the document still prints with the data already in the store.
    pendingInterestAfterPayment.value = null
  }

  ready.value = true
  setTimeout(() => {
    window.print()
  }, 500)
})
</script>

<style scoped>
.print-container {
  background: #f1f5f9;
  min-height: 100vh;
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.actions-bar {
  display: flex;
  justify-content: space-between;
  width: 100%;
  max-width: 800px;
  margin-bottom: 20px;
}

.invoice-box {
  background: white;
  width: 100%;
  max-width: 800px;
  padding: 40px;
  box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
  border-radius: var(--radius-lg, 8px);
  color: var(--text, #334155);
  font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
}

.invoice-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 20px;
  margin-bottom: 20px;
}

.company-details h2 {
  margin: 0 0 5px 0;
  color: #0f172a;
}

.invoice-meta h1 {
  margin: 0 0 10px 0;
  color: var(--accent, #4f46e5);
  font-size: 24px;
  text-align: right;
}

.invoice-meta p {
  margin: 0;
  text-align: right;
}

.customer-info h3, .loan-info h3, .balances-section h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 5px;
}

.customer-info p, .loan-info p {
  margin: 5px 0;
}

.loan-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 16px;
}

.print-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.print-table th, .print-table td {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.print-table th {
  background-color: var(--surface-soft, #f8fafc);
  font-weight: 600;
  color: var(--text, #475569);
  border-bottom: 2px solid var(--line-light, #e2e8f0);
}

.print-table tfoot th {
  background-color: #f1f5f9;
  font-size: 18px;
  color: #0f172a;
}

/* Balances section */
.balances-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
}

.balances-section h3 {
  color: var(--accent, #4f46e5);
  border-bottom-color: var(--line-light, #e2e8f0);
}

.balances-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
}

.balances-table .balance-total-row td {
  border-bottom: none;
  padding-top: 14px;
}

.balance-value {
  font-weight: 700;
  font-size: 1.05em;
  color: #0f172a;
}

.balance-zero {
  color: #16a34a !important;
}

/* Status badge */
.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.85em;
  font-weight: 600;
}

.status-active {
  background: #dcfce7;
  color: #15803d;
}

.status-overdue {
  background: #fee2e2;
  color: #dc2626;
}

.status-closed {
  background: #d1fae5;
  color: #065f46;
}

/* Closed notice */
.closed-notice {
  margin-top: 12px;
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  border-radius: 6px;
  padding: 12px 16px;
  color: #065f46;
  font-size: 0.95em;
}

/* .text-right, .text-center, .mt-8 and .mt-16 come from main.css. */

/* Wider statement and history tables need to stay within one printed page width. */
.compact-table th,
.compact-table td {
  padding: 7px 8px;
  font-size: 0.82em;
}

.row-reversed td {
  color: var(--muted, #475569);
  text-decoration: line-through;
}

.row-reversed td strong {
  color: var(--danger, #ef4444);
  text-decoration: none;
}

.payment-notes {
  background: var(--surface-soft, #f8fafc);
  padding: 15px;
  border-radius: var(--radius-md, 6px);
  border-left: 4px solid var(--accent, #4f46e5);
}

.invoice-footer {
  margin-top: 50px;
  text-align: center;
  border-top: 1px solid #e2e8f0;
  padding-top: 20px;
}

.muted {
  color: #94a3b8;
  font-size: 12px;
}

.loading {
  font-size: 1.2rem;
  color: #64748b;
  text-align: center;
  width: 100%;
  padding-top: 100px;
}

@media print {
  body * {
    visibility: hidden;
  }
  .no-print {
    display: none !important;
  }
  .print-container {
    background: transparent;
    padding: 0;
  }
  .invoice-box, .invoice-box * {
    visibility: visible;
  }
  .invoice-box {
    position: absolute;
    left: 0;
    top: 0;
    box-shadow: none;
    padding: 0;
    max-width: none;
    width: 100%;
  }
  @page {
    margin: 1.5cm;
  }
}
</style>
