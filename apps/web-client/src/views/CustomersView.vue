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
        <select v-model="customerStatusFilter" class="table-select">
          <option value="all">{{ t('loans.allStatuses') }}</option>
          <option value="active">{{ t('common.active') }}</option>
          <option value="archived">{{ t('common.archived') }}</option>
        </select>
        <span class="table-count">{{ t('customers.totalRecords', { count: filteredCustomers.length }) }}</span>
      </div>
      <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleCustomerSort('id')">
                {{ t('common.id') }}
                <span v-if="getCustomerSortBadge('id')" class="sort-indicator">
                  {{ getCustomerSortBadge('id') }}
                </span>
              </button>
            </th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleCustomerSort('name')">
                {{ t('common.name') }}
                <span v-if="getCustomerSortBadge('name')" class="sort-indicator">
                  {{ getCustomerSortBadge('name') }}
                </span>
              </button>
            </th>
            <th>{{ t('customers.document') }}</th>
            <th>{{ t('common.phone') }}</th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleCustomerSort('city')">
                {{ t('common.city') }}
                <span v-if="getCustomerSortBadge('city')" class="sort-indicator">
                  {{ getCustomerSortBadge('city') }}
                </span>
              </button>
            </th>
            <th>
              <button class="sort-header-btn" type="button" @click="toggleCustomerSort('status')">
                {{ t('common.status') }}
                <span v-if="getCustomerSortBadge('status')" class="sort-indicator">
                  {{ getCustomerSortBadge('status') }}
                </span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="customer in filteredCustomers" :key="customer.id" class="clickable-row" @click="openCustomerDetail(customer.id)">
            <td>{{ customer.id }}</td>
            <td>{{ customer.fullName }}</td>
            <td>{{ customer.documentType }} / {{ customer.documentNumber }}</td>
            <td>{{ customer.phone }}</td>
            <td>{{ customer.city }}</td>
            <td>{{ customer.status === 'active' ? t('common.active') : t('common.archived') }}</td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <div v-if="showCreateModal" class="modal-backdrop" @click.self="closeCreateModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ t('customers.createCustomer') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closeCreateModal">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
        </div>

        <form class="form mt-16" @submit.prevent="handleCreateCustomer">
          <div class="grid grid-2">
            <label>
              {{ t('customers.fullName') }}
              <input v-model="form.fullName" required />
            </label>
            <label>
              {{ t('customers.documentType') }}
              <select v-model="form.documentType" required>
                <option v-for="option in documentTypeOptions" :key="option" :value="option">{{ option }}</option>
              </select>
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
          <div class="form-inline">
            <button
              v-if="selectedCustomer.status === 'active'"
              class="btn btn-secondary"
              type="button"
              :disabled="isSaving"
              @click="handleArchiveCustomer"
            >
              <Archive :size="16" />
              {{ t('customers.archiveCustomer') }}
            </button>
            <button
              v-else
              class="btn btn-secondary"
              type="button"
              :disabled="isSaving"
              @click="handleActivateCustomer"
            >
              <CheckCircle2 :size="16" />
              {{ t('customers.activateCustomer') }}
            </button>
            <button class="btn btn-secondary" type="button" :disabled="isSaving" @click="handleDeleteCustomer">
              <Trash2 :size="16" />
              {{ t('customers.deleteCustomer') }}
            </button>
            <button class="btn btn-secondary" type="button" @click="closeDetailModal">
              <X :size="16" />
              {{ t('common.close') }}
            </button>
          </div>
        </div>

        <div class="customer-header mt-16">
          <div>
            <h3 class="customer-title">{{ selectedCustomer.fullName }}</h3>
            <p class="muted">{{ selectedCustomer.documentType }} / {{ selectedCustomer.documentNumber }} · #{{ selectedCustomer.id }}</p>
          </div>
          <span class="pill" :class="selectedCustomer.status === 'active' ? 'pill-current' : 'pill-overdue'">
            {{ selectedCustomer.status === 'active' ? t('common.active') : t('common.archived') }}
          </span>
        </div>

        <p v-if="hasCustomerCreditTraceability" class="notice mt-16" style="background: var(--warning-soft); color: #92400e; border-color: var(--warning-border);">{{ t('customers.traceabilityDeleteHint') }}</p>

        <!-- ── Tabs ──────────────────────────────────── -->
        <div class="detail-tabs mt-16">
          <button class="tab-btn" :class="{ active: detailTab === 'overview' }" type="button" @click="detailTab = 'overview'">
            <LayoutDashboard :size="14" />
            {{ t('customers.tabOverview') }}
          </button>
          <button class="tab-btn" :class="{ active: detailTab === 'loans' }" type="button" @click="detailTab = 'loans'">
            <HandCoins :size="14" />
            {{ t('customers.tabLoans') }}
            <span v-if="selectedCustomerLoans.length" class="tab-count">{{ selectedCustomerLoans.length }}</span>
          </button>
          <button class="tab-btn" :class="{ active: detailTab === 'payments' }" type="button" @click="detailTab = 'payments'">
            <Wallet :size="14" />
            {{ t('customers.tabPayments') }}
            <span v-if="selectedCustomerPayments.length" class="tab-count">{{ selectedCustomerPayments.length }}</span>
          </button>
          <button class="tab-btn" :class="{ active: detailTab === 'collateral' }" type="button" @click="detailTab = 'collateral'">
            <Package :size="14" />
            {{ t('customers.tabCollateral') }}
            <span v-if="selectedCustomerCollateral.length" class="tab-count">{{ selectedCustomerCollateral.length }}</span>
          </button>
          <button class="tab-btn" :class="{ active: detailTab === 'edit' }" type="button" @click="detailTab = 'edit'">
            <Pencil :size="14" />
            {{ t('customers.tabEdit') }}
          </button>
        </div>

        <!-- ── Tab: Overview ────────────────────────── -->
        <template v-if="detailTab === 'overview'">
        <article class="card mt-16">
          <h3>{{ t('customers.globalAuditFiltersTitle') }}</h3>
          <p class="muted">{{ t('customers.globalAuditFiltersHint') }}</p>
          <div class="audit-filter-grid mt-16">
            <label>
              {{ t('customers.auditFilterFrom') }}
              <DateInputField v-model="auditFromDate" :label="t('customers.auditFilterFrom')" :placeholder="t('settings.dateFormat')" />
            </label>
            <label>
              {{ t('customers.auditFilterTo') }}
              <DateInputField v-model="auditToDate" :label="t('customers.auditFilterTo')" :placeholder="t('settings.dateFormat')" />
            </label>
            <label>
              {{ t('customers.auditFilterLoan') }}
              <select v-model="auditLoanFilter">
                <option value="all">{{ t('customers.auditFilterAllLoans') }}</option>
                <option v-for="loanId in loanAuditFilterOptions" :key="loanId" :value="loanId">#{{ loanId }}</option>
              </select>
            </label>
            <button class="btn btn-secondary" type="button" @click="resetAuditFilters">
              <FilterX :size="16" />
              {{ t('customers.auditResetFilters') }}
            </button>
          </div>
        </article>

        <div class="grid grid-2 mt-16">
          <article class="card audit-summary-card">
            <h3>{{ t('customers.auditSnapshotTitle') }}</h3>
            <p class="muted">{{ t('customers.auditSnapshotHint') }}</p>
            <div class="audit-metrics mt-16">
              <div class="audit-metric-item">
                <p class="audit-metric-label">{{ t('customers.totalLoansLabel') }}</p>
                <p class="audit-metric-value">{{ totalCustomerLoans }}</p>
              </div>
              <div class="audit-metric-item">
                <p class="audit-metric-label">{{ t('customers.activeLoansLabel') }}</p>
                <p class="audit-metric-value">{{ activeCustomerLoans }}</p>
              </div>
              <div class="audit-metric-item">
                <p class="audit-metric-label">{{ t('customers.overdueLoansLabel') }}</p>
                <p class="audit-metric-value">{{ overdueCustomerLoans }}</p>
              </div>
              <div class="audit-metric-item">
                <p class="audit-metric-label">{{ t('payments.historyTitle') }}</p>
                <p class="audit-metric-value">{{ auditFilteredEvents.length }}</p>
              </div>
            </div>
            <div class="stats-inline mt-16">
              <span class="pill">{{ t('customers.lastPaymentAt', { date: formatDateTime(lastPaymentEventDate) }) }}</span>
              <span class="pill">{{ t('customers.lastPaymentAmount', { amount: formatCurrency(lastPaymentEventAmount) }) }}</span>
            </div>
          </article>

          <article class="card audit-trace-card">
            <h3>{{ t('customers.quickTraceabilityTitle') }}</h3>
            <p class="muted">{{ t('customers.quickTraceabilityHint') }}</p>
            <ul class="audit-timeline mt-16">
              <li v-for="event in quickTraceabilityEvents" :key="`quick-${event.id}`" class="audit-timeline-item">
                <div>
                  <p class="audit-timeline-title">#{{ event.loan_id }} · {{ paymentTypeLabel(event.payment_type) }}</p>
                  <p class="muted">{{ formatDateTime(event.payment_date) }}</p>
                </div>
                <span class="pill">{{ formatCurrency(event.total_entered_amount) }}</span>
              </li>
              <li v-if="!quickTraceabilityEvents.length" class="muted">{{ t('customers.noPaymentEvents') }}</li>
            </ul>
          </article>
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
        </template>

        <!-- ── Tab: Edit ─────────────────────────── -->
        <template v-if="detailTab === 'edit'">
        <form class="form mt-16" @submit.prevent="handleUpdateCustomer">
          <div class="grid grid-3">
            <label>
              {{ t('customers.fullName') }}
              <input v-model="editForm.fullName" required />
            </label>
            <label>
              {{ t('customers.documentType') }}
              <select v-model="editForm.documentType" required>
                <option v-for="option in editDocumentTypeOptions" :key="option" :value="option">{{ option }}</option>
              </select>
            </label>
            <label>
              {{ t('customers.documentNumber') }}
              <input v-model="editForm.documentNumber" required />
            </label>
            <label>
              {{ t('common.status') }}
              <select v-model="editForm.status" required>
                <option value="active">{{ t('common.active') }}</option>
                <option value="archived">{{ t('common.archived') }}</option>
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
        </template>

        <!-- ── Tab: Payments ──────────────────────── -->
        <template v-if="detailTab === 'payments'">
        <div class="mt-16">
          <h3>{{ t('customers.paymentBehavior') }}</h3>
          <p class="muted">{{ t('customers.paymentBehaviorHint') }}</p>
          <p v-if="financialDataLoading" class="muted mt-16">{{ t('customers.loadingFinancialData') }}</p>
          <p v-else-if="financialDataError" class="muted mt-16">{{ t('customers.financialDataUnavailable') }}</p>

          <div v-else class="table-wrap mt-16">
          <table>
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
                  <span class="pill" :class="getPendingStatusClass(item)">
                    {{ t(getPendingStatusKey(item)) }}
                  </span>
                </td>
              </tr>
              <tr v-if="!pendingInterestItems.length">
                <td colspan="7">{{ t('customers.noPendingInterestDetail') }}</td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>

        <div class="mt-16">
          <h3>{{ t('customers.customerPaymentTraceability') }}</h3>
          <p class="muted" v-if="!auditFilteredEvents.length">{{ t('customers.noPaymentEvents') }}</p>
          <div v-else class="table-wrap mt-16">
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
              <tr v-for="event in auditFilteredEvents" :key="event.id">
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
        </div>
        </template>

        <!-- ── Tab: Loans ─────────────────────────── -->
        <template v-if="detailTab === 'loans'">
        <div class="mt-16">
          <h3>{{ t('customers.customerLoans') }}</h3>
          <p class="muted" v-if="!selectedCustomerLoans.length">{{ t('customers.noLoans') }}</p>
          <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.id') }}</th>
                <th>{{ t('common.type') }}</th>
                <th>{{ t('customers.loanDisbursementDate') }}</th>
                <th :title="t('loans.graceDaysHelp')">{{ t('loans.dueDay') }}</th>
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
                    <Pencil :size="16" />
                    {{ t('customers.editLoan') }}
                  </button>
                  <button class="btn btn-secondary" type="button" :disabled="isSaving" @click.stop="handleDeleteLoan(loan.id)">
                    <Trash2 :size="16" />
                    {{ t('customers.deleteLoan') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
        </template>

        <!-- ── Tab: Payments (customer payments) continues ── -->
        <template v-if="detailTab === 'payments'">
        <div class="mt-16">
          <h3>{{ t('customers.customerPayments') }}</h3>
          <p class="muted">{{ t('customers.totalPaid', { amount: formatCurrency(totalCustomerPaid) }) }}</p>
          <p class="muted" v-if="!selectedCustomerPayments.length">{{ t('customers.noPayments') }}</p>
          <div v-else class="table-wrap mt-16">
          <table>
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
                <td>{{ formatCurrency(payment.allocatedToPenalty) }}</td>
                <td>{{ formatCurrency(payment.allocatedToInterest) }}</td>
                <td>{{ formatCurrency(payment.allocatedToFees) }}</td>
                <td>{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
                <td>
                  {{ paymentMethodLabel(payment.paymentMethod) }}
                </td>
                <td>{{ payment.isReversed ? t('payments.reversed') : t('common.active') }}</td>
                <td>
                  <button
                    class="btn btn-secondary"
                    type="button"
                    :disabled="payment.isReversed || isSaving"
                    @click="openPaymentEditModal(payment)"
                  >
                    <Pencil :size="16" />
                    {{ t('payments.editPayment') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
        </template>

        <!-- ── Tab: Collateral ─────────────────────── -->
        <template v-if="detailTab === 'collateral'">
        <div class="mt-16">
          <h3>{{ t('customers.customerCollateral') }}</h3>
          <p class="muted" v-if="!selectedCustomerCollateral.length">{{ t('customers.noCollateral') }}</p>
          <div v-else class="table-wrap">
          <table>
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
                    <Pencil :size="16" />
                    {{ t('customers.editCollateral') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
        </template>
      </div>
    </div>

    <div v-if="showCustomerLoanDetailModal && selectedCustomerLoanDetail" class="modal-backdrop" @click.self="closeCustomerLoanDetail">
      <div class="modal-panel card modal-panel-lg">
        <div class="modal-header">
          <h3>{{ t('loans.loanDetail') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closeCustomerLoanDetail">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
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
          <span class="pill" :title="t('loans.graceDaysHelp')">{{ t('loans.dueDay') }}: {{ selectedCustomerLoanDetail.dueDay }}</span>
          <span class="pill">{{ t('loans.rate') }}: {{ selectedCustomerLoanDetail.monthlyInterestRate }}%</span>
          <span class="pill">{{ t('common.date') }}: {{ formatDateDMY(selectedCustomerLoanDetail.disbursementDate) }}</span>
        </div>

        <div class="mt-16 stats-inline">
          <span class="muted"><strong>{{ t('loans.description') }}:</strong> {{ selectedCustomerLoanDetail.description || t('loans.noDescription') }}</span>
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
          <button class="btn btn-secondary" type="button" @click="closeLoanEditModal">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
        </div>

        <form class="form mt-16" @submit.prevent="handleUpdateLoan">
          <div class="grid grid-2">
            <label>
              {{ t('loans.loanType') }}
              <select v-model="loanEditForm.loanType" required>
                <option value="pawn">{{ t('common.pawn') }}</option>
                <option value="personal">{{ t('common.personal') }}</option>
              </select>
            </label>
            <label>
              {{ t('loans.principalAmount') }}
              <input v-model.number="loanEditForm.principalAmount" type="number" min="1" required />
            </label>
            <label>
              {{ t('loans.outstanding') }}
              <input v-model.number="loanEditForm.outstandingPrincipal" type="number" min="0" required />
            </label>
            <label>
              {{ t('loans.monthlyInterestRate') }}
              <input v-model.number="loanEditForm.monthlyInterestRate" type="number" min="0" step="0.1" required />
            </label>
            <label>
              {{ t('loans.latePenaltyRate') }}
              <input v-model.number="loanEditForm.latePenaltyRate" type="number" min="0" step="0.1" required />
            </label>
            <label>
              {{ t('loans.disbursementDate') }}
              <DateInputField
                v-model="loanEditForm.disbursementDate"
                :label="t('loans.disbursementDate')"
                :placeholder="t('settings.dateFormat')"
                :required="true"
              />
            </label>
            <label :title="t('loans.graceDaysHelp')">
              {{ t('loans.dueDay') }}
              <input
                v-model.number="loanEditForm.dueDay"
                type="number"
                min="0"
                max="60"
                required
                :title="t('loans.graceDaysHelp')"
              />
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
          <label class="mt-8">
            {{ t('loans.description') }}
            <textarea v-model="loanEditForm.description" rows="3" :placeholder="t('loans.descriptionPlaceholder')" />
          </label>
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
          <button class="btn btn-secondary" type="button" @click="closeCollateralEditModal">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
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

    <div v-if="showPaymentEditModal" class="modal-backdrop" @click.self="closePaymentEditModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ t('payments.editPayment') }}</h3>
          <button class="btn btn-secondary" type="button" @click="closePaymentEditModal">
            <X :size="16" />
            {{ t('common.close') }}
          </button>
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { Archive, CheckCircle2, FilterX, HandCoins, LayoutDashboard, Package, Pencil, Save, Trash2, UserPlus, Users, Wallet, X } from 'lucide-vue-next'
import DateInputField from '../components/DateInputField.vue'
import PageHeader from '../components/PageHeader.vue'
import { apiClient } from '../services/api'
import { usePlatformStore } from '../stores/platformStore'
import type { CollateralItem, Customer, Loan, Payment } from '../types/domain'
import { formatDateDMY, toIsoDate } from '../utils/date'

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

type SortDirection = 'asc' | 'desc'
type CustomerSortKey = 'name' | 'id' | 'city' | 'status'

interface SortCriterion<T extends string> {
  key: T
  direction: SortDirection
}

const {
  state,
  createCustomer,
  updateCustomer,
  deleteCustomer,
  updateLoan,
  deleteLoan,
  updatePayment,
  updateCollateral,
  getCustomerById,
  ensureInitialized
} =
  usePlatformStore()
const { t, locale } = useI18n()
const route = useRoute()
const currencyCode = computed(() => state.globalSettings?.currencyCode ?? 'COP')
const message = ref('')
const search = ref('')
const customerStatusFilter = ref<'all' | 'active' | 'archived'>('all')
const customerSortPriority = ref<SortCriterion<CustomerSortKey>[]>([{ key: 'name', direction: 'asc' }])
const selectedCustomerId = ref<number | null>(null)
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const showCustomerLoanDetailModal = ref(false)
const showLoanEditModal = ref(false)
const showCollateralEditModal = ref(false)
const showPaymentEditModal = ref(false)
const detailTab = ref<'overview' | 'loans' | 'payments' | 'collateral' | 'edit'>('overview')
const isSaving = ref(false)
const financialDataLoading = ref(false)
const financialDataError = ref(false)
const pendingInterestData = ref<InterestPendingResponse | null>(null)
const principalContextData = ref<PrincipalContextResponse | null>(null)
const paymentEvents = ref<PaymentEvent[]>([])
const auditFromDate = ref('')
const auditToDate = ref('')
const auditLoanFilter = ref('all')
const selectedLoanForEditId = ref<number | null>(null)
const selectedLoanDetailId = ref<number | null>(null)
const selectedCollateralForEditId = ref<number | null>(null)
const selectedPaymentForEditId = ref<number | null>(null)
const documentTypeOptions = ['CC', 'TI', 'NIT', 'CE', 'PAS']
const editDocumentTypeOptions = computed(() => {
  if (!editForm.documentType || documentTypeOptions.includes(editForm.documentType)) {
    return documentTypeOptions
  }

  return [editForm.documentType, ...documentTypeOptions]
})

onMounted(async () => {
  await ensureInitialized()
})

watch(
  () => route.query.q,
  (value) => {
    search.value = typeof value === 'string' ? value : ''
  },
  { immediate: true }
)

const form = reactive({
  fullName: '',
  documentType: 'CC',
  documentNumber: '',
  phone: '',
  city: ''
})

const editForm = reactive({
  fullName: '',
  documentType: 'CC',
  documentNumber: '',
  phone: '',
  email: '',
  address: '',
  city: '',
  status: 'active' as 'active' | 'archived'
})

const loanEditForm = reactive({
  loanType: 'pawn' as 'pawn' | 'personal',
  description: '',
  principalAmount: 0,
  outstandingPrincipal: 0,
  monthlyInterestRate: 0,
  latePenaltyRate: 0,
  disbursementDate: '',
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

const paymentEditForm = reactive({
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
  selectedCustomerId.value === null ? null : getCustomerById(selectedCustomerId.value)
)

const isLoanSelectedByAuditFilter = (loanId: number) => {
  return auditLoanFilter.value === 'all' || String(loanId) === auditLoanFilter.value
}

const isInAuditDateRange = (value: string) => {
  const fromIso = toIsoDate(auditFromDate.value)
  const toIso = toIsoDate(auditToDate.value)
  const valueIso = normalizeToIsoDate(value)
  if (!valueIso) {
    return false
  }

  if (fromIso && valueIso < fromIso) {
    return false
  }

  if (toIso && valueIso > toIso) {
    return false
  }

  return true
}

const allSelectedCustomerLoans = computed(() => {
  if (!selectedCustomer.value) {
    return []
  }

  return state.loans
    .filter((loan: Loan) => loan.customerId === selectedCustomer.value?.id)
    .sort((a, b) => new Date(b.disbursementDate).getTime() - new Date(a.disbursementDate).getTime())
})

const selectedCustomerLoans = computed(() => {
  return allSelectedCustomerLoans.value.filter(
    (loan: Loan) => isLoanSelectedByAuditFilter(loan.id) && isInAuditDateRange(loan.disbursementDate)
  )
})

const selectedCustomerLoanIds = computed(
  () => new Set(allSelectedCustomerLoans.value.filter((loan: Loan) => isLoanSelectedByAuditFilter(loan.id)).map((loan) => loan.id))
)
const hasCustomerCreditTraceability = computed(() => allSelectedCustomerLoans.value.length > 0)

const selectedCustomerPayments = computed(() =>
  state.payments.filter((payment: Payment) => selectedCustomerLoanIds.value.has(payment.loanId) && isInAuditDateRange(payment.paymentDate))
)

const selectedCustomerCollateral = computed(() =>
  state.collateralItems.filter((item: CollateralItem) => selectedCustomerLoanIds.value.has(item.loanId))
)

const selectedCustomerLoanDetail = computed(() => {
  if (selectedLoanDetailId.value === null) {
    return null
  }

  return allSelectedCustomerLoans.value.find((loan: Loan) => loan.id === selectedLoanDetailId.value) ?? null
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
  allSelectedCustomerLoans.value.filter((loan: Loan) => loan.loanType === 'pawn' && loan.status !== 'closed')
)

const pendingInterestItems = computed(() => {
  const allItems = pendingInterestData.value?.groups.flatMap((group) => group.items) ?? []
  return allItems.filter((item) => isLoanSelectedByAuditFilter(item.loan_id) && isInAuditDateRange(item.due_date))
})

const totalPendingInterest = computed(() => pendingInterestItems.value.reduce((sum, item) => sum + item.remaining_pending_amount, 0))
const totalPendingPenalty = computed(() => pendingInterestItems.value.reduce((sum, item) => sum + item.penalty_amount, 0))
const totalPendingOutstanding = computed(() => pendingInterestItems.value.reduce((sum, item) => sum + item.current_outstanding_balance, 0))
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

const totalCustomerLoans = computed(() => selectedCustomerLoans.value.length)
const activeCustomerLoans = computed(() => selectedCustomerLoans.value.filter((loan) => loan.status === 'active').length)
const overdueCustomerLoans = computed(() => selectedCustomerLoans.value.filter((loan) => loan.status === 'overdue').length)

const normalizeToIsoDate = (value: string) => {
  const directMatch = value.match(/^(\d{4}-\d{2}-\d{2})/)
  if (directMatch) {
    return directMatch[1]
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  return parsed.toISOString().slice(0, 10)
}

const auditFilteredEvents = computed(() =>
  paymentEvents.value.filter((event) => isLoanSelectedByAuditFilter(event.loan_id) && isInAuditDateRange(event.payment_date))
)

const loanAuditFilterOptions = computed(() => {
  return [...allSelectedCustomerLoans.value]
    .map((loan) => String(loan.id))
    .sort((a, b) => Number(a) - Number(b))
})

const lastPaymentEventDate = computed(() => {
  return [...auditFilteredEvents.value].sort((a, b) => new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime())[0]?.payment_date ?? ''
})

const lastPaymentEventAmount = computed(() => {
  return [...auditFilteredEvents.value].sort((a, b) => new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime())[0]?.total_entered_amount ?? 0
})

const quickTraceabilityEvents = computed(() => {
  return [...auditFilteredEvents.value]
    .sort((a, b) => new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime())
    .slice(0, 6)
})

const resetAuditFilters = () => {
  auditFromDate.value = ''
  auditToDate.value = ''
  auditLoanFilter.value = 'all'
}

const firstLoanDisbursementDate = computed(() => {
  if (!allSelectedCustomerLoans.value.length) {
    return ''
  }

  return [...allSelectedCustomerLoans.value]
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

const formatDateTime = (value: string) => {
  if (!value) {
    return '-'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return '-'
  }

  return new Intl.DateTimeFormat(locale.value === 'es' ? 'es-CO' : 'en-US', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(parsed)
}

const syncEditForm = () => {
  if (!selectedCustomer.value) {
    return
  }

  editForm.fullName = selectedCustomer.value.fullName
  editForm.documentType = selectedCustomer.value.documentType || 'CC'
  editForm.documentNumber = selectedCustomer.value.documentNumber
  editForm.phone = selectedCustomer.value.phone
  editForm.email = selectedCustomer.value.email
  editForm.address = selectedCustomer.value.address
  editForm.city = selectedCustomer.value.city
  editForm.status = selectedCustomer.value.status
}

const selectCustomer = (customerId: number) => {
  selectedCustomerId.value = customerId
  resetAuditFilters()
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
  detailTab.value = 'overview'
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
  loanEditForm.loanType = loan.loanType
  loanEditForm.description = loan.description
  loanEditForm.principalAmount = loan.principalAmount
  loanEditForm.outstandingPrincipal = loan.outstandingPrincipal
  loanEditForm.monthlyInterestRate = loan.monthlyInterestRate
  loanEditForm.latePenaltyRate = loan.latePenaltyRate
  loanEditForm.disbursementDate = formatDateDMY(loan.disbursementDate)
  loanEditForm.dueDay = loan.dueDay
  loanEditForm.status = loan.status
  showLoanEditModal.value = true
}

const closeLoanEditModal = () => {
  selectedLoanForEditId.value = null
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

const openPaymentEditModal = (payment: Payment) => {
  selectedPaymentForEditId.value = payment.id
  paymentEditForm.paymentDate = formatDateDMY(payment.paymentDate)
  paymentEditForm.totalAmount = payment.totalAmount
  paymentEditForm.allocatedToPenalty = payment.allocatedToPenalty
  paymentEditForm.allocatedToInterest = payment.allocatedToInterest
  paymentEditForm.allocatedToFees = payment.allocatedToFees
  paymentEditForm.allocatedToPrincipal = payment.allocatedToPrincipal
  paymentEditForm.paymentMethod = payment.paymentMethod
  paymentEditForm.notes = payment.notes
  showPaymentEditModal.value = true
}

const closePaymentEditModal = () => {
  showPaymentEditModal.value = false
  selectedPaymentForEditId.value = null
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
      form.documentType = 'CC'
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
      documentType: editForm.documentType,
      documentNumber: editForm.documentNumber,
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

const updateSelectedCustomerStatus = async (statusValue: 'active' | 'archived') => {
  if (!selectedCustomer.value || isSaving.value) {
    return
  }

  isSaving.value = true
  try {
    const result = await updateCustomer({
      id: selectedCustomer.value.id,
      fullName: editForm.fullName,
      documentType: editForm.documentType,
      documentNumber: editForm.documentNumber,
      phone: editForm.phone,
      email: editForm.email,
      address: editForm.address,
      city: editForm.city,
      status: statusValue
    })

    message.value = t(result.messageKey)
    if (result.ok) {
      editForm.status = statusValue
      syncEditForm()
    }
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    isSaving.value = false
  }
}

const handleArchiveCustomer = async () => {
  if (!selectedCustomer.value) {
    return
  }

  const confirmed = window.confirm(t('customers.archiveCustomerConfirm'))
  if (!confirmed) {
    return
  }

  await updateSelectedCustomerStatus('archived')
}

const handleActivateCustomer = async () => {
  if (!selectedCustomer.value) {
    return
  }

  const confirmed = window.confirm(t('customers.activateCustomerConfirm'))
  if (!confirmed) {
    return
  }

  await updateSelectedCustomerStatus('active')
}

const handleDeleteCustomer = async () => {
  if (!selectedCustomer.value || isSaving.value) {
    return
  }

  const confirmed = window.confirm(t('customers.deleteCustomerConfirm'))
  if (!confirmed) {
    return
  }

  isSaving.value = true
  try {
    const result = await deleteCustomer(selectedCustomer.value.id)
    message.value = t(result.messageKey)

    if (result.ok) {
      selectedCustomerId.value = null
      closeCustomerLoanDetail()
      closeDetailModal()
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

  if (loanEditForm.outstandingPrincipal > loanEditForm.principalAmount) {
    message.value = t('messages.loanOutstandingExceedsPrincipal')
    return
  }

  const disbursementDate = toIsoDate(loanEditForm.disbursementDate)
  if (!disbursementDate) {
    message.value = t('messages.invalidDateFormat')
    return
  }

  isSaving.value = true
  try {
    const result = await updateLoan({
      id: selectedLoanForEditId.value,
      loanType: loanEditForm.loanType,
      description: loanEditForm.description,
      principalAmount: loanEditForm.principalAmount,
      outstandingPrincipal: loanEditForm.outstandingPrincipal,
      monthlyInterestRate: loanEditForm.monthlyInterestRate,
      latePenaltyRate: loanEditForm.latePenaltyRate,
      disbursementDate,
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

const handleDeleteLoan = async (loanId: number) => {
  if (isSaving.value) {
    return
  }

  const confirmed = window.confirm(t('customers.deleteLoanConfirm'))
  if (!confirmed) {
    return
  }

  isSaving.value = true
  try {
    const result = await deleteLoan(loanId)
    message.value = t(result.messageKey)

    if (result.ok && selectedLoanDetailId.value === loanId) {
      closeCustomerLoanDetail()
    }
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

const handleUpdatePayment = async () => {
  if (selectedPaymentForEditId.value === null || isSaving.value) {
    return
  }

  const paymentDate = toIsoDate(paymentEditForm.paymentDate)
  if (!paymentDate) {
    message.value = t('messages.invalidDateFormat')
    return
  }

  isSaving.value = true
  try {
    const result = await updatePayment({
      id: selectedPaymentForEditId.value,
      paymentDate,
      totalAmount: paymentEditForm.totalAmount,
      allocatedToPenalty: paymentEditForm.allocatedToPenalty,
      allocatedToInterest: paymentEditForm.allocatedToInterest,
      allocatedToFees: paymentEditForm.allocatedToFees,
      allocatedToPrincipal: paymentEditForm.allocatedToPrincipal,
      paymentMethod: paymentEditForm.paymentMethod,
      notes: paymentEditForm.notes
    })

    message.value = t(result.messageKey)
    if (result.ok && selectedCustomer.value) {
      closePaymentEditModal()
      await loadCustomerFinancialData(selectedCustomer.value.id)
    }
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

const getPendingStatusKey = (item: { overdue: boolean; due_date: string }) => {
  if (item.overdue) {
    return 'common.overdue'
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const dueDate = new Date(item.due_date)
  dueDate.setHours(0, 0, 0, 0)

  return dueDate.getTime() === today.getTime() ? 'payments.current' : 'payments.upcoming'
}

const getPendingStatusClass = (item: { overdue: boolean; due_date: string }) => {
  if (item.overdue) {
    return 'pill-overdue'
  }

  return getPendingStatusKey(item) === 'payments.current' ? 'pill-current' : 'pill-upcoming'
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

const getSortDirectionSymbol = (direction: SortDirection) => (direction === 'asc' ? '↑' : '↓')

const getCustomerSortMeta = (key: CustomerSortKey) => {
  const index = customerSortPriority.value.findIndex((item) => item.key === key)
  if (index === -1) {
    return null
  }

  return {
    direction: customerSortPriority.value[index].direction,
    priority: index + 1
  }
}

const getCustomerSortBadge = (key: CustomerSortKey) => {
  const meta = getCustomerSortMeta(key)
  if (!meta) {
    return ''
  }

  return `${getSortDirectionSymbol(meta.direction)}${meta.priority}`
}

const toggleCustomerSort = (key: CustomerSortKey) => {
  const index = customerSortPriority.value.findIndex((item) => item.key === key)

  if (index === -1) {
    customerSortPriority.value = [{ key, direction: 'asc' }, ...customerSortPriority.value]
    return
  }

  const current = customerSortPriority.value[index]
  const next = [...customerSortPriority.value]

  if (current.direction === 'asc') {
    const updated = { key, direction: 'desc' as SortDirection }
    next.splice(index, 1)
    customerSortPriority.value = [updated, ...next]
    return
  }

  next.splice(index, 1)
  customerSortPriority.value = next.length ? next : [{ key: 'name', direction: 'asc' }]
}

const filteredCustomers = computed(() => {
  const query = search.value.trim().toLowerCase()
  const filtered = state.customers.filter((customer: Customer) => {
    const statusMatches = customerStatusFilter.value === 'all' || customer.status === customerStatusFilter.value
    if (!statusMatches) {
      return false
    }

    if (!query) {
      return true
    }

    return [customer.fullName, customer.documentNumber, customer.phone, customer.city].some((value) =>
      value.toLowerCase().includes(query)
    )
  })

  return [...filtered].sort((a, b) => {
    for (const criterion of customerSortPriority.value) {
      let result = 0

      if (criterion.key === 'id') {
        result = a.id - b.id
      } else if (criterion.key === 'city') {
        result = a.city.localeCompare(b.city)
      } else if (criterion.key === 'status') {
        result = a.status.localeCompare(b.status)
      } else {
        result = a.fullName.localeCompare(b.fullName)
      }

      if (result !== 0) {
        return criterion.direction === 'asc' ? result : -result
      }
    }

    return 0
  })
})
</script>
