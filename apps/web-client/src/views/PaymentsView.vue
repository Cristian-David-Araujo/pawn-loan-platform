<template>
  <section>
    <PageHeader :title="t('payments.title')" :subtitle="t('payments.subtitle')">
      <template #icon>
        <ReceiptText :size="18" />
      </template>
    </PageHeader>

    <div class="card mt-16 form-inline" style="position: relative; z-index: 50;">
      <label style="width: 100%; max-width: 400px;">
        {{ t('common.customer') }}
        <CustomerAutocomplete v-model="selectedCustomerId" :customers="sortedCustomers" :placeholder="t('common.searchPlaceholder')" />
      </label>
    </div>

    <div class="tabs mt-16">
      <button class="tab-btn" :class="{ active: activeTab === 'interest' }" @click="activeTab = 'interest'" type="button">
        {{ t('payments.interestTab') }}
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'principal' }" @click="activeTab = 'principal'" type="button">
        {{ t('payments.principalTab') }}
      </button>
    </div>

    <!-- Above the working area: at the foot of the page this sat below the history table,
         so a rejected payment looked like nothing had happened at all. -->
    <p v-if="message" class="notice mt-16">{{ message }}</p>

    <div v-if="activeTab === 'interest'" class="card mt-16">
      <h3>{{ t('payments.pendingInterestTitle') }}</h3>
      <p class="muted">{{ t('common.breakdownNote') }}</p>

      <div class="table-toolbar mt-16" style="justify-content: flex-end;">
        <span class="pill">{{ t('payments.suggestedForSelected', { amount: formatCurrency(suggestedSelectedAmount) }) }}</span>
      </div>

      <div class="table-wrap" v-if="flatPendingItems.length">
        <table>
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  :checked="allChargesSelected"
                  :aria-label="t('payments.selectAllRows')"
                  @change="toggleAllCharges"
                />
              </th>
              <th>{{ t('common.loan') }}</th>
              <th>{{ t('common.type') }}</th>
              <th>{{ t('payments.period') }}</th>
              <th>{{ t('payments.dueDate') }}</th>
              <th class="text-right">{{ t('payments.originalInterest') }}</th>
              <th class="text-right">{{ t('payments.pendingInterest') }}</th>
              <th class="text-right">{{ t('payments.penalty') }}</th>
              <th class="text-right">{{ t('payments.outstandingPeriod') }}</th>
              <th>{{ t('common.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in paginatedPendingItems"
              :key="item.interest_charge_id"
              :class="{ 'selected-row': isChargeSelected(item.interest_charge_id) }"
            >
              <td>
                <input
                  type="checkbox"
                  :checked="isChargeSelected(item.interest_charge_id)"
                  :aria-label="t('payments.selectPeriodRow', { period: item.billing_period })"
                  @change="toggleCharge(item.interest_charge_id)"
                />
              </td>
              <td>#{{ item.loan_id }}</td>
              <td>{{ item.loan_type === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
              <td>{{ item.billing_period }}</td>
              <td>{{ formatDateDMY(item.due_date) }}</td>
              <td class="text-right">{{ formatCurrency(item.original_interest_amount) }}</td>
              <td class="text-right">{{ formatCurrency(item.remaining_pending_amount) }}</td>
              <td class="text-right">{{ formatCurrency(item.penalty_amount) }}</td>
              <td class="text-right">{{ formatCurrency(item.current_outstanding_balance) }}</td>
              <td>
                <span class="pill" :class="getPendingStatusClass(item)">
                  {{ t(getPendingStatusKey(item)) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="empty-state" v-else>
        <div class="empty-state-icon"><CircleDollarSign :size="22" /></div>
        <p>{{ selectedCustomerId ? t('payments.noPendingInterest') : t('payments.selectCustomerFirst') }}</p>
      </div>
      <Pagination
        v-if="flatPendingItems.length"
        v-model="pendingInterestCurrentPage"
        :totalItems="flatPendingItems.length"
        :itemsPerPage="10"
      />

      <PaymentCollectionForm
        v-if="flatPendingItems.length"
        v-model:amount="interestEnteredAmount"
        v-model:method="interestPaymentMethod"
        v-model:notes="interestNotes"
        v-model:print-receipt="printReceiptOnSave"
        :submit-label="t('payments.registerInterestPayment')"
        :submit-disabled="interestAmountToPay <= 0 || processing"
        @use-suggested="useSuggestedAmount"
        @amount-edited="interestAmountTouched = true"
        @submit="submitInterestPayment"
      >
        <template #icon><CircleDollarSign :size="16" /></template>
        <p>{{ t('payments.selectedItems', { count: selectedChargeIds.size }) }}</p>
        <p>{{ t('payments.amountEntered', { amount: formatCurrency(interestAmountToPay) }) }}</p>
        <p>{{ t('payments.remainingAfterPayment', { amount: formatCurrency(remainingAfterInterestPayment) }) }}</p>
        <p class="pill pill-warning" v-if="partialAmount > 0">
          {{ t('payments.partialDetected', { amount: formatCurrency(partialAmount) }) }}
        </p>
        <p class="pill pill-upcoming" v-if="advanceAmount > 0">
          {{ t('payments.advanceDetected', { amount: formatCurrency(advanceAmount) }) }}
        </p>
      </PaymentCollectionForm>
    </div>

    <div v-if="activeTab === 'principal'" class="card mt-16">
      <h3>{{ t('payments.principalTitle') }}</h3>
      <p class="muted">{{ t('payments.principalOrderHint') }}</p>

      <div class="table-toolbar mt-16" style="justify-content: flex-end;">
        <span class="pill">{{ t('payments.suggestedForSelected', { amount: formatCurrency(suggestedPrincipalAmount) }) }}</span>
      </div>

      <div class="table-wrap" v-if="principalContextItems.length">
        <table>
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  :checked="allPrincipalLoansSelected"
                  :aria-label="t('payments.selectAllRows')"
                  @change="toggleAllPrincipalLoans"
                />
              </th>
              <th>{{ t('common.loan') }}</th>
              <th>{{ t('common.type') }}</th>
              <th>{{ t('payments.disbursedOn') }}</th>
              <th class="text-right">{{ t('payments.originalPrincipal') }}</th>
              <th class="text-right">{{ t('payments.outstandingPrincipal') }}</th>
              <th class="text-right">{{ t('payments.accruedUnpaidInterest') }}</th>
              <th class="text-right">{{ t('payments.penalty') }}</th>
              <th class="text-right">{{ t('payments.totalPayoff') }}</th>
              <th>{{ t('payments.nextDueDate') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in paginatedPrincipalItems"
              :key="item.loan_id"
              :class="{ 'selected-row': isPrincipalLoanSelected(item.loan_id) }"
            >
              <td>
                <input
                  type="checkbox"
                  :checked="isPrincipalLoanSelected(item.loan_id)"
                  :aria-label="t('payments.selectLoanRow', { id: item.loan_id })"
                  @change="togglePrincipalLoan(item.loan_id)"
                />
              </td>
              <td>
                #{{ item.loan_id }}
                <span class="pill pill-upcoming" v-if="index === 0 && principalCurrentPage === 1">
                  {{ t('payments.oldestTag') }}
                </span>
              </td>
              <td>{{ item.loan_type === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
              <td>{{ formatDateDMY(item.disbursement_date) }}</td>
              <td class="text-right">{{ formatCurrency(item.original_principal) }}</td>
              <td class="text-right">{{ formatCurrency(item.outstanding_principal) }}</td>
              <td class="text-right">{{ formatCurrency(item.accrued_unpaid_interest) }}</td>
              <td class="text-right">{{ formatCurrency(item.penalties) }}</td>
              <td class="text-right">{{ formatCurrency(item.total_payoff_amount) }}</td>
              <td>{{ formatDateDMY(item.next_due_date) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="empty-state" v-else>
        <div class="empty-state-icon"><WalletCards :size="22" /></div>
        <p>{{ selectedCustomerId ? t('payments.noLoansForPrincipal') : t('payments.selectCustomerFirst') }}</p>
      </div>
      <Pagination
        v-if="principalContextItems.length"
        v-model="principalCurrentPage"
        :totalItems="principalContextItems.length"
        :itemsPerPage="10"
      />

      <PaymentCollectionForm
        v-if="principalContextItems.length"
        v-model:amount="principalAmount"
        v-model:method="principalPaymentMethod"
        v-model:notes="principalNotes"
        v-model:print-receipt="printReceiptOnSave"
        :submit-label="t('payments.registerPrincipalPayment')"
        :submit-disabled="!selectedChargeCountPrincipal || principalAmountToPay <= 0 || principalExceedsSelected || principalBlockedByInterest || processing"
        @use-suggested="usePrincipalSuggestedAmount"
        @amount-edited="principalAmountTouched = true"
        @submit="submitPrincipalPayment"
      >
        <template #icon><WalletCards :size="16" /></template>
        <p>{{ t('payments.selectedItems', { count: selectedChargeCountPrincipal }) }}</p>
        <p>{{ t('payments.amountEntered', { amount: formatCurrency(principalAmountToPay) }) }}</p>
        <p>{{ t('payments.remainingAfterPrincipal', { amount: formatCurrency(remainingPrincipalAfterPayment) }) }}</p>
        <p class="pill pill-overdue" v-if="principalExceedsSelected">
          {{ t('payments.principalExceedsOutstanding', { amount: formatCurrency(suggestedPrincipalAmount) }) }}
        </p>
        <p class="pill pill-warning" v-else-if="blockedPrincipalLoans.length && !allowPrincipalWithUnpaidInterest">
          {{ t('payments.principalBlockedHint', {
            loans: blockedPrincipalLoans.map((item) => '#' + item.loan_id).join(', '),
            amount: formatCurrency(blockedPrincipalInterest)
          }) }}
        </p>
        <label class="checkbox-row mt-16">
          <input v-model="allowPrincipalWithUnpaidInterest" type="checkbox" />
          {{ t('payments.allowWithUnpaidInterest') }}
        </label>
        <!-- Only when this amount would actually free pledges, so it never sits there as
             an option that does nothing. The items are spelled out because nobody should
             agree to hand over goods they cannot see. -->
        <template v-if="custodyReadyToHandBack.length">
          <label class="checkbox-row">
            <input v-model="handBackCustodyOnSettle" type="checkbox" />
            {{ t('collaterals.handBackOnSettle', { count: custodyReadyToHandBack.length }) }}
          </label>
          <ul class="handback-list">
            <li v-for="item in custodyReadyToHandBack" :key="item.id">
              <strong>{{ item.custodyCode }}</strong> — {{ item.description }}
              <span class="muted">({{ formatCurrency(item.appraisedValue) }})</span>
            </li>
          </ul>
          <p class="handback-total">
            {{ t('collaterals.handBackAppraisedTotal', { amount: formatCurrency(custodyHandBackAppraised) }) }}
          </p>
        </template>
      </PaymentCollectionForm>
    </div>

    <div class="card mt-16" v-if="selectedCustomerId">
      <h3>{{ t('payments.historyTitle') }}</h3>
      <p class="muted">{{ t('payments.historyUnifiedHint') }}</p>
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
          <CustomSelect v-model="historyLoanFilter" :options="historyLoanFilterOptions" />
        </label>
        <label>
          {{ t('payments.filterType') }}
          <CustomSelect v-model="historyTypeFilter" :options="historyTypeFilterOptions" />
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
            <th width="36"></th>
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.loan') }}</th>
            <th>{{ t('common.date') }}</th>
            <th class="text-right">{{ t('common.total') }}</th>
            <th class="text-right">{{ t('common.interest') }}</th>
            <th class="text-right">{{ t('payments.penalty') }}</th>
            <th class="text-right">{{ t('common.principal') }}</th>
            <th>{{ t('common.method') }}</th>
            <th>{{ t('common.receivedBy', 'Received by') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="payment in paginatedCustomerPayments" :key="payment.id">
            <tr>
              <td>
                <button
                  class="btn btn-secondary btn-icon"
                  type="button"
                  :title="t('payments.paymentBreakdown')"
                  :aria-expanded="expandedPaymentIds.has(payment.id)"
                  @click="toggleExpanded(payment.id)"
                >
                  <ChevronDown v-if="expandedPaymentIds.has(payment.id)" :size="14" />
                  <ChevronRight v-else :size="14" />
                </button>
              </td>
              <td>#{{ payment.id }}</td>
              <td>#{{ payment.loanId }}</td>
              <td>{{ formatDateDMY(payment.paymentDate) }}</td>
              <td class="text-right">{{ formatCurrency(payment.totalAmount) }}</td>
              <td class="text-right">{{ formatCurrency(payment.allocatedToInterest) }}</td>
              <td class="text-right">{{ formatCurrency(payment.allocatedToPenalty) }}</td>
              <td class="text-right">{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
              <td>{{ getPaymentMethodLabel(payment.paymentMethod) }}</td>
              <td>{{ payment?.receiver?.full_name || payment?.receiver?.username || '-' }}</td>
              <td>
                <span :class="['pill', payment.isReversed ? 'pill-overdue' : 'pill-current']">
                  {{ payment.isReversed ? t('payments.reversed') : t('common.active') }}
                </span>
              </td>
              <td>
                <div class="form-inline">
                  <a :href="'/print/invoice/payment/' + payment.id" target="_blank" class="btn btn-secondary btn-icon" :title="t('common.printReceipt')" style="text-decoration: none;">
                    <Printer :size="16" />
                  </a>
                  <button v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])" class="btn btn-secondary btn-icon" type="button" :title="t('payments.editPayment')" :disabled="payment.isReversed || processing" @click="openPaymentEditModal(payment)">
                    <Pencil :size="14" />
                  </button>
                  <button
                    v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])"
                    class="btn btn-danger btn-icon"
                    type="button"
                    :title="t('payments.deletePayment')"
                    :aria-label="t('payments.deletePayment')"
                    :disabled="payment.isReversed || processing"
                    @click="openReversalModal(payment)"
                  >
                    <Trash2 :size="14" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="expandedPaymentIds.has(payment.id)" class="payment-detail-row">
              <td colspan="12">
                <div class="payment-breakdown">
                  <!-- A deleted payment has to say who removed it, when and why. -->
                  <p v-if="payment.isReversed" class="pill pill-overdue">
                    <strong>{{ t('payments.reversed') }}:</strong>
                    {{ payment.reversalReason || '—' }}
                    <span v-if="payment.reversedAt">
                      · {{ formatDateDMY(payment.reversedAt.split('T')[0]) }}
                    </span>
                    <span v-if="payment.reverser">
                      · {{ payment.reverser.full_name || payment.reverser.username }}
                    </span>
                  </p>
                  <p v-if="payment.notes" class="muted"><strong>{{ t('payments.notes') }}:</strong> {{ payment.notes }}</p>
                  <table v-if="getPaymentEvents(payment.id).length" class="breakdown-table">
                    <thead>
                      <tr>
                        <th>{{ t('payments.paymentType') }}</th>
                        <th>{{ t('payments.period') }}</th>
                        <th class="text-right">{{ t('common.total') }}</th>
                        <th class="text-right">{{ t('common.interest') }}</th>
                        <th class="text-right">{{ t('payments.penalty') }}</th>
                        <th class="text-right">{{ t('common.principal') }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="event in getPaymentEvents(payment.id)" :key="event.id">
                        <td>{{ getPaymentTypeLabel(event.payment_type) }}</td>
                        <td>{{ event.billing_period || '-' }}</td>
                        <td class="text-right">{{ formatCurrency(event.total_entered_amount) }}</td>
                        <td class="text-right">{{ formatCurrency(event.allocated_to_interest) }}</td>
                        <td class="text-right">{{ formatCurrency(event.allocated_to_penalty) }}</td>
                        <td class="text-right">{{ formatCurrency(event.allocated_to_principal) }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <p v-else class="muted">{{ t('payments.noBreakdown') }}</p>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="!filteredCustomerPayments.length">
            <td colspan="12">{{ t('payments.noHistory') }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <Pagination v-model="customerPaymentsCurrentPage" :totalItems="filteredCustomerPayments.length" :itemsPerPage="10" />
    </div>

    <PaymentReversalModal
      :payment="paymentPendingReversal"
      @close="paymentPendingReversal = null"
      @deleted="onPaymentDeleted"
    />

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
              <CustomSelect v-model="paymentEditForm.paymentMethod" :options="paymentMethodOptions" />
            </label>
            <label>
              {{ t('common.total') }}
              <CurrencyInput v-model="paymentEditForm.totalAmount" :required="true" />
            </label>
            <label>
              {{ t('common.interest') }}
              <CurrencyInput v-model="paymentEditForm.allocatedToInterest" :required="true" />
            </label>
            <label>
              {{ t('payments.penalty') }}
              <CurrencyInput v-model="paymentEditForm.allocatedToPenalty" :required="true" />
            </label>
            <label>
              {{ t('common.fees') }}
              <CurrencyInput v-model="paymentEditForm.allocatedToFees" :required="true" />
            </label>
            <label>
              {{ t('common.principal') }}
              <CurrencyInput v-model="paymentEditForm.allocatedToPrincipal" :required="true" />
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

  </section>
</template>

<script setup lang="ts">
import CustomSelect from '../components/CustomSelect.vue'
import Pagination from '../components/Pagination.vue'
import PaymentCollectionForm from '../components/PaymentCollectionForm.vue'
import PaymentReversalModal from '../components/PaymentReversalModal.vue'
import { usePagination } from '../composables/usePagination'
import { useRowSelection } from '../composables/useRowSelection'
import type { Payment, PaymentMethod } from '../types/domain'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useConfirmDialog } from '../composables/useConfirmDialog'
import { CircleDollarSign, ChevronDown, ChevronRight, FilterX, Pencil, ReceiptText, Save, Trash2, WalletCards, Printer } from 'lucide-vue-next'
import CustomerAutocomplete from '../components/CustomerAutocomplete.vue'
import DateInputField from '../components/DateInputField.vue'
import CurrencyInput from '../components/CurrencyInput.vue'
import PageHeader from '../components/PageHeader.vue'
import { apiClient, apiErrorMessage } from '../services/api'
import { usePlatformStore } from '../stores/platformStore'
import { useAuthState, UserRole } from '../modules/authentication/authState'
import { formatDateDMY, toIsoDate } from '../utils/date'
import { paymentTypeKey } from '../utils/paymentTypes'

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
  payment_id: number | null
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
  operator?: any
}

const { state, ensureInitialized, refreshAll, updatePayment, releaseCollateralForLoan } =
  usePlatformStore()
const { hasRole } = useAuthState()
const router = useRouter()
const { t, locale } = useI18n()
  const { confirm } = useConfirmDialog()
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
  // useRowSelection prunes the ticked rows itself; this only clears the typed amount so
  // the next customer does not inherit a figure from the previous one.
  principalAmount.value = 0
  principalAmountTouched.value = false
})
const principalAmount = ref(0)
const principalPaymentMethod = ref<PaymentMethod>('cash')
const allowPrincipalWithUnpaidInterest = ref(false)
// Off by default on purpose: the vault record must only change when somebody states that
// the goods actually left the counter.
const handBackCustodyOnSettle = ref(false)
const principalNotes = ref('')

const interestPaymentMethod = ref<PaymentMethod>('cash')
const interestNotes = ref('')
const interestEnteredAmount = ref(0)
const interestAmountTouched = ref(false)
const principalAmountTouched = ref(false)

const pendingInterest = ref<InterestPendingResponse | null>(null)
const principalContext = ref<PrincipalContextResponse | null>(null)
const paymentHistory = ref<PaymentEvent[]>([])
const historyFromDate = ref('')
const historyToDate = ref('')
const historyLoanFilter = ref('all')
const historyTypeFilter = ref('all')
const processing = ref(false)
const message = ref('')
const paymentPendingReversal = ref<Payment | null>(null)
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

// Oldest loan first: that is the order the API allocates in, so the table shows the path
// the money will actually take when several loans are ticked.
//
// The context also carries loans that are closed but still owe interest, so the printed
// balances can report them. They have no principal left to pay, so they are dropped here —
// their interest is collected on the other tab.
const principalContextItems = computed(() =>
  (principalContext.value?.items ?? [])
    .filter((item) => item.outstanding_principal > 0)
    .sort((a, b) => {
      const delta =
        new Date(a.disbursement_date).getTime() - new Date(b.disbursement_date).getTime()
      return delta !== 0 ? delta : a.loan_id - b.loan_id
    })
)

const {
  selected: selectedPrincipalLoanIds,
  selectedRows: selectedPrincipalLoans,
  isSelected: isPrincipalLoanSelected,
  toggle: togglePrincipalSelection,
  toggleAll: toggleAllPrincipalSelection,
  selectAll: selectAllPrincipalLoans,
  allSelected: allPrincipalLoansSelected
} = useRowSelection(principalContextItems, (item) => item.loan_id)

const selectedChargeCountPrincipal = computed(() => selectedPrincipalLoanIds.value.size)

const suggestedPrincipalAmount = computed(() =>
  selectedPrincipalLoans.value.reduce((sum, item) => sum + item.outstanding_principal, 0)
)

const principalAmountToPay = computed(() => Math.max(0, principalAmount.value || 0))

const remainingPrincipalAfterPayment = computed(() =>
  Math.max(0, suggestedPrincipalAmount.value - principalAmountToPay.value)
)

// Principal has no advance pool, so the API refuses anything it cannot fully apply.
// Catching it here keeps the operator from submitting a payment that is bound to 400.
const principalExceedsSelected = computed(
  () => principalAmountToPay.value > suggestedPrincipalAmount.value
)

// The API blocks per loan on the pending interest *and* penalty of that loan.
const blockedPrincipalLoans = computed(() =>
  selectedPrincipalLoans.value.filter((item) => item.accrued_unpaid_interest + item.penalties > 0)
)

// The API rejects this combination outright, so the button stays disabled while it holds
// instead of letting the operator click into a guaranteed failure.
const principalBlockedByInterest = computed(
  () => blockedPrincipalLoans.value.length > 0 && !allowPrincipalWithUnpaidInterest.value
)

const blockedPrincipalInterest = computed(() =>
  blockedPrincipalLoans.value.reduce(
    (sum, item) => sum + item.accrued_unpaid_interest + item.penalties,
    0
  )
)

const usePrincipalSuggestedAmount = () => {
  principalAmount.value = suggestedPrincipalAmount.value
}

const sortedPaymentHistory = computed(() =>
  [...paymentHistory.value].sort((a, b) => new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime())
)

const eventsByPaymentId = computed(() => {
  const map = new Map<number, PaymentEvent[]>()
  for (const event of sortedPaymentHistory.value) {
    if (event.payment_id === null || event.payment_id === undefined) {
      continue
    }
    const list = map.get(event.payment_id) ?? []
    list.push(event)
    map.set(event.payment_id, list)
  }
  return map
})

const getPaymentEvents = (paymentId: number) => eventsByPaymentId.value.get(paymentId) ?? []

const expandedPaymentIds = ref(new Set<number>())

const toggleExpanded = (paymentId: number) => {
  const next = new Set(expandedPaymentIds.value)
  if (next.has(paymentId)) {
    next.delete(paymentId)
  } else {
    next.add(paymentId)
  }
  expandedPaymentIds.value = next
}

const paymentHistoryLoanOptions = computed(() => {
  const values = new Set(selectedCustomerPayments.value.map((payment) => String(payment.loanId)))
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

const filteredCustomerPayments = computed(() => {
  const fromIso = toIsoDate(historyFromDate.value)
  const toIso = toIsoDate(historyToDate.value)

  return selectedCustomerPayments.value.filter((payment) => {
    if (historyLoanFilter.value !== 'all' && String(payment.loanId) !== historyLoanFilter.value) {
      return false
    }

    if (historyTypeFilter.value === 'interest' && payment.allocatedToInterest <= 0) {
      return false
    }

    if (historyTypeFilter.value === 'principal' && payment.allocatedToPrincipal <= 0) {
      return false
    }

    const paymentIso = normalizeIso(payment.paymentDate)
    if (!paymentIso) {
      return false
    }

    if (fromIso && paymentIso < fromIso) {
      return false
    }

    if (toIso && paymentIso > toIso) {
      return false
    }

    return true
  })
})

const totalPendingOutstanding = computed(() =>
  flatPendingItems.value.reduce((sum, item) => sum + item.current_outstanding_balance, 0)
)

const {
  selected: selectedChargeIds,
  selectedRows: selectedPendingItems,
  isSelected: isChargeSelected,
  toggle: toggleChargeSelection,
  toggleAll: toggleAllChargeSelection,
  selectAll: selectAllCharges,
  allSelected: allChargesSelected
} = useRowSelection(flatPendingItems, (item) => item.interest_charge_id)

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

const getPaymentTypeLabel = (paymentType: string) => t(paymentTypeKey(paymentType))

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
  if (!selectedCustomerId.value) {
    return
  }
  // A dedicated print document instead of printing the whole application page.
  window.open(`/print/invoice/history/${selectedCustomerId.value}`, '_blank')
}

const openReversalModal = (payment: Payment) => {
  paymentPendingReversal.value = payment
}

const onPaymentDeleted = async (paymentId: number) => {
  await refreshAll()
  await loadCustomerPaymentData()
  message.value = t('payments.paymentDeleted', { id: paymentId })
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
  operator?: any
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
  } catch (error) {
    message.value = apiErrorMessage(error) || t('messages.operationFailed')
  } finally {
    processing.value = false
  }
}

const useSuggestedAmount = () => {
  interestEnteredAmount.value = suggestedSelectedAmount.value
  interestAmountTouched.value = false
}

// Until the operator types an amount by hand, keep it in step with what is ticked.
const toggleCharge = (chargeId: number) => {
  toggleChargeSelection(chargeId)
  if (!interestAmountTouched.value) {
    useSuggestedAmount()
  }
}

const toggleAllCharges = () => {
  toggleAllChargeSelection()
  if (!interestAmountTouched.value) {
    useSuggestedAmount()
  }
}

const togglePrincipalLoan = (loanId: number) => {
  togglePrincipalSelection(loanId)
  if (!principalAmountTouched.value) {
    usePrincipalSuggestedAmount()
  }
}

const toggleAllPrincipalLoans = () => {
  toggleAllPrincipalSelection()
  if (!principalAmountTouched.value) {
    usePrincipalSuggestedAmount()
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
  // Both tabs open with everything ticked and the amount prefilled to that total.
  selectAllCharges()
  useSuggestedAmount()
  selectAllPrincipalLoans()
  usePrincipalSuggestedAmount()
  principalAmountTouched.value = false
}

const submitInterestPayment = async () => {
  if (!selectedCustomerId.value || interestAmountToPay.value <= 0 || processing.value) {
    return
  }

  const confirmed = await confirm(
    t('payments.confirmRegisterInterest', {
      amount: formatCurrency(interestAmountToPay.value),
      count: selectedChargeIds.value.size
    })
  )
  if (!confirmed) {
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
  } catch (error) {
    message.value = apiErrorMessage(error) || t('messages.operationFailed')
  } finally {
    processing.value = false
  }
}

interface PrincipalPaymentResult {
  allocations?: { loan_id: number; loan_status: string }[]
}

const custodyInCustodyFor = (loanId: number) =>
  state.collateralItems.filter((item) => item.loanId === loanId && item.status === 'in-custody')

/**
 * Which of the ticked loans this amount would settle, mirroring the API's oldest-first
 * walk. Used only to decide whether the custody question is worth asking at all.
 */
const loansSettledByPayment = computed(() => {
  let remaining = principalAmountToPay.value
  const settled: number[] = []
  for (const item of selectedPrincipalLoans.value) {
    if (remaining <= 0) break
    if (remaining >= item.outstanding_principal && item.outstanding_principal > 0) {
      settled.push(item.loan_id)
    }
    remaining -= Math.min(item.outstanding_principal, remaining)
  }
  return settled
})

/**
 * Pledges that would be free to hand over once this payment lands. The API refuses to
 * release while interest is pending, so loans that still owe interest are left out.
 */
const custodyHandBackAppraised = computed(() =>
  custodyReadyToHandBack.value.reduce((sum, item) => sum + item.appraisedValue, 0)
)

const custodyReadyToHandBack = computed(() =>
  loansSettledByPayment.value
    .filter((loanId) => {
      const loan = state.loans.find((item) => item.id === loanId)
      return Boolean(loan) && (loan?.interestDue ?? 0) <= 0
    })
    .flatMap((loanId) => custodyInCustodyFor(loanId))
)

/**
 * Closes custody for the loans this payment actually settled, per the server's answer
 * rather than the prediction above.
 *
 * Driven by an explicit checkbox instead of running on its own: handing over the goods is
 * a physical act at the counter, and a customer may pay today and collect next week.
 * Releasing on their behalf would make the custody report claim an empty vault.
 */
const handBackSettledCustody = async (
  allocations: { loan_id: number; loan_status: string }[],
  shownToOperator: Set<number>
) => {
  const settledLoanIds = allocations
    .filter((item) => item.loan_status === 'closed')
    .map((item) => item.loan_id)
    // Never release a pledge the operator was not shown: the server decides what got
    // settled, but consent is limited to the list that was on screen.
    .filter((loanId) => shownToOperator.has(loanId))
    .filter((loanId) => custodyInCustodyFor(loanId).length > 0)

  if (!settledLoanIds.length) {
    return
  }

  const itemCount = settledLoanIds.reduce(
    (sum, loanId) => sum + custodyInCustodyFor(loanId).length,
    0
  )

  try {
    for (const loanId of settledLoanIds) {
      await releaseCollateralForLoan(loanId)
    }
    message.value = t('collaterals.handbackDone', { count: itemCount })
  } catch (error) {
    // The payment itself already succeeded, so say exactly why the pledges stayed put.
    message.value = apiErrorMessage(error) || t('collaterals.handbackFailed')
  }
}

const submitPrincipalPayment = async () => {
  if (
    !selectedCustomerId.value ||
    !selectedPrincipalLoanIds.value.size ||
    principalAmountToPay.value <= 0 ||
    principalExceedsSelected.value ||
    principalBlockedByInterest.value ||
    processing.value
  ) {
    return
  }

  // The one dialog has to state the goods leaving too, not just the money coming in.
  const custodyNote =
    handBackCustodyOnSettle.value && custodyReadyToHandBack.value.length
      ? '\n\n' +
        t('collaterals.confirmHandbackAppend', {
          count: custodyReadyToHandBack.value.length,
          codes: custodyReadyToHandBack.value.map((item) => item.custodyCode).join(', ')
        })
      : ''

  const confirmed = await confirm(
    t('payments.confirmRegisterPrincipal', {
      amount: formatCurrency(principalAmountToPay.value),
      loans: selectedPrincipalLoans.value.map((item) => '#' + item.loan_id).join(', ')
    }) + custodyNote
  )
  if (!confirmed) {
    return
  }

  // Snapshot before the request: both lists recompute once the payment refreshes data.
  const shownForHandback = new Set(loansSettledByPayment.value)

  processing.value = true
  try {
    const result = await apiClient.request<PrincipalPaymentResult>('/payments/principal', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: selectedCustomerId.value,
        // Honoured server-side, unlike the interest flow: the operator picks the loans.
        selected_loan_ids: [...selectedPrincipalLoanIds.value],
        total_amount: principalAmountToPay.value,
        payment_method: principalPaymentMethod.value,
        allow_with_unpaid_interest: allowPrincipalWithUnpaidInterest.value,
        notes: principalNotes.value
      })
    })

    await refreshAll()
    await loadCustomerPaymentData()
    message.value = t('messages.paymentRegistered')

    // Before any navigation: the print redirect below would unmount this view.
    if (handBackCustodyOnSettle.value) {
      await handBackSettledCustody(result.allocations ?? [], shownForHandback)
    }

    if (printReceiptOnSave.value && selectedCustomerPayments.value.length > 0) {
      router.push(`/print/invoice/payment/${selectedCustomerPayments.value[0].id}`)
    }
  } catch (error) {
    message.value = apiErrorMessage(error) || t('messages.operationFailed')
  } finally {
    processing.value = false
  }
}

onMounted(async () => {
  await ensureInitialized()
})
const { currentPage: pendingInterestCurrentPage, paginatedArray: paginatedPendingItems } = usePagination(flatPendingItems)

const { currentPage: principalCurrentPage, paginatedArray: paginatedPrincipalItems } =
  usePagination(principalContextItems)

const { currentPage: customerPaymentsCurrentPage, paginatedArray: paginatedCustomerPayments } = usePagination(filteredCustomerPayments)

const paymentMethodOptions = computed(() => [
  { value: 'cash', label: t('common.cash') },
  { value: 'bank-transfer', label: t('common.bankTransfer') },
  { value: 'other', label: t('common.other') }
])

const historyLoanFilterOptions = computed(() => {
  const options = [{ value: 'all', label: t('payments.allLoans') }]
  paymentHistoryLoanOptions.value.forEach(loanId => {
    options.push({ value: loanId, label: '#' + loanId })
  })
  return options
})

const historyTypeFilterOptions = computed(() => [
  { value: 'all', label: t('payments.allTypes') },
  { value: 'interest', label: t('common.interest') },
  { value: 'principal', label: t('common.principal') }
])
</script>

<style scoped>
/* Spells out the pledges a hand-back would release, right where the choice is made. */
.handback-list {
  margin: 0.4rem 0 0 0;
  padding-left: 1.5rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.handback-list li {
  margin-bottom: 0.15rem;
}

.handback-total {
  margin-top: 0.35rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
}
</style>
