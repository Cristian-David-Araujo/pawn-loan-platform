<template>
  <section>
    <PageHeader :title="t('customers.title')" :subtitle="t('customers.subtitle')">
      <template #icon>
        <Users :size="18" />
      </template>
      <template #actions>
        <button class="btn" type="button" @click="openCreateModal">
          <UserPlus :size="16" />
          {{ t('customers.createCustomer') }}
        </button>
      </template>
    </PageHeader>

    <p v-if="message" class="notice mt-16">{{ message }}</p>

    <div class="card mt-16">
      <div class="table-toolbar">
        <input v-model="search" class="table-search" type="text" :placeholder="t('customers.searchPlaceholder')" />
        <span class="table-count">{{ t('customers.totalRecords', { count: filteredCustomers.length }) }}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('customers.document') }}</th>
            <th>{{ t('common.phone') }}</th>
            <th>{{ t('common.city') }}</th>
            <th>{{ t('common.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="customer in filteredCustomers" :key="customer.id" class="clickable-row" @click="openCustomerDetail(customer.id)">
            <td>{{ customer.id }}</td>
            <td>{{ customer.fullName }}</td>
            <td>{{ customer.documentType }} / {{ customer.documentNumber }}</td>
            <td>{{ customer.phone }}</td>
            <td>{{ customer.city }}</td>
            <td>{{ customer.status === 'active' ? t('common.active') : customer.status }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showCreateModal" class="modal-backdrop" @click.self="closeCreateModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ t('customers.createCustomer') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closeCreateModal">{{ t('common.close') }}</button>
        </div>

        <form class="form mt-16" @submit.prevent="handleCreateCustomer">
          <div class="grid grid-2">
            <label>
              {{ t('customers.fullName') }}
              <input v-model="form.fullName" required />
            </label>
            <label>
              {{ t('customers.documentType') }}
              <input v-model="form.documentType" required />
            </label>
            <label>
              {{ t('customers.documentNumber') }}
              <input v-model="form.documentNumber" required />
            </label>
            <label>
              {{ t('common.phone') }}
              <input v-model="form.phone" required />
            </label>
            <label>
              {{ t('common.city') }}
              <input v-model="form.city" required />
            </label>
          </div>
          <button class="btn" type="submit">
            <UserPlus :size="16" />
            {{ t('customers.createCustomer') }}
          </button>
        </form>
      </div>
    </div>

    <div v-if="showDetailModal && selectedCustomer" class="modal-backdrop" @click.self="closeDetailModal">
      <div class="modal-panel card modal-panel-lg customer-detail-shell">
        <div class="modal-header">
          <h3>{{ t('customers.customerDetail') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closeDetailModal">{{ t('common.close') }}</button>
        </div>

        <p class="muted mt-16">{{ t('customers.selectedCustomer', { id: selectedCustomer.id }) }}</p>

        <div class="customer-header mt-16">
          <div>
            <h3 class="customer-title">{{ selectedCustomer.fullName }}</h3>
            <p class="muted">{{ selectedCustomer.documentType }} / {{ selectedCustomer.documentNumber }}</p>
          </div>
          <span class="pill" :class="selectedCustomer.status === 'active' ? 'pill-current' : 'pill-overdue'">
            {{ selectedCustomer.status === 'active' ? t('common.active') : selectedCustomer.status }}
          </span>
        </div>

        <div class="stats-inline mt-16">
          <span class="pill">{{ t('customers.customerSince', { date: formatDateDMY(selectedCustomer.createdAt) }) }}</span>
          <span class="pill">{{ t('customers.lastUpdate', { date: formatDateDMY(selectedCustomer.updatedAt) }) }}</span>
          <span v-if="firstLoanDisbursementDate" class="pill">
            {{ t('customers.firstLoanDate', { date: formatDateDMY(firstLoanDisbursementDate) }) }}
          </span>
        </div>

        <div class="grid grid-4 mt-16">
          <div class="card stat-card stat-accent-blue">
            <p class="stat-label">{{ t('customers.totalPaidLabel') }}</p>
            <p class="stat-value">{{ formatCurrency(totalCustomerPaid) }}</p>
          </div>
          <div class="card stat-card stat-accent-amber">
            <p class="stat-label">{{ t('customers.pendingOutstanding') }}</p>
            <p class="stat-value">{{ formatCurrency(totalPendingOutstanding) }}</p>
          </div>
          <div class="card stat-card stat-accent-green">
            <p class="stat-label">{{ t('customers.availableAdvance') }}</p>
            <p class="stat-value">{{ formatCurrency(availableAdvanceBalance) }}</p>
          </div>
          <div class="card stat-card stat-accent-indigo">
            <p class="stat-label">{{ t('customers.totalOutstandingPrincipal') }}</p>
            <p class="stat-value">{{ formatCurrency(totalOutstandingPrincipal) }}</p>
          </div>
        </div>

        <div class="stats-inline mt-16">
          <span class="pill">{{ t('customers.pendingInterestOnly', { amount: formatCurrency(totalPendingInterest) }) }}</span>
          <span class="pill">{{ t('customers.pendingPenaltyOnly', { amount: formatCurrency(totalPendingPenalty) }) }}</span>
          <span class="pill">{{ t('customers.unpaidAccruedInterest', { amount: formatCurrency(totalAccruedUnpaidInterest) }) }}</span>
        </div>

        <form class="form mt-16" @submit.prevent="handleUpdateCustomer">
          <div class="grid grid-3">
            <label>
              {{ t('customers.fullName') }}
              <input v-model="editForm.fullName" required />
            </label>
            <label>
              {{ t('customers.document') }}
              <input :value="`${selectedCustomer.documentType} / ${selectedCustomer.documentNumber}`" disabled />
            </label>
            <label>
              {{ t('common.status') }}
              <select v-model="editForm.status" required>
                <option value="active">{{ t('common.active') }}</option>
                <option value="archived">archived</option>
              </select>
            </label>
            <label>
              {{ t('common.phone') }}
              <input v-model="editForm.phone" required />
            </label>
            <label>
              {{ t('customers.email') }}
              <input v-model="editForm.email" type="email" />
            </label>
            <label>
              {{ t('customers.address') }}
              <input v-model="editForm.address" />
            </label>
            <label>
              {{ t('common.city') }}
              <input v-model="editForm.city" required />
            </label>
          </div>
          <button class="btn" type="submit" :disabled="isSaving">
            <Save :size="16" />
            {{ t('customers.saveChanges') }}
          </button>
        </form>

        <div class="mt-16">
          <h3>{{ t('customers.paymentBehavior') }}</h3>
          <p class="muted">{{ t('customers.paymentBehaviorHint') }}</p>
          <p v-if="financialDataLoading" class="muted mt-16">{{ t('customers.loadingFinancialData') }}</p>
          <p v-else-if="financialDataError" class="muted mt-16">{{ t('customers.financialDataUnavailable') }}</p>

          <table v-else>
            <thead>
              <tr>
                <th>{{ t('common.loan') }}</th>
                <th>{{ t('payments.period') }}</th>
                <th>{{ t('payments.dueDate') }}</th>
                <th>{{ t('payments.pendingInterest') }}</th>
                <th>{{ t('payments.penalty') }}</th>
                <th>{{ t('payments.outstandingPeriod') }}</th>
                <th>{{ t('common.status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in pendingInterestItems" :key="item.interest_charge_id">
                <td>#{{ item.loan_id }}</td>
                <td>{{ item.billing_period }}</td>
                <td>{{ formatDateDMY(item.due_date) }}</td>
                <td>{{ formatCurrency(item.remaining_pending_amount) }}</td>
                <td>{{ formatCurrency(item.penalty_amount) }}</td>
                <td>{{ formatCurrency(item.current_outstanding_balance) }}</td>
                <td>
                  <span class="pill" :class="item.overdue ? 'pill-overdue' : 'pill-current'">
                    {{ item.overdue ? t('common.overdue') : t('payments.currentOrUpcoming') }}
                  </span>
                </td>
              </tr>
              <tr v-if="!pendingInterestItems.length">
                <td colspan="7">{{ t('customers.noPendingInterestDetail') }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-16">
          <h3>{{ t('customers.customerPaymentTraceability') }}</h3>
          <p class="muted" v-if="!paymentEvents.length">{{ t('customers.noPaymentEvents') }}</p>
          <table v-else>
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
              <tr v-for="event in paymentEvents" :key="event.id">
                <td>{{ formatDateDMY(event.payment_date) }}</td>
                <td>{{ paymentTypeLabel(event.payment_type) }}</td>
                <td>#{{ event.loan_id }}</td>
                <td>{{ event.billing_period || '-' }}</td>
                <td>{{ formatCurrency(event.total_entered_amount) }}</td>
                <td>{{ formatCurrency(event.allocated_to_interest) }}</td>
                <td>{{ formatCurrency(event.allocated_to_penalty) }}</td>
                <td>{{ formatCurrency(event.allocated_to_principal) }}</td>
                <td>{{ paymentMethodLabel(event.payment_method) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-16">
          <h3>{{ t('customers.customerLoans') }}</h3>
          <p class="muted" v-if="!selectedCustomerLoans.length">{{ t('customers.noLoans') }}</p>
          <table v-else>
            <thead>
              <tr>
                <th>{{ t('common.id') }}</th>
                <th>{{ t('common.type') }}</th>
                <th>{{ t('customers.loanDisbursementDate') }}</th>
                <th>{{ t('loans.dueDay') }}</th>
                <th>{{ t('common.principal') }}</th>
                <th>{{ t('loans.outstanding') }}</th>
                <th>{{ t('loans.rate') }}</th>
                <th>{{ t('common.status') }}</th>
                <th>{{ t('common.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="loan in selectedCustomerLoans"
                :key="loan.id"
                class="clickable-row"
                @click="openCustomerLoanDetail(loan.id)"
              >
                <td>#{{ loan.id }}</td>
                <td>{{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
                <td>{{ formatDateDMY(loan.disbursementDate) }}</td>
                <td>{{ loan.dueDay }}</td>
                <td>{{ formatCurrency(loan.principalAmount) }}</td>
                <td>{{ formatCurrency(loan.outstandingPrincipal) }}</td>
                <td>{{ loan.monthlyInterestRate }}%</td>
                <td>{{ t(`common.${loan.status}`) }}</td>
                <td>
                  <button class="btn btn-secondary" type="button" @click.stop="openLoanEditModal(loan)">
                    {{ t('customers.editLoan') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-16">
          <h3>{{ t('customers.customerPayments') }}</h3>
          <p class="muted">{{ t('customers.totalPaid', { amount: formatCurrency(totalCustomerPaid) }) }}</p>
          <p class="muted" v-if="!selectedCustomerPayments.length">{{ t('customers.noPayments') }}</p>
          <table v-else>
            <thead>
              <tr>
                <th>{{ t('common.id') }}</th>
                <th>{{ t('common.loan') }}</th>
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
              <tr v-for="payment in selectedCustomerPayments" :key="payment.id">
                <td>#{{ payment.id }}</td>
                <td>#{{ payment.loanId }}</td>
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
          <h3>{{ t('customers.customerCollateral') }}</h3>
          <p class="muted" v-if="!selectedCustomerCollateral.length">{{ t('customers.noCollateral') }}</p>
          <table v-else>
            <thead>
              <tr>
                <th>{{ t('common.id') }}</th>
                <th>{{ t('common.loan') }}</th>
                <th>{{ t('customers.associatedLoanType') }}</th>
                <th>{{ t('customers.associatedLoanStatus') }}</th>
                <th>{{ t('common.description') }}</th>
                <th>{{ t('collateral.appraisedValue') }}</th>
                <th>{{ t('collateral.custodyCode') }}</th>
                <th>{{ t('common.status') }}</th>
                <th>{{ t('common.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in selectedCustomerCollateral" :key="item.id">
                <td>#{{ item.id }}</td>
                <td>#{{ item.loanId }}</td>
                <td>{{ getLoanTypeLabel(item.loanId) }}</td>
                <td>{{ getLoanStatusLabel(item.loanId) }}</td>
                <td>{{ item.description }}</td>
                <td>{{ formatCurrency(item.appraisedValue) }}</td>
                <td>{{ item.custodyCode }}</td>
                <td>{{ item.status === 'in-custody' ? t('common.inCustody') : t(`common.${item.status}`) }}</td>
                <td>
                  <button class="btn btn-secondary" type="button" @click="openCollateralEditModal(item)">
                    {{ t('customers.editCollateral') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showCustomerLoanDetailModal && selectedCustomerLoanDetail" class="modal-backdrop" @click.self="closeCustomerLoanDetail">
      <div class="modal-panel card modal-panel-lg">
        <div class="modal-header">
          <h3>{{ t('loans.loanDetail') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closeCustomerLoanDetail">{{ t('common.close') }}</button>
        </div>

        <p class="muted mt-16">{{ t('loans.selectedLoan', { id: selectedCustomerLoanDetail.id }) }}</p>

        <div class="grid grid-4 mt-16">
          <div class="card stat-card stat-accent-indigo">
            <p class="stat-label">{{ t('common.customer') }}</p>
            <p class="stat-value">{{ selectedCustomer?.fullName }}</p>
          </div>
          <div class="card stat-card stat-accent-blue">
            <p class="stat-label">{{ t('common.type') }}</p>
            <p class="stat-value">
              {{ selectedCustomerLoanDetail.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}
            </p>
          </div>
          <div class="card stat-card stat-accent-green">
            <p class="stat-label">{{ t('common.principal') }}</p>
            <p class="stat-value">{{ formatCurrency(selectedCustomerLoanDetail.principalAmount) }}</p>
          </div>
          <div class="card stat-card stat-accent-amber">
            <p class="stat-label">{{ t('loans.outstanding') }}</p>
            <p class="stat-value">{{ formatCurrency(selectedCustomerLoanDetail.outstandingPrincipal) }}</p>
          </div>
        </div>

        <div class="stats-inline mt-16">
          <span class="pill">{{ t('common.status') }}: {{ t(`common.${selectedCustomerLoanDetail.status}`) }}</span>
          <span class="pill">{{ t('loans.dueDay') }}: {{ selectedCustomerLoanDetail.dueDay }}</span>
          <span class="pill">{{ t('loans.rate') }}: {{ selectedCustomerLoanDetail.monthlyInterestRate }}%</span>
          <span class="pill">{{ t('common.date') }}: {{ formatDateDMY(selectedCustomerLoanDetail.disbursementDate) }}</span>
        </div>

        <div class="mt-16">
          <h3>{{ t('loans.loanPayments') }}</h3>
          <p class="muted" v-if="!selectedCustomerLoanPayments.length">{{ t('loans.noLoanPayments') }}</p>
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
              <tr v-for="payment in selectedCustomerLoanPayments" :key="payment.id">
                <td>#{{ payment.id }}</td>
                <td>{{ formatDateDMY(payment.paymentDate) }}</td>
                <td>{{ formatCurrency(payment.totalAmount) }}</td>
                <td>{{ formatCurrency(payment.allocatedToPenalty) }}</td>
                <td>{{ formatCurrency(payment.allocatedToInterest) }}</td>
                <td>{{ formatCurrency(payment.allocatedToFees) }}</td>
                <td>{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
                <td>{{ paymentMethodLabel(payment.paymentMethod) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-16">
          <h3>{{ t('loans.loanCollateral') }}</h3>
          <p class="muted" v-if="!selectedCustomerLoanCollateral.length">{{ t('loans.noLoanCollateral') }}</p>
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
              <tr v-for="item in selectedCustomerLoanCollateral" :key="item.id">
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

    <div v-if="showLoanEditModal" class="modal-backdrop" @click.self="closeLoanEditModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ t('customers.editLoan') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closeLoanEditModal">{{ t('common.close') }}</button>
        </div>

        <form class="form mt-16" @submit.prevent="handleUpdateLoan">
          <div class="grid grid-2">
            <label>
              {{ t('loans.monthlyInterestRate') }}
              <input v-model.number="loanEditForm.monthlyInterestRate" type="number" min="0" step="0.1" required />
            </label>
            <label>
              {{ t('loans.dueDay') }}
              <input v-model.number="loanEditForm.dueDay" type="number" min="1" max="28" required />
            </label>
            <label>
              {{ t('common.status') }}
              <select v-model="loanEditForm.status" required>
                <option value="active">{{ t('common.active') }}</option>
                <option value="overdue">{{ t('common.overdue') }}</option>
                <option value="closed">{{ t('common.closed') }}</option>
              </select>
            </label>
          </div>
          <button class="btn" type="submit" :disabled="isSaving">
            <Save :size="16" />
            {{ t('customers.saveChanges') }}
          </button>
        </form>
      </div>
    </div>

    <div v-if="showCollateralEditModal" class="modal-backdrop" @click.self="closeCollateralEditModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ t('customers.editCollateral') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closeCollateralEditModal">{{ t('common.close') }}</button>
        </div>

        <form class="form mt-16" @submit.prevent="handleUpdateCollateral">
          <div class="grid grid-2">
            <label>
              {{ t('common.loan') }}
              <select v-model.number="collateralEditForm.loanId" required>
                <option v-for="loan in collateralAssignableLoans" :key="loan.id" :value="loan.id">#{{ loan.id }}</option>
              </select>
            </label>
            <label>
              {{ t('common.description') }}
              <input v-model="collateralEditForm.description" required />
            </label>
            <label>
              {{ t('collateral.appraisedValue') }}
              <input v-model.number="collateralEditForm.appraisedValue" type="number" min="1" required />
            </label>
            <label>
              {{ t('collateral.storageLocation') }}
              <input v-model="collateralEditForm.storageLocation" required />
            </label>
            <label>
              {{ t('common.status') }}
              <select v-model="collateralEditForm.status" required>
                <option value="in-custody">{{ t('common.inCustody') }}</option>
                <option value="released">{{ t('common.released') }}</option>
                <option value="liquidated">{{ t('common.liquidated') }}</option>
              </select>
            </label>
          </div>
          <button class="btn" type="submit" :disabled="isSaving">
            <Save :size="16" />
            {{ t('customers.saveChanges') }}
          </button>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Save, UserPlus, Users } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { apiClient } from '../services/api'
import { useMockPlatformStore } from '../stores/mockPlatformStore'
import type { CollateralItem, Customer, Loan, Payment } from '../types/domain'
import { formatDateDMY } from '../utils/date'

interface InterestPendingItem {
  interest_charge_id: number
  loan_id: number
  billing_period: string
  due_date: string
  remaining_pending_amount: number
  penalty_amount: number
  current_outstanding_balance: number
  overdue: boolean
}

interface InterestPendingGroup {
  items: InterestPendingItem[]
}

interface InterestPendingResponse {
  groups: InterestPendingGroup[]
  total_pending_interest: number
  total_pending_penalty: number
  total_outstanding: number
  available_advance_balance: number
}

interface PrincipalContextItem {
  outstanding_principal: number
  accrued_unpaid_interest: number
}

interface PrincipalContextResponse {
  items: PrincipalContextItem[]
}

interface PaymentEvent {
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
}

const { state, createCustomer, updateCustomer, updateLoan, updateCollateral, getCustomerById, ensureInitialized } =
  useMockPlatformStore()
const { t, locale } = useI18n()
const currencyCode = computed(() => state.globalSettings?.currencyCode ?? 'COP')
const message = ref('')
const search = ref('')
const selectedCustomerId = ref<number | null>(null)
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const showCustomerLoanDetailModal = ref(false)
const showLoanEditModal = ref(false)
const showCollateralEditModal = ref(false)
const isSaving = ref(false)
const financialDataLoading = ref(false)
const financialDataError = ref(false)
const pendingInterestData = ref<InterestPendingResponse | null>(null)
const principalContextData = ref<PrincipalContextResponse | null>(null)
const paymentEvents = ref<PaymentEvent[]>([])
const selectedLoanForEditId = ref<number | null>(null)
const selectedLoanDetailId = ref<number | null>(null)
const selectedCollateralForEditId = ref<number | null>(null)

onMounted(async () => {
  await ensureInitialized()
})

const form = reactive({
  fullName: '',
  documentType: 'ID',
  documentNumber: '',
  phone: '',
  city: ''
})

const editForm = reactive({
  fullName: '',
  phone: '',
  email: '',
  address: '',
  city: '',
  status: 'active' as 'active' | 'archived'
})

const loanEditForm = reactive({
  monthlyInterestRate: 0,
  dueDay: 1,
  status: 'active' as 'active' | 'overdue' | 'closed'
})

const collateralEditForm = reactive({
  loanId: 0,
  description: '',
  appraisedValue: 0,
  storageLocation: '',
  status: 'in-custody' as 'in-custody' | 'released' | 'liquidated'
})

const selectedCustomer = computed(() =>
  selectedCustomerId.value === null ? null : getCustomerById(selectedCustomerId.value)
)

const selectedCustomerLoans = computed(() => {
  if (!selectedCustomer.value) {
    return []
  }

  return state.loans
    .filter((loan: Loan) => loan.customerId === selectedCustomer.value?.id)
    .sort((a, b) => new Date(b.disbursementDate).getTime() - new Date(a.disbursementDate).getTime())
})

const selectedCustomerLoanIds = computed(() => new Set(selectedCustomerLoans.value.map((loan: Loan) => loan.id)))

const selectedCustomerPayments = computed(() =>
  state.payments.filter((payment: Payment) => selectedCustomerLoanIds.value.has(payment.loanId))
)

const selectedCustomerCollateral = computed(() =>
  state.collateralItems.filter((item: CollateralItem) => selectedCustomerLoanIds.value.has(item.loanId))
)

const selectedCustomerLoanDetail = computed(() => {
  if (selectedLoanDetailId.value === null) {
    return null
  }

  return selectedCustomerLoans.value.find((loan: Loan) => loan.id === selectedLoanDetailId.value) ?? null
})

const selectedCustomerLoanPayments = computed(() => {
  if (!selectedCustomerLoanDetail.value) {
    return []
  }

  return selectedCustomerPayments.value
    .filter((payment: Payment) => payment.loanId === selectedCustomerLoanDetail.value?.id)
    .sort((a, b) => new Date(b.paymentDate).getTime() - new Date(a.paymentDate).getTime())
})

const selectedCustomerLoanCollateral = computed(() => {
  if (!selectedCustomerLoanDetail.value) {
    return []
  }

  return selectedCustomerCollateral.value.filter((item: CollateralItem) => item.loanId === selectedCustomerLoanDetail.value?.id)
})

const collateralAssignableLoans = computed(() =>
  selectedCustomerLoans.value.filter((loan: Loan) => loan.loanType === 'pawn' && loan.status !== 'closed')
)

const pendingInterestItems = computed(() => pendingInterestData.value?.groups.flatMap((group) => group.items) ?? [])

const totalPendingInterest = computed(() => pendingInterestData.value?.total_pending_interest ?? 0)
const totalPendingPenalty = computed(() => pendingInterestData.value?.total_pending_penalty ?? 0)
const totalPendingOutstanding = computed(() => pendingInterestData.value?.total_outstanding ?? 0)
const availableAdvanceBalance = computed(() => pendingInterestData.value?.available_advance_balance ?? 0)

const totalOutstandingPrincipal = computed(() =>
  (principalContextData.value?.items ?? []).reduce((sum, loan) => sum + loan.outstanding_principal, 0)
)

const totalAccruedUnpaidInterest = computed(() =>
  (principalContextData.value?.items ?? []).reduce((sum, loan) => sum + loan.accrued_unpaid_interest, 0)
)

const totalCustomerPaid = computed(() =>
  selectedCustomerPayments.value.reduce((sum: number, payment: Payment) => sum + payment.totalAmount, 0)
)

const firstLoanDisbursementDate = computed(() => {
  if (!selectedCustomerLoans.value.length) {
    return ''
  }

  return [...selectedCustomerLoans.value]
    .sort((a, b) => new Date(a.disbursementDate).getTime() - new Date(b.disbursementDate).getTime())[0]
    .disbursementDate
})

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    style: 'currency',
    currency: currencyCode.value
  }).format(
    amount
  )

const syncEditForm = () => {
  if (!selectedCustomer.value) {
    return
  }

  editForm.fullName = selectedCustomer.value.fullName
  editForm.phone = selectedCustomer.value.phone
  editForm.email = selectedCustomer.value.email
  editForm.address = selectedCustomer.value.address
  editForm.city = selectedCustomer.value.city
  editForm.status = selectedCustomer.value.status
}

const selectCustomer = (customerId: number) => {
  selectedCustomerId.value = customerId
  syncEditForm()
  void loadCustomerFinancialData(customerId)
}

const openCreateModal = () => {
  showCreateModal.value = true
}

const closeCreateModal = () => {
  showCreateModal.value = false
}

const openCustomerDetail = (customerId: number) => {
  selectCustomer(customerId)
  showDetailModal.value = true
}

const closeDetailModal = () => {
  showDetailModal.value = false
}

const openCustomerLoanDetail = (loanId: number) => {
  selectedLoanDetailId.value = loanId
  showCustomerLoanDetailModal.value = true
}

const closeCustomerLoanDetail = () => {
  showCustomerLoanDetailModal.value = false
}

const openLoanEditModal = (loan: Loan) => {
  selectedLoanForEditId.value = loan.id
  loanEditForm.monthlyInterestRate = loan.monthlyInterestRate
  loanEditForm.dueDay = loan.dueDay
  loanEditForm.status = loan.status
  showLoanEditModal.value = true
}

const closeLoanEditModal = () => {
  showLoanEditModal.value = false
}

const openCollateralEditModal = (item: CollateralItem) => {
  selectedCollateralForEditId.value = item.id
  collateralEditForm.loanId = item.loanId
  collateralEditForm.description = item.description
  collateralEditForm.appraisedValue = item.appraisedValue
  collateralEditForm.storageLocation = item.storageLocation
  collateralEditForm.status = item.status
  showCollateralEditModal.value = true
}

const closeCollateralEditModal = () => {
  showCollateralEditModal.value = false
}

const loadCustomerFinancialData = async (customerId: number) => {
  financialDataLoading.value = true
  financialDataError.value = false

  try {
    const [pending, principal, history] = await Promise.all([
      apiClient.request<InterestPendingResponse>(`/payments/customers/${customerId}/interest-pending`),
      apiClient.request<PrincipalContextResponse>(`/payments/customers/${customerId}/principal-context`),
      apiClient.request<PaymentEvent[]>(`/payments/customers/${customerId}/history`)
    ])

    pendingInterestData.value = pending
    principalContextData.value = principal
    paymentEvents.value = history
  } catch {
    financialDataError.value = true
    pendingInterestData.value = null
    principalContextData.value = null
    paymentEvents.value = []
  } finally {
    financialDataLoading.value = false
  }
}

const handleCreateCustomer = async () => {
  try {
    const result = await createCustomer({ ...form })
    message.value = t(result.messageKey)

    if (result.ok) {
      form.fullName = ''
      form.documentType = 'ID'
      form.documentNumber = ''
      form.phone = ''
      form.city = ''
      closeCreateModal()
    }
  } catch {
    message.value = t('messages.operationFailed')
  }
}

const handleUpdateCustomer = async () => {
  if (!selectedCustomer.value || isSaving.value) {
    return
  }

  isSaving.value = true
  try {
    const result = await updateCustomer({
      id: selectedCustomer.value.id,
      fullName: editForm.fullName,
      phone: editForm.phone,
      email: editForm.email,
      address: editForm.address,
      city: editForm.city,
      status: editForm.status
    })

    message.value = t(result.messageKey)
    if (result.ok) {
      syncEditForm()
    }
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    isSaving.value = false
  }
}

const handleUpdateLoan = async () => {
  if (selectedLoanForEditId.value === null || isSaving.value) {
    return
  }

  isSaving.value = true
  try {
    const result = await updateLoan({
      id: selectedLoanForEditId.value,
      monthlyInterestRate: loanEditForm.monthlyInterestRate,
      dueDay: loanEditForm.dueDay,
      status: loanEditForm.status
    })

    message.value = t(result.messageKey)
    closeLoanEditModal()
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    isSaving.value = false
  }
}

const handleUpdateCollateral = async () => {
  if (selectedCollateralForEditId.value === null || isSaving.value) {
    return
  }

  isSaving.value = true
  try {
    const result = await updateCollateral({
      id: selectedCollateralForEditId.value,
      loanId: collateralEditForm.loanId,
      description: collateralEditForm.description,
      appraisedValue: collateralEditForm.appraisedValue,
      storageLocation: collateralEditForm.storageLocation,
      status: collateralEditForm.status
    })

    message.value = t(result.messageKey)
    closeCollateralEditModal()
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    isSaving.value = false
  }
}

const getLoanById = (loanId: number) => selectedCustomerLoans.value.find((loan) => loan.id === loanId) ?? null

const getLoanTypeLabel = (loanId: number) => {
  const loan = getLoanById(loanId)
  if (!loan) {
    return '-'
  }
  return loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal')
}

const getLoanStatusLabel = (loanId: number) => {
  const loan = getLoanById(loanId)
  if (!loan) {
    return '-'
  }
  return t(`common.${loan.status}`)
}

const paymentMethodLabel = (method: string) => {
  if (method === 'cash') {
    return t('common.cash')
  }
  if (method === 'bank-transfer') {
    return t('common.bankTransfer')
  }
  return t('common.other')
}

const paymentTypeLabel = (paymentType: string) => {
  if (paymentType === 'interest') {
    return t('payments.interestTab')
  }
  if (paymentType === 'principal') {
    return t('payments.principalTab')
  }
  if (paymentType === 'advance') {
    return t('customers.advancePayment')
  }
  return paymentType
}

const filteredCustomers = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) {
    return state.customers
  }

  return state.customers.filter((customer: Customer) =>
    [customer.fullName, customer.documentNumber, customer.phone, customer.city].some((value) =>
      value.toLowerCase().includes(query)
    )
  )
})
</script>
