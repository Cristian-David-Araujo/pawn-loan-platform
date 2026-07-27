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
            {{ globalSettings.companyDocumentType || t('common.taxId') }}: {{ globalSettings.companyDocumentNumber }}
          </p>
          <p v-if="globalSettings?.companyAddress">
            {{ globalSettings.companyAddress }}
          </p>
          <p v-if="globalSettings?.companyPhone">
            {{ t('common.phoneShort') }}: {{ globalSettings.companyPhone }}
          </p>
          <p v-if="globalSettings?.companyEmail">
            {{ t('common.emailLabel') }}: {{ globalSettings.companyEmail }}
          </p>
        </div>
        <div class="invoice-meta">
          <h1>{{ documentTitle }}</h1>
          <p v-if="!isCustomer"><strong>{{ t('common.documentNo') }}:</strong> {{ idString }}</p>
          <p><strong>{{ t('common.documentDate') }}:</strong> {{ dateString }}</p>
        </div>
      </div>

      <!-- A reversed payment must never read as a valid receipt. -->
      <div class="reversed-notice" v-if="isPayment && payment?.isReversed">
        {{ t('common.reversedFlag') }} — {{ t('common.paymentReversedNotice') }}
      </div>

      <!-- Customer info -->
      <div class="doc-section" v-if="customer">
        <h3 class="section-title">{{ t('common.customerDataTitle') }}</h3>
        <div class="info-grid">
          <p><strong>{{ t('common.name') }}:</strong> {{ customer.fullName }}</p>
          <p><strong>{{ customer.documentType }}:</strong> {{ customer.documentNumber }}</p>
          <p><strong>{{ t('common.phone') }}:</strong> {{ customer.phone }}</p>
        </div>
      </div>

      <!-- Payment metadata (receipts) -->
      <div class="doc-section" v-if="isPayment && payment">
        <h3 class="section-title">{{ t('common.paymentDetailsTitle') }}</h3>
        <div class="info-grid">
          <p v-if="spansMultipleLoans">
            <strong>{{ t('common.loansCovered') }}:</strong> {{ coveredLoanLabels }}
          </p>
          <p v-else-if="loan"><strong>{{ t('common.loanNumber') }}:</strong> {{ loanLabel(loan.id) }}</p>
          <p v-if="loan">
            <strong>{{ t('common.type') }}:</strong>
            {{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}
          </p>
          <p><strong>{{ t('common.receiptPaymentType') }}:</strong> {{ getPaymentTypeLabel(payment) }}</p>
          <p>
            <strong>{{ t('common.amountReceived') }}:</strong>
            <span class="balance-value">{{ formatCurrency(payment.totalAmount) }}</span>
          </p>
          <p><strong>{{ t('common.method') }}:</strong> {{ paymentMethodLabel }}</p>
          <p v-if="payment.receiver">
            <strong>{{ t('common.receivedBy') }}:</strong>
            {{ payment.receiver.full_name || payment.receiver.username }}
          </p>
          <p class="span-2" v-if="payment.notes">
            <strong>{{ t('common.notes') }}:</strong> {{ payment.notes }}
          </p>
        </div>
      </div>

      <!-- Payment details table -->
      <div class="invoice-details">
        <template v-if="isPayment && payment">
          <!-- Only for legacy payments with no ledger rows: the breakdown below
               already totals the same buckets, so showing both is noise. -->
          <div class="doc-section" v-if="!breakdownLines.length">
            <h3 class="section-title">{{ t('common.paymentSummaryTitle') }}</h3>
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
          </div>

          <!-- One payment can settle several invoices, so show where each part landed. -->
          <div class="doc-section" v-if="breakdownLines.length">
            <h3 class="section-title">{{ t('common.paymentBreakdownTitle') }}</h3>
            <table class="print-table">
              <thead>
                <tr>
                  <th v-if="spansMultipleLoans">{{ t('common.loan') }}</th>
                  <th>{{ t('payments.period') }}</th>
                  <th>{{ t('common.dueOn') }}</th>
                  <th class="text-right">{{ t('common.chargeAmount') }}</th>
                  <th class="text-right">{{ t('common.interest') }}</th>
                  <th class="text-right" v-if="breakdownHasPenalty">{{ t('common.penalty') }}</th>
                  <th class="text-right" v-if="breakdownHasPrincipal">{{ t('common.principal') }}</th>
                  <th class="text-right">{{ t('common.applied') }}</th>
                  <th>{{ t('common.coverage') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="line in breakdownLines"
                  :key="line.payment_event_id"
                  :class="{ 'row-reversed': line.is_reversed }"
                >
                  <td v-if="spansMultipleLoans">{{ loanLabel(line.loan_id) }}</td>
                  <td>{{ line.billing_period || eventTypeLabel(line.payment_type) }}</td>
                  <td>{{ line.charge_due_date ? formatDateDMY(line.charge_due_date) : '—' }}</td>
                  <td class="text-right">
                    {{ line.charge_amount !== null ? formatCurrency(line.charge_amount) : '—' }}
                  </td>
                  <td class="text-right">{{ formatCurrency(line.allocated_to_interest) }}</td>
                  <td class="text-right" v-if="breakdownHasPenalty">
                    {{ formatCurrency(line.allocated_to_penalty) }}
                  </td>
                  <td class="text-right" v-if="breakdownHasPrincipal">
                    {{ formatCurrency(line.allocated_to_principal) }}
                  </td>
                  <td class="text-right balance-value">{{ formatCurrency(line.allocated_total) }}</td>
                  <td class="coverage-cell">{{ coverageLabel(line) }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <th :colspan="breakdownLabelSpan">{{ t('common.totalApplied') }}</th>
                  <th class="text-right">{{ formatCurrency(breakdownTotals.interest) }}</th>
                  <th class="text-right" v-if="breakdownHasPenalty">
                    {{ formatCurrency(breakdownTotals.penalty) }}
                  </th>
                  <th class="text-right" v-if="breakdownHasPrincipal">
                    {{ formatCurrency(breakdownTotals.principal) }}
                  </th>
                  <th class="text-right">{{ formatCurrency(breakdownTotals.total) }}</th>
                  <th></th>
                </tr>
              </tfoot>
            </table>
            <p class="note" v-if="unallocatedAmount > 0">
              {{ t('common.unallocatedAmount') }}: <strong>{{ formatCurrency(unallocatedAmount) }}</strong>
            </p>
            <p class="muted">{{ t('common.breakdownNote') }}</p>
          </div>
        </template>

        <template v-else-if="isLoan && loan">
          <div class="doc-section">
            <h3 class="section-title">{{ t('common.loanDetailsTitle') }}</h3>
            <table class="print-table">
              <thead>
                <tr>
                  <th>{{ t('common.concept') }}</th>
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
            <div class="info-grid" v-if="loan.description || loan.created_by">
              <p class="span-2" v-if="loan.description">
                <strong>{{ t('common.description') }}:</strong> {{ loan.description }}
              </p>
              <p v-if="loan.created_by">
                <strong>{{ t('common.createdBy') }}:</strong>
                {{ loan.created_by.full_name || loan.created_by.username }}
              </p>
            </div>
          </div>
        </template>

        <!-- Customer Statement (Estado de Cuenta) -->
        <template v-else-if="isCustomer && customer">
          <div class="doc-section">
            <h3 class="section-title">{{ t('common.loansSummaryTitle') }}</h3>
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
            <p class="muted">{{ t('common.statementNote') }}</p>
          </div>
        </template>

        <!-- Payment history -->
        <template v-else-if="isHistory">
          <div class="doc-section">
            <h3 class="section-title">{{ t('common.paymentHistoryTitle') }}</h3>
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
            <p class="muted">{{ t('common.historyNote', { count: historyEvents.length }) }}</p>
          </div>
        </template>
      </div>

      <!-- ── LOAN STATEMENT (estado de cuenta del préstamo) ── -->
      <div class="doc-section" v-if="isLoan && loan">
        <h3 class="section-title">{{ t('common.loanStatementTitle') }}</h3>
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
          </tbody>
        </table>
        <!-- Non-monetary facts belong outside the figures, so the table closes on its total. -->
        <div class="info-grid">
          <p v-if="loanStatement">
            <strong>{{ t('common.nextDueDate') }}:</strong> {{ formatDateDMY(loanStatement.next_due_date) }}
          </p>
          <p>
            <strong>{{ t('common.loanStatus') }}:</strong>
            <span class="status-badge" :class="loanStatusClass">{{ loanStatusLabel }}</span>
          </p>
        </div>

        <div class="closed-notice" v-if="loan.status === 'closed'">
          {{ t('common.loanClosedNotice') }}
        </div>
      </div>

      <!-- Pledged items backing the loan; absent for personal loans. -->
      <div class="doc-section" v-if="isLoan && loanCollateral.length">
        <h3 class="section-title">{{ t('common.collateralSectionTitle') }}</h3>
        <table class="print-table compact-table">
          <thead>
            <tr>
              <th>{{ t('collateral.custodyCode') }}</th>
              <th>{{ t('common.description') }}</th>
              <th v-if="collateralHasItemType">{{ t('common.type') }}</th>
              <th v-if="collateralHasSerial">{{ t('common.serialNumber') }}</th>
              <th class="text-right">{{ t('collateral.appraisedValue') }}</th>
              <th v-if="collateralHasStatus">{{ t('common.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in loanCollateral" :key="item.id">
              <td>{{ item.custodyCode }}</td>
              <td>{{ item.description }}</td>
              <td v-if="collateralHasItemType">{{ item.itemType || '—' }}</td>
              <td v-if="collateralHasSerial">{{ item.serialNumber || '—' }}</td>
              <td class="text-right balance-value">{{ formatCurrency(item.appraisedValue) }}</td>
              <td v-if="collateralHasStatus">
                <span class="status-badge" :class="collateralStatusClass(item.status)">
                  {{ collateralStatusLabel(item.status) }}
                </span>
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <th :colspan="collateralLabelSpan">{{ t('common.totalAppraised') }}</th>
              <th class="text-right">{{ formatCurrency(collateralTotalAppraised) }}</th>
              <th v-if="collateralHasStatus"></th>
            </tr>
          </tfoot>
        </table>
        <p class="muted">{{ t('common.collateralNote') }}</p>
      </div>

      <div class="doc-section" v-if="isLoan && loanPendingItems.length">
        <h3 class="section-title">{{ t('common.pendingPeriodsTitle') }}</h3>
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
      </div>

      <!-- ── POST-PAYMENT BALANCES (the main new section) ── -->
      <div class="doc-section" v-if="isPayment && loan">
        <h3 class="section-title">{{ t('common.remainingBalancesTitle') }}</h3>
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
          </tbody>
        </table>
        <div class="info-grid">
          <p>
            <strong>{{ t('common.loanStatus') }}:</strong>
            <span class="status-badge" :class="loanStatusClass">{{ loanStatusLabel }}</span>
          </p>
        </div>

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

/** One line of "where did this payment go" — see GET /payments/{id}/allocations. */
interface PaymentAllocation {
  payment_event_id: number
  payment_type: string
  loan_id: number
  interest_charge_id: number | null
  billing_period: string
  charge_amount: number | null
  charge_due_date: string | null
  allocated_to_interest: number
  allocated_to_penalty: number
  allocated_to_principal: number
  allocated_total: number
  fully_covered: boolean
  is_reversed: boolean
}

interface PaymentAllocations {
  payment_id: number
  payment_date: string
  loan_ids: number[]
  total_amount: number
  total_allocated: number
  unallocated_amount: number
  is_reversed: boolean
  allocations: PaymentAllocation[]
}

// Statement data: per-loan balances and the pending periods behind them.
const statements = ref<LoanStatement[]>([])
const pendingItems = ref<PendingInterestItem[]>([])
const historyEvents = ref<PaymentEventRow[]>([])
const breakdown = ref<PaymentAllocations | null>(null)

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

const loanCollateral = computed(() => {
  const current = loan.value
  if (!current) return []
  return state.collateralItems
    .filter((item) => item.loanId === current.id)
    .sort((a, b) => a.custodyCode.localeCompare(b.custodyCode))
})

const collateralTotalAppraised = computed(() =>
  loanCollateral.value.reduce((sum, item) => sum + item.appraisedValue, 0)
)

// Type and serial are API-only fields with empty-ish defaults, so their columns show up
// only once somebody fills them in — otherwise the table prints a constant.
const collateralHasItemType = computed(() =>
  loanCollateral.value.some((item) => item.itemType && item.itemType !== 'general')
)

const collateralHasSerial = computed(() =>
  loanCollateral.value.some((item) => Boolean(item.serialNumber))
)

// Collateral can only be registered on an open loan and starts out in custody, so on a
// freshly issued document this column is a constant. It only earns its space on a reprint
// after something moved the item (foreclosure, release, sale).
const collateralHasStatus = computed(() =>
  loanCollateral.value.some((item) => item.status !== 'in-custody')
)

const collateralLabelSpan = computed(
  () => 2 + (collateralHasItemType.value ? 1 : 0) + (collateralHasSerial.value ? 1 : 0)
)

const collateralStatusKeys: Record<string, string> = {
  'in-custody': 'collaterals.statusInCustody',
  returned: 'collaterals.statusReturned',
  released: 'collaterals.statusReleased',
  for_sale: 'collaterals.statusForSale',
  sold: 'collaterals.statusSold',
  liquidated: 'collaterals.statusLiquidated'
}

const collateralStatusLabel = (value: string) => {
  const key = collateralStatusKeys[value]
  return key ? t(key) : value
}

const collateralStatusClass = (value: string) => {
  if (value === 'in-custody' || value === 'returned') return 'status-closed'
  if (value === 'liquidated' || value === 'sold') return 'status-overdue'
  return 'status-active'
}

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

const breakdownLines = computed(() => breakdown.value?.allocations ?? [])

// Reversed lines stay visible for traceability but must not inflate the totals.
const breakdownTotals = computed(() => {
  const live = breakdownLines.value.filter((line) => !line.is_reversed)
  return {
    interest: live.reduce((sum, line) => sum + line.allocated_to_interest, 0),
    penalty: live.reduce((sum, line) => sum + line.allocated_to_penalty, 0),
    principal: live.reduce((sum, line) => sum + line.allocated_to_principal, 0),
    total: live.reduce((sum, line) => sum + line.allocated_total, 0)
  }
})

const unallocatedAmount = computed(() => breakdown.value?.unallocated_amount ?? 0)

// `Payment.loan_id` only points at the first loan, so a multi-loan payment needs the real list.
const coveredLoanIds = computed(() => {
  const ids = breakdown.value?.loan_ids ?? []
  if (ids.length) return ids
  return loan.value ? [loan.value.id] : []
})

const spansMultipleLoans = computed(() => coveredLoanIds.value.length > 1)

const coveredLoanLabels = computed(() => coveredLoanIds.value.map(loanLabel).join(', '))

const coverageLabel = (line: PaymentAllocation) =>
  line.fully_covered ? t('common.coverageFull') : t('common.coveragePartial')

// Columns that would be all zeros are dropped, so the table stays readable on paper.
const breakdownHasPenalty = computed(() =>
  breakdownLines.value.some((line) => line.allocated_to_penalty > 0)
)

const breakdownHasPrincipal = computed(() =>
  breakdownLines.value.some((line) => line.allocated_to_principal > 0)
)

const breakdownLabelSpan = computed(() => (spansMultipleLoans.value ? 4 : 3))

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

const documentTitle = computed(() => {
  if (isPayment.value) return t('common.receiptTitle')
  if (isCustomer.value) return t('common.customerStatementTitle')
  if (isHistory.value) return t('common.paymentHistoryTitle')
  return t('common.loanInvoiceTitle')
})

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
    'status-closed': l.status === 'closed',
    'status-defaulted': l.status === 'defaulted'
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
      // Balances remaining AFTER this payment, plus the ledger rows the payment produced.
      const [pending, allocations] = await Promise.all([
        loadStatement(loan.value.customerId),
        apiClient.request<PaymentAllocations>(`/payments/${id.value}/allocations`)
      ])
      pendingInterestAfterPayment.value = pending.total_pending_interest
      pendingPenaltyAfterPayment.value = pending.total_pending_penalty
      breakdown.value = allocations
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
/* ── Document shell ──────────────────────────────────────────
   The four documents (receipt, loan invoice, customer statement, payment
   history) share this shell so they read as one family of paperwork.

   Deliberately restrained: whitespace carries the structure, not fills and
   rules. One accent colour, one emphasis weight, one hairline. Anything that
   adds a second way of saying "this is a section" has been left out. */
.print-container {
  background: var(--surface-hover);
  min-height: 100vh;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.actions-bar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  max-width: 840px;
  margin-bottom: 20px;
}

.invoice-box {
  --doc-gap: 34px;
  background: var(--surface);
  width: 100%;
  max-width: 840px;
  padding: 56px 52px;
  box-shadow: var(--shadow);
  border-radius: var(--radius-xs);
  color: var(--text);
  font-size: 14px;
  line-height: 1.65;
}

/* ── Header ── */
.invoice-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--line);
}

.company-details h2 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text);
}

.company-details p,
.invoice-meta p {
  margin: 0;
  font-size: 12.5px;
  color: var(--muted);
}

.invoice-meta {
  text-align: right;
  flex-shrink: 0;
}

.invoice-meta h1 {
  margin: 0 0 6px 0;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.01em;
  color: var(--accent);
}

/* ── Sections ──
   A quiet lead-in label is the only sectioning device; no boxes, no rules. */
.doc-section {
  margin-top: var(--doc-gap);
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--muted);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 32px;
}

.info-grid p {
  margin: 0;
}

.info-grid strong {
  font-weight: 400;
  color: var(--muted);
}

/* Free text (notes, descriptions) needs the full width, not half a column. */
.info-grid p.span-2 {
  grid-column: 1 / -1;
}

/* Metadata trailing a table reads as a caption, so it needs breathing room. */
.print-table + .info-grid {
  margin-top: 18px;
}

/* ── Tables ── */
.print-table {
  width: 100%;
  border-collapse: collapse;
}

.print-table th,
.print-table td {
  padding: 11px 14px 11px 0;
  text-align: left;
  vertical-align: top;
}

.print-table th:last-child,
.print-table td:last-child {
  padding-right: 0;
}

.print-table thead th {
  padding-top: 0;
  padding-bottom: 9px;
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}

.print-table tbody td {
  border-bottom: 1px solid var(--line-light);
}

.print-table tbody tr:last-child td {
  border-bottom: none;
}

.print-table tfoot th {
  padding-top: 13px;
  font-weight: 600;
  border-top: 1px solid var(--line);
}

.print-table .text-right {
  white-space: nowrap;
}

/* The statement and history tables carry 8-9 columns, so they step down one
   notch rather than getting their own visual language. */
.compact-table th,
.compact-table td {
  padding: 9px 10px 9px 0;
  font-size: 12.5px;
}

.row-reversed td {
  color: var(--muted);
  text-decoration: line-through;
}

.row-reversed td strong {
  color: var(--danger);
  text-decoration: none;
}

.coverage-cell {
  color: var(--muted);
}

/* ── Balances ──
   Same table language as everything else; only the closing figure is bolder. */
.balances-table td {
  padding: 10px 0;
  border-bottom: 1px solid var(--line-light);
}

.balances-table tr:last-child td {
  border-bottom: none;
}

.balances-table .balance-total-row td {
  border-top: 1px solid var(--line);
  border-bottom: none;
  padding-top: 13px;
  font-size: 15px;
}

.balance-value {
  font-weight: 600;
}

/* A settled bucket reads as good news rather than just another figure. */
.balance-zero {
  color: #065f46;
}

/* ── Status pills: the app's own pill shape, minus the border. ── */
.status-badge {
  display: inline-block;
  border-radius: var(--radius-full);
  padding: 0.15rem 0.55rem;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  background: var(--surface-soft);
  color: var(--text-secondary);
}

.status-active {
  background: var(--info-soft);
  color: #3730a3;
}

.status-overdue,
.status-defaulted {
  background: var(--danger-soft);
  color: #b91c1c;
}

.status-closed {
  background: var(--success-soft);
  color: #065f46;
}

/* ── Notices: one shape, tinted by meaning. ── */
.closed-notice,
.reversed-notice,
.note {
  margin: 14px 0 0 0;
  padding: 10px 14px;
  border-left: 2px solid var(--line);
  background: var(--surface-soft);
  color: var(--text-secondary);
  font-size: 13px;
}

.closed-notice {
  border-left-color: var(--success);
  background: var(--success-soft);
  color: #065f46;
}

.reversed-notice {
  margin-top: var(--doc-gap);
  border-left-color: var(--danger);
  background: var(--danger-soft);
  color: #b91c1c;
  font-weight: 600;
}

.note {
  border-left-color: var(--warning);
  background: var(--warning-soft);
  color: #92400e;
}

/* ── Footer ── */
.invoice-footer {
  margin-top: 48px;
  padding-top: 18px;
  border-top: 1px solid var(--line);
  text-align: center;
}

.invoice-footer p {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.muted {
  margin: 12px 0 0 0;
  color: var(--muted);
  font-size: 12px;
}

.loading {
  font-size: 1.05rem;
  color: var(--muted);
  text-align: center;
  width: 100%;
  padding-top: 100px;
}

/* .text-right, .text-center, .mt-8 and .mt-16 come from main.css. */

@media (max-width: 640px) {
  .print-container {
    padding: 16px 10px;
  }

  .invoice-box {
    --doc-gap: 26px;
    padding: 26px 20px;
  }

  .invoice-header {
    flex-direction: column;
    gap: 16px;
  }

  .invoice-meta {
    text-align: left;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}

@media print {
  /* Browsers drop backgrounds by default, which would flatten every pill and
     notice to white. These documents go to customers, so keep them. */
  * {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  .no-print {
    display: none !important;
  }

  .print-container {
    display: block;
    background: transparent;
    padding: 0;
    min-height: 0;
  }

  .invoice-box {
    --doc-gap: 26px;
    max-width: none;
    width: 100%;
    padding: 0;
    box-shadow: none;
    border-radius: 0;
    font-size: 10.5pt;
  }

  /* Long tables repeat their header on every page and never split a row. */
  thead {
    display: table-header-group;
  }

  tfoot {
    display: table-row-group;
  }

  tr {
    break-inside: avoid;
  }

  .section-title,
  .invoice-header {
    break-after: avoid;
  }

  .balances-table,
  .info-grid,
  .closed-notice,
  .reversed-notice,
  .note,
  .invoice-footer {
    break-inside: avoid;
  }

  .invoice-footer {
    margin-top: 30px;
  }

  @page {
    margin: 1.6cm;
  }
}
</style>
