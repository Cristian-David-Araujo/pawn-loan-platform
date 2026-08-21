<template>
  <section>
    <!-- The list and the detail are two addresses, so only one is on screen at a time. The
         detail used to float over the list in a modal, which is why up to eight backdrops
         could stack: every action inside it had nowhere to go but another layer. -->
    <template v-if="!showDetail">
    <PageHeader :title="t('customers.title')" :subtitle="t('customers.subtitle')">
      <template #icon>
        <Users :size="18" />
      </template>
      <template #actions>
        <button v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])" class="btn" type="button" @click="openCreateModal">
          <UserPlus :size="16" />
          {{ t('customers.createCustomer') }}
        </button>
      </template>
    </PageHeader>

    <p v-if="message" :class="[messageClass, 'mt-16']">{{ message }}</p>

    <div class="card mt-16">
      <div class="table-toolbar">
        <!-- A placeholder is not a label: it is gone the moment the field has a value, and a
             screen reader announces nothing. -->
        <input
          v-model="search"
          class="table-search"
          type="search"
          :placeholder="t('customers.searchPlaceholder')"
          :aria-label="t('customers.searchPlaceholder')"
        />
        <CustomSelect v-model="customerStatusFilter" inputClass="table-select" :options="customerStatusFilterOptions" />
        <span class="table-count">{{ t('customers.totalRecords', { count: filteredCustomers.length }) }}</span>
      </div>
      <!-- This table used to render its six headings over nothing on a fresh installation
           or a search with no match: no empty row, no empty state. -->
      <div v-if="!filteredCustomers.length" class="empty-state">
        <div class="empty-state-icon"><Users :size="22" /></div>
        <p class="empty-state-title">
          {{ search || customerStatusFilter !== 'all' ? t('customers.noMatchesTitle') : t('customers.noneYetTitle') }}
        </p>
        <p class="empty-state-hint">
          {{ search || customerStatusFilter !== 'all' ? t('customers.noMatchesHint') : t('customers.noneYetHint') }}
        </p>
        <button
          v-if="!search && customerStatusFilter === 'all'"
          class="btn"
          type="button"
          @click="openCreateModal"
        >
          <UserPlus :size="16" />
          {{ t('customers.createCustomer') }}
        </button>
      </div>
      <div v-else class="table-wrap">
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
          <tr v-for="customer in paginatedCustomers" :key="customer.id" class="clickable-row" @click="openCustomerDetail(customer.id)">
            <td :data-label="t('common.id')">{{ customer.id }}</td>
            <td :data-label="t('common.name')">{{ customer.fullName }}</td>
            <td :data-label="t('customers.document')">{{ customer.documentType }} / {{ customer.documentNumber }}</td>
            <td :data-label="t('common.phone')">{{ customer.phone }}</td>
            <td :data-label="t('common.city')">{{ customer.city }}</td>
            <td :data-label="t('common.status')">
              <span :class="['pill', customer.status === 'active' ? 'pill-current' : '']">
                {{ customer.status === 'active' ? t('common.active') : t('common.archived') }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <Pagination v-model="customerCurrentPage" :totalItems="filteredCustomers.length" :itemsPerPage="10" />
      </div>
    </div>
    </template>


    <!-- Editing is a mode, not a section. It was the fifth tab, which made it the one edit
         form in the app that did not behave like the others: everything else opens a modal
         from the header and returns you where you were. A tab swapped the whole page for a
         form and left no way back except another tab. -->
    <div v-if="showEditModal && selectedCustomer" class="modal-backdrop" @click.self="showEditModal = false">
      <div class="modal-panel card modal-panel-lg">
        <div class="modal-header">
          <h3>{{ t('customers.tabEdit') }}</h3>
          <button class="btn btn-secondary btn-icon" type="button" :aria-label="t('common.close')" @click="showEditModal = false">
            <X :size="16" />
          </button>
        </div>
        <form class="form mt-16" @submit.prevent="handleUpdateCustomer">
          <div class="grid grid-3">
            <label>
              {{ t('customers.fullName') }}
              <input v-model="editForm.fullName" required />
            </label>
            <label>
              {{ t('customers.documentType') }}
              <CustomSelect v-model="editForm.documentType" :options="formattedDocumentTypeOptions" />
            </label>
            <label>
              {{ t('customers.documentNumber') }}
              <input v-model="editForm.documentNumber" required />
            </label>
            <label>
              {{ t('common.status') }}
              <CustomSelect v-model="editForm.status" :options="customerStatusOptions" />
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
              <CustomSelect v-model="form.documentType" :options="formattedDocumentTypeOptions" />
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

    <div v-if="showDetail && selectedCustomer" class="customer-detail-page">
      <div class="customer-detail-shell">
        <div class="modal-header">
          <h3>
            <!-- Back to the list, not a close button: the list is where this came from and
                 where the browser's own back button goes. -->
            <button class="btn btn-ghost btn-icon" type="button" :aria-label="t('customers.backToList')" @click="closeDetail">
              <ArrowLeft :size="16" />
            </button>
            {{ selectedCustomer.fullName }}
          </h3>
          <div class="form-inline">
            <button
              v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])"
              class="btn btn-secondary"
              type="button"
              @click="openEditModal"
            >
              <Pencil :size="16" />
              {{ t('customers.tabEdit') }}
            </button>
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
            <button v-if="hasRole([UserRole.Administrator])" class="btn btn-destructive" type="button" :disabled="isSaving" @click="handleDeleteCustomer">
              <Trash2 :size="16" />
              {{ t('customers.deleteCustomer') }}
            </button>
            <a :href="'/print/invoice/customer/' + selectedCustomer.id" target="_blank" class="btn btn-secondary">
              <Printer :size="16" />
              {{ t('common.printStatement') }}
            </a>
            <a :href="'/print/invoice/history/' + selectedCustomer.id" target="_blank" class="btn btn-secondary">
              <Printer :size="16" />
              {{ t('common.printHistory') }}
            </a>
          </div>
        </div>

        <!-- No name here: it is the page's title. What this carries is everything else the
             record knows, which had no home before — the phone, the address and the city were
             stored, editable, and shown on no screen at all. The dates stay as pills on the
             overview rather than being repeated here. -->
        <div class="customer-header mt-16">
          <dl class="identity-grid">
            <div>
              <dt>{{ t('customers.documentNumber') }}</dt>
              <dd>{{ selectedCustomer.documentType }} {{ selectedCustomer.documentNumber }}</dd>
            </div>
            <div>
              <dt>{{ t('common.phone') }}</dt>
              <dd>{{ selectedCustomer.phone || '—' }}</dd>
            </div>
            <div>
              <dt>{{ t('customers.email') }}</dt>
              <dd>{{ selectedCustomer.email || '—' }}</dd>
            </div>
            <div>
              <dt>{{ t('customers.address') }}</dt>
              <dd>{{ selectedCustomer.address || '—' }}</dd>
            </div>
            <div>
              <dt>{{ t('common.city') }}</dt>
              <dd>{{ selectedCustomer.city || '—' }}</dd>
            </div>
            <div>
              <dt>{{ t('common.id') }}</dt>
              <dd class="code">#{{ selectedCustomer.id }}</dd>
            </div>
          </dl>
          <span class="pill" :class="selectedCustomer.status === 'active' ? 'pill-current' : 'pill-overdue'">
            {{ selectedCustomer.status === 'active' ? t('common.active') : t('common.archived') }}
          </span>
        </div>

        <CustomerIdentityDocumentPanel
          class="mt-16"
          :customer-id="selectedCustomer.id"
          :can-edit="hasRole([UserRole.Administrator, UserRole.LoanOfficer])"
        />

        <!-- The customer's position, above the tabs and above the fold.
             It sat at the foot of the Resumen tab, starting at y=1177 on an 1100px viewport:
             the four figures that answer "how is this customer doing" were the last thing on
             the page and only on one tab. They describe the customer, not a section, so they
             belong beside the identity and stay put while the tabs change. -->
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

        <!-- Was a `.notice` with an inline style repainting it amber; `.notice-warning` is
             that same tone as a system class. -->
        <p v-if="hasCustomerCreditTraceability" class="notice notice-warning mt-16">{{ t('customers.traceabilityDeleteHint') }}</p>


        <!-- ── Tabs ──────────────────────────────────── -->
        <div class="detail-tabs mt-16">
          <button class="tab-btn" :class="{ active: detailTab === 'overview' }" type="button" @click="goToTab('overview')">
            <LayoutDashboard :size="14" />
            {{ t('customers.tabOverview') }}
          </button>
          <button class="tab-btn" :class="{ active: detailTab === 'loans' }" type="button" @click="goToTab('loans')">
            <HandCoins :size="14" />
            {{ t('customers.tabLoans') }}
            <span v-if="allSelectedCustomerLoans.length" class="tab-count">{{ allSelectedCustomerLoans.length }}</span>
          </button>
          <button class="tab-btn" :class="{ active: detailTab === 'payments' }" type="button" @click="goToTab('payments')">
            <Wallet :size="14" />
            {{ t('customers.tabPayments') }}
            <span v-if="selectedCustomerPayments.length" class="tab-count">{{ selectedCustomerPayments.length }}</span>
          </button>
          <button class="tab-btn" :class="{ active: detailTab === 'collateral' }" type="button" @click="goToTab('collateral')">
            <Package :size="14" />
            {{ t('customers.tabCollateral') }}
            <span v-if="selectedCustomerCollateral.length" class="tab-count">{{ selectedCustomerCollateral.length }}</span>
          </button>
        </div>

        <!-- Below the tabs, not above them: a filter refines the section you chose, so it
             cannot come before the choice. Sitting above, it pushed the first row of every
             tab ~300px down and applied to content that was not on screen yet. -->
        <article class="card mt-16">
          <h3>{{ t('customers.globalAuditFiltersTitle') }}</h3>
          <p class="muted">{{ t('customers.globalAuditFiltersHint') }}</p>
          <div class="audit-filter-grid mt-16">
            <label>
              {{ t('customers.auditFilterFrom') }}
              <DateInputField v-model="auditFromDate" :range-start="auditFromDate" :range-end="auditToDate" :label="t('customers.auditFilterFrom')" />
            </label>
            <label>
              {{ t('customers.auditFilterTo') }}
              <DateInputField v-model="auditToDate" :range-start="auditFromDate" :range-end="auditToDate" :label="t('customers.auditFilterTo')" />
            </label>
            <label>
              {{ t('customers.auditFilterLoan') }}
              <CustomSelect v-model="auditLoanFilter" :options="auditLoanFilterOptions" />
            </label>
            <button class="btn btn-secondary" type="button" @click="resetAuditFilters">
              <FilterX :size="16" />
              {{ t('customers.auditResetFilters') }}
            </button>
          </div>
        </article>

        <!-- ── Tab: Overview ────────────────────────── -->
        <template v-if="detailTab === 'overview'">
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

        </template>

        <!-- ── Tab: Edit ─────────────────────────── -->

        <!-- ── Tab: Payments ──────────────────────── -->
        <template v-if="detailTab === 'payments'">
        <div class="mt-16">
          <div class="section-head-split">
            <div>
              <h3>{{ t('customers.invoicesTitle') }}</h3>
              <p class="muted">{{ t('customers.invoicesHint') }}</p>
            </div>
            <CustomSelect
              v-model="invoiceFilter"
              inputClass="table-select"
              :options="invoiceFilterOptions"
              :ariaLabel="t('customers.invoiceFilter')"
            />
          </div>

          <p v-if="financialDataLoading" class="muted mt-16">{{ t('customers.loadingFinancialData') }}</p>
          <p v-else-if="financialDataError" class="muted mt-16">{{ t('customers.financialDataUnavailable') }}</p>

          <div v-else class="table-wrap mt-16">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.loan') }}</th>
                <th>{{ t('payments.period') }}</th>
                <th>{{ t('payments.dueDate') }}</th>
                <th class="text-right">{{ t('common.periodInterest') }}</th>
                <th class="text-right">{{ t('payments.penalty') }}</th>
                <th class="text-right">{{ t('common.paid') }}</th>
                <th class="text-right">{{ t('payments.outstandingPeriod') }}</th>
                <th>{{ t('common.status') }}</th>
                <th v-if="canVoidCharges">{{ t('common.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in paginatedInvoices" :key="item.interest_charge_id">
                <td :data-label="t('common.loan')">#{{ item.loan_id }}</td>
                <td :data-label="t('payments.period')">{{ item.billing_period }}</td>
                <td :data-label="t('payments.dueDate')">{{ formatDateDMY(item.due_date) }}</td>
                <td class="text-right" :data-label="t('common.periodInterest')">{{ formatCurrency(item.charge_amount) }}</td>
                <td class="text-right" :data-label="t('payments.penalty')">{{ formatCurrency(item.penalty_amount) }}</td>
                <td class="text-right" :data-label="t('common.paid')">{{ formatCurrency(item.paid_amount) }}</td>
                <td class="text-right num-strong" :data-label="t('payments.outstandingPeriod')">
                  {{ formatCurrency(item.outstanding) }}
                </td>
                <td :data-label="t('common.status')">
                  <span class="pill" :class="invoiceStatusClass(item)">{{ t(invoiceStatusKey(item)) }}</span>
                  <div class="muted mt-1" v-if="item.voided && item.void_reason">{{ item.void_reason }}</div>
                </td>
                <!-- No data-label: an action cell becomes a full-width block on a phone. -->
                <td v-if="canVoidCharges" class="text-right">
                  <button
                    v-if="!item.voided && !item.settled"
                    class="btn btn-destructive btn-icon"
                    type="button"
                    :title="t('interest.voidCharge')"
                    :aria-label="t('interest.voidCharge')"
                    @click="chargeToVoid = toVoidable(item)"
                  >
                    <Ban :size="14" />
                  </button>
                </td>
              </tr>
              <tr v-if="!filteredInvoices.length">
                <td :colspan="canVoidCharges ? 9 : 8">{{ t('customers.noInvoicesForFilter') }}</td>
              </tr>
            </tbody>
          </table>
              <Pagination v-model="invoicesCurrentPage" :totalItems="filteredInvoices.length" :itemsPerPage="10" />
          </div>
        </div>

        </template>

        <!-- ── Tab: Loans ─────────────────────────── -->
        <template v-if="detailTab === 'loans'">
        <div class="mt-16">
          <div class="flex-between">
            <h3>{{ t('customers.customerLoans') }}</h3>
          </div>
          <p class="muted" v-if="!allSelectedCustomerLoans.length">{{ t('customers.noLoans') }}</p>
          <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.id') }}</th>
                <th>{{ t('common.type') }}</th>
                <th>{{ t('customers.loanDisbursementDate') }}</th>
                <th>{{ t('common.principal') }}</th>
                <th>{{ t('loans.outstanding') }}</th>
                <th>{{ t('loans.rate') }}</th>
                <th>{{ t('common.status') }}</th>
                <th>{{ t('common.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="loan in paginatedCustomerLoans"
                :key="loan.id"
                class="clickable-row"
                @click="openCustomerLoanDetail(loan.id)"
              >
                <td :data-label="t('common.id')">#{{ loan.id }}</td>
                <td :data-label="t('common.type')">{{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
                <td :data-label="t('customers.loanDisbursementDate')">{{ formatDateDMY(loan.disbursementDate) }}</td>
                <td :data-label="t('common.principal')">{{ formatCurrency(loan.principalAmount) }}</td>
                <td :data-label="t('loans.outstanding')">{{ formatCurrency(loan.outstandingPrincipal) }}</td>
                <td :data-label="t('loans.rate')">{{ loan.monthlyInterestRate }}%</td>
                <td :data-label="t('common.status')">
                  <LoanStatusPill :status="loan.status" :paused="loan.interestPaused" :pauseReason="loan.interestPauseReason" />
                </td>
                <td>
                  <div class="form-inline">
                    <button v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])" class="btn btn-secondary btn-icon" type="button" :title="t('customers.editLoan')" @click.stop="openLoanEditModal(loan)">
                      <Pencil :size="14" />
                    </button>
                    <a :href="'/print/invoice/loan/' + loan.id" target="_blank" class="btn btn-secondary btn-icon" :title="t('common.printInvoice')" @click.stop>
                      <Printer :size="16" />
                    </a>
                    <button v-if="hasRole([UserRole.Administrator])" class="btn btn-destructive btn-icon" type="button" :title="t('customers.deleteLoan')" :disabled="isSaving" @click.stop="handleDeleteLoan(loan.id)">
                      <Trash2 :size="16" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
              <Pagination v-model="loansCurrentPage" :totalItems="allSelectedCustomerLoans.length" :itemsPerPage="10" />
          </div>
        </div>
        </template>

        <!-- ── Tab: Payments (customer payments) continues ── -->
        <template v-if="detailTab === 'payments'">
        <div class="mt-16">
          <div class="section-head-split">
            <div>
              <h3>{{ t('customers.customerPayments') }}</h3>
              <p class="muted">{{ t('customers.totalPaid', { amount: formatCurrency(totalCustomerPaid) }) }}</p>
            </div>
            <button class="btn btn-secondary" type="button" @click="printHistory" v-if="selectedCustomerPayments.length">
              <Printer :size="16" />
              {{ t('common.printHistory') }}
            </button>
          </div>
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
                <th>{{ t('common.receivedBy') }}</th>
                <th>{{ t('payments.notes') }}</th>
                <th>{{ t('common.status') }}</th>
                <th>{{ t('common.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="payment in paginatedCustomerPayments" :key="payment.id">
              <tr :class="{ 'row-expanded': expandedPaymentId === payment.id }">
                <td :data-label="t('common.id')">
                  <button
                    class="btn btn-ghost btn-icon"
                    type="button"
                    :aria-expanded="expandedPaymentId === payment.id"
                    :aria-label="t('payments.showAllocation')"
                    :title="t('payments.showAllocation')"
                    @click="togglePaymentAllocation(payment.id)"
                  >
                    <component :is="expandedPaymentId === payment.id ? ChevronDown : ChevronRight" :size="14" />
                  </button>
                  #{{ payment.id }}
                </td>
                <td :data-label="t('common.loan')">#{{ payment.loanId }}</td>
                <td :data-label="t('common.date')">{{ formatDateDMY(payment.paymentDate) }}</td>
                <td :data-label="t('common.total')">{{ formatCurrency(payment.totalAmount) }}</td>
                <td :data-label="t('payments.penalty')">{{ formatCurrency(payment.allocatedToPenalty) }}</td>
                <td :data-label="t('common.interest')">{{ formatCurrency(payment.allocatedToInterest) }}</td>
                <td :data-label="t('common.fees')">{{ formatCurrency(payment.allocatedToFees) }}</td>
                <td :data-label="t('common.principal')">{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
                <td :data-label="t('common.method')">
                  {{ paymentMethodLabel(payment.paymentMethod) }}
                </td>
                <td :data-label="t('common.receivedBy')">{{ userLabel(payment.receiver) ?? '-' }}</td>
                <td class="muted" :data-label="t('payments.notes')">{{ payment.notes || '-' }}</td>
                <td :data-label="t('common.status')">
                  <span :class="['pill', payment.isReversed ? 'pill-overdue' : 'pill-current']">
                    {{ payment.isReversed ? t('payments.reversed') : t('common.active') }}
                  </span>
                  <div class="muted mt-1" v-if="payment.isReversed">
                    <span v-if="payment.reversalReason">{{ payment.reversalReason }}</span>
                    <span v-if="userLabel(payment.reverser)">
                      · {{ t('payments.reversedBy', { name: userLabel(payment.reverser) }) }}
                    </span>
                  </div>
                </td>
                <td>
                  <div class="form-inline">
                    <a :href="'/print/invoice/payment/' + payment.id" target="_blank" class="btn btn-secondary btn-icon" :title="t('common.printReceipt')">
                      <Printer :size="16" />
                    </a>
                    <button
                      v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])"
                      class="btn btn-secondary btn-icon"
                      type="button"
                      :title="t('payments.editPayment')"
                      :disabled="payment.isReversed || isSaving"
                      @click="openPaymentEditModal(payment)"
                    >
                      <Pencil :size="16" />
                    </button>
                    <button
                      v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])"
                      class="btn btn-destructive btn-icon"
                      type="button"
                      :title="t('payments.deletePayment')"
                      :aria-label="t('payments.deletePayment')"
                      :disabled="payment.isReversed || isSaving"
                      @click="paymentPendingReversal = payment"
                    >
                      <Trash2 :size="16" />
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="expandedPaymentId === payment.id" class="row-detail">
                <td colspan="13">
                  <PaymentAllocationDetail :paymentId="payment.id" />
                </td>
              </tr>
              </template>
            </tbody>
          </table>
              <Pagination v-model="paymentsCurrentPage" :totalItems="selectedCustomerPayments.length" :itemsPerPage="10" />
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
              <tr v-for="item in paginatedCustomerCollateral" :key="item.id">
                <td :data-label="t('common.id')">#{{ item.id }}</td>
                <td :data-label="t('common.loan')">#{{ item.loanId }}</td>
                <td :data-label="t('customers.associatedLoanType')">{{ getLoanTypeLabel(item.loanId) }}</td>
                <td :data-label="t('customers.associatedLoanStatus')">{{ getLoanStatusLabel(item.loanId) }}</td>
                <td :data-label="t('common.description')">{{ item.description }}</td>
                <td :data-label="t('collateral.appraisedValue')">{{ formatCurrency(item.appraisedValue) }}</td>
                <td :data-label="t('collateral.custodyCode')">{{ item.custodyCode }}</td>
                <td :data-label="t('common.status')">{{ item.status === 'in-custody' ? t('common.inCustody') : t(`common.${item.status}`) }}</td>
                <td>
                  <button v-if="hasRole([UserRole.Administrator, UserRole.LoanOfficer])" class="btn btn-secondary" type="button" @click="openCollateralEditModal(item)">
                    <Pencil :size="16" />
                    {{ t('customers.editCollateral') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
              <Pagination v-model="collateralsCurrentPage" :totalItems="selectedCustomerCollateral.length" :itemsPerPage="10" />
          </div>
        </div>
        </template>
      </div>
    </div>

    <PaymentReversalModal
      :payment="paymentPendingReversal"
      @close="paymentPendingReversal = null"
      @deleted="onPaymentDeleted"
    />

    <VoidInterestChargeModal
      :charge="chargeToVoid"
      @close="chargeToVoid = null"
      @voided="onChargeVoided"
    />

    <LoanDetailModal
      :show="showCustomerLoanDetailModal"
      :loan="selectedCustomerLoanDetail"
      :customerName="selectedCustomer?.fullName || ''"
      :payments="selectedCustomerLoanPayments"
      :collaterals="selectedCustomerLoanCollateral"
      :financialDataLoading="financialDataLoading"
      :totalPendingInterest="totalPendingInterestForLoan"
      :totalPendingPenalty="totalPendingPenaltyForLoan"
      @close="closeCustomerLoanDetail"
      @payments-changed="reloadSelectedCustomerFinancials"
    />

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
              <CustomSelect v-model="loanEditForm.loanType" :options="loanTypeOptions" />
            </label>
            <label>
              {{ t('loans.principalAmount') }}
              <CurrencyInput v-model="loanEditForm.principalAmount" :required="true" />
            </label>
            <label>
              {{ t('loans.outstanding') }}
              <CurrencyInput v-model="loanEditForm.outstandingPrincipal" :required="true" />
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
               
                :required="true"
              />
            </label>
            <!--
              Read-only, for the same reason the pledge's custody status next door is.
              `active` and `overdue` are owned by the server's overdue-transition job, so
              setting either by hand is reverted on the next interest cycle. `closed` is
              reached by paying the principal to zero or by a forced close that records a
              reason — writing it here wrote the balance off with nobody's name on it. And
              `defaulted` was not even in the option list, so opening this form on a
              foreclosed loan showed a control whose current value was not among its choices.
            -->
            <label>
              {{ t('common.status') }}
              <p class="form-static-value">{{ t(`common.${loanEditForm.status}`) }}</p>
              <span class="field-hint">{{ t('loans.statusIsAutomatic') }}</span>
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
              <CustomSelect v-model.number="collateralEditForm.loanId" :options="collateralLoanIdOptions" />
            </label>
            <label>
              {{ t('common.description') }}
              <input v-model="collateralEditForm.description" required />
            </label>
            <label>
              {{ t('collateral.appraisedValue') }}
              <CurrencyInput v-model="collateralEditForm.appraisedValue" :required="true" />
            </label>
            <label>
              {{ t('collateral.storageLocation') }}
              <input v-model="collateralEditForm.storageLocation" required />
            </label>
            <!-- Custody state is not an editable field: handing a pledge back, foreclosing
                 it or selling it each have their own action, and each checks the debt first. -->
            <label>
              {{ t('common.status') }}
              <p class="form-static-value">{{ collateralStatusLabel(collateralEditForm.status) }}</p>
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
               
                :required="true"
              />
            </label>
            <label>
              {{ t('payments.paymentMethod') }}
              <CustomSelect v-model="paymentEditForm.paymentMethod" :options="paymentMethodOptions" />
            </label>
          </div>
          <!-- Read only on purpose: the amounts belong to the ledger. A wrong figure is
               corrected by reversing the payment, which asks for a reason. -->
          <p class="muted mt-8">
            {{ t('payments.editAmountsAreFixed') }}
          </p>
          <div class="stats-inline mt-8">
            <span class="pill">{{ t('common.total') }}: {{ formatCurrency(paymentEditForm.totalAmount) }}</span>
            <span class="pill">{{ t('common.interest') }}: {{ formatCurrency(paymentEditForm.allocatedToInterest) }}</span>
            <span class="pill">{{ t('payments.penalty') }}: {{ formatCurrency(paymentEditForm.allocatedToPenalty) }}</span>
            <span class="pill">{{ t('common.principal') }}: {{ formatCurrency(paymentEditForm.allocatedToPrincipal) }}</span>
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
import CustomSelect from '../components/CustomSelect.vue'
import Pagination from '../components/Pagination.vue'
import { usePagination } from '../composables/usePagination'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirmDialog } from '../composables/useConfirmDialog'
import { usePageMessage } from '../composables/usePageMessage'
import LoanDetailModal from '../components/LoanDetailModal.vue'
import LoanStatusPill from '../components/LoanStatusPill.vue'
import PaymentReversalModal from '../components/PaymentReversalModal.vue'
import VoidInterestChargeModal, { type VoidableCharge } from '../components/VoidInterestChargeModal.vue'
import PaymentAllocationDetail from '../components/PaymentAllocationDetail.vue'
import { useRoute, useRouter } from 'vue-router'
import { useBackNavigation } from '../composables/useBackNavigation'
import { Archive, ArrowLeft, Ban, CheckCircle2, ChevronDown, ChevronRight, FilterX, HandCoins, LayoutDashboard, Package, Pencil, Save, Trash2, UserPlus, Users, Wallet, X, Printer } from 'lucide-vue-next'
import DateInputField from '../components/DateInputField.vue'
import CurrencyInput from '../components/CurrencyInput.vue'
import CustomerIdentityDocumentPanel from '../components/CustomerIdentityDocumentPanel.vue'
import PageHeader from '../components/PageHeader.vue'
import { apiClient } from '../services/api'
import { usePlatformStore } from '../stores/platformStore'
import { useAuthState, UserRole } from '../modules/authentication/authState'
import type { CollateralItem, Customer, Loan, Payment } from '../types/domain'
import { formatCurrency } from '../utils/currency'
import { formatDateDMY, formatDateTime, toIsoDate } from '../utils/date'
import { paymentTypeKey } from '../utils/paymentTypes'
import { userLabel } from '../utils/userLabel'
import { interestPeriodClass, interestPeriodKey } from '../utils/loanStatus'

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
const { t } = useI18n()
const { confirm } = useConfirmDialog()
const route = useRoute()
const router = useRouter()
const { hasRole } = useAuthState()
const { message, messageClass, notify, fail, report } = usePageMessage()
const search = ref('')
const customerStatusFilter = ref<'all' | 'active' | 'archived'>('all')
const customerSortPriority = ref<SortCriterion<CustomerSortKey>[]>([{ key: 'name', direction: 'asc' }])
const selectedCustomerId = ref<number | null>(null)
const showCreateModal = ref(false)
const showEditModal = ref(false)

const openEditModal = () => {
  syncEditForm()
  showEditModal.value = true
}
/* Derived from the route, not from a flag. The detail is a place now, so the address is
   what decides whether it is open and which tab is showing — that is what makes it linkable
   and what makes the browser's back button return to the previous tab. */
const DETAIL_TABS = ['overview', 'loans', 'payments', 'collateral'] as const
type DetailTab = (typeof DETAIL_TABS)[number]

const showDetail = computed(() => route.name === 'customer-detail')
const detailTab = computed<DetailTab>(() => {
  const tab = route.params.tab as string | undefined
  // An unknown tab in a hand-typed URL opens the overview rather than a blank panel.
  return DETAIL_TABS.includes(tab as DetailTab) ? (tab as DetailTab) : 'overview'
})
const showCustomerLoanDetailModal = ref(false)
const showLoanEditModal = ref(false)
const showCollateralEditModal = ref(false)
const showPaymentEditModal = ref(false)
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

onMounted(async () => {
  await ensureInitialized()

  // A pasted link or a reload arrives with the id already in the address.
  const routeId = Number(route.params.id)
  if (Number.isFinite(routeId) && routeId > 0) selectCustomer(routeId)
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
  status: 'active' as Loan['status']
})

const collateralEditForm = reactive({
  loanId: 0,
  description: '',
  appraisedValue: 0,
  storageLocation: '',
  status: 'in-custody' as CollateralItem['status']
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

/* `selectedCustomerLoans` used to sit here, narrowing the customer's loans by the audit
   card's date range and loan picker — and then feeding the Loans tab, its count badge, the
   overview counters, `getLoanById` (which labels loan numbers on payment rows) and the loan
   dropdown inside the collateral edit modal.

   So setting a date range to read an audit trail made loans vanish from the customer's loan
   list, dropped the tab badge, blanked loan labels on payment rows, and could leave a
   pledge's own loan out of the dropdown used to edit that pledge — with nothing on screen
   saying why. The audit range now scopes only what it is about: the traceability tables,
   through `selectedCustomerPayments` below. Everything else reads the full list. */

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

const totalPendingInterestForLoan = computed(() => {
  if (!pendingInterestData.value || !selectedCustomerLoanDetail.value) return 0
  let total = 0
  for (const group of pendingInterestData.value.groups) {
    for (const item of group.items) {
      if (item.loan_id === selectedCustomerLoanDetail.value.id) {
        total += item.remaining_pending_amount
      }
    }
  }
  return total
})

const totalPendingPenaltyForLoan = computed(() => {
  if (!pendingInterestData.value || !selectedCustomerLoanDetail.value) return 0
  let total = 0
  for (const group of pendingInterestData.value.groups) {
    for (const item of group.items) {
      if (item.loan_id === selectedCustomerLoanDetail.value.id) {
        total += item.penalty_amount
      }
    }
  }
  return total
})

const selectedCustomerLoanCollateral = computed(() => {
  if (!selectedCustomerLoanDetail.value) {
    return []
  }

  return selectedCustomerCollateral.value.filter((item: CollateralItem) => item.loanId === selectedCustomerLoanDetail.value?.id)
})

const pendingInterestItems = computed(() => {
  const allItems = pendingInterestData.value?.groups.flatMap((group) => group.items) ?? []
  return allItems.filter((item) => isLoanSelectedByAuditFilter(item.loan_id) && isInAuditDateRange(item.due_date))
})


const totalPendingOutstanding = computed(() => pendingInterestItems.value.reduce((sum, item) => sum + item.current_outstanding_balance, 0))
const availableAdvanceBalance = computed(() => pendingInterestData.value?.available_advance_balance ?? 0)

const totalOutstandingPrincipal = computed(() =>
  (principalContextData.value?.items ?? []).reduce((sum, loan) => sum + loan.outstanding_principal, 0)
)



const totalCustomerPaid = computed(() =>
  selectedCustomerPayments.value.reduce((sum: number, payment: Payment) => sum + payment.totalAmount, 0)
)

const totalCustomerLoans = computed(() => allSelectedCustomerLoans.value.length)
const activeCustomerLoans = computed(() => allSelectedCustomerLoans.value.filter((loan) => loan.status === 'active').length)
const overdueCustomerLoans = computed(() => allSelectedCustomerLoans.value.filter((loan) => loan.status === 'overdue').length)

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

/* The third local copy of a shared formatter, and the only one that was also wrong about
   the clock. It hard-coded a DD/MM/YYYY order, so this screen ignored
   GlobalSettings.dateFormat like the other two did — but it also parsed with `new Date()`,
   which reads a timestamp carrying no offset as *local* time. The API stores them as UTC,
   so every audit entry was stamped with the viewer's own offset: the same action read five
   hours apart on a laptop in Bogotá and a laptop set to UTC. utils/date's formatDateTime
   appends the Z for exactly this reason. */

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


/* Later navigations only — the first one is handled in `onMounted`.
 *
 * An `immediate: true` watcher here reads the route before the rest of the setup has run, and
 * `const` in <script setup> is not hoisted: it reached `selectCustomer`, which reaches
 * `loadCustomerFinancialData`, and threw in the temporal dead zone — taking the whole view
 * down, so the route rendered nothing at all. `onMounted` runs after every declaration, which
 * makes the order irrelevant instead of merely correct today. */
watch(
  () => route.params.id,
  (value) => {
    const id = Number(value)
    if (Number.isFinite(id) && id > 0 && selectedCustomerId.value !== id) selectCustomer(id)
  }
)

const openCreateModal = () => {
  showCreateModal.value = true
}

const closeCreateModal = () => {
  showCreateModal.value = false
}

const openCustomerDetail = (customerId: number) => {
  void router.push({ name: 'customer-detail', params: { id: String(customerId), tab: 'overview' } })
}

/* Same reasoning as the loan page: a customer is also reached from more than one place. */
const goBackFromCustomer = useBackNavigation({ name: 'customers' })

const closeDetail = () => {
  goBackFromCustomer()
}

/* `push`, so the browser's back button returns to the tab you came from rather than leaving
   the customer entirely. The tab is in the address precisely so it is a place worth going
   back to; `replace` would have put it in the URL and then refused to honour it. */
const goToTab = (tab: DetailTab) => {
  if (!selectedCustomerId.value) return
  void router.push({
    name: 'customer-detail',
    params: { id: String(selectedCustomerId.value), tab }
  })
}

/* A loan has its own page now. Opening it from here used to stack a modal on the customer
   modal, which is the nesting this whole change exists to end. */
const openCustomerLoanDetail = (loanId: number) => {
  void router.push({ name: 'loan-detail', params: { id: String(loanId) } })
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
    const [pending, principal, history, invoices] = await Promise.all([
      apiClient.request<InterestPendingResponse>(`/payments/customers/${customerId}/interest-pending`),
      apiClient.request<PrincipalContextResponse>(`/payments/customers/${customerId}/principal-context`),
      apiClient.request<PaymentEvent[]>(`/payments/customers/${customerId}/history`),
      apiClient.request<{ items: InterestHistoryItem[] }>(`/payments/customers/${customerId}/interest-history`)
    ])

    pendingInterestData.value = pending
    principalContextData.value = principal
    paymentEvents.value = history
    interestHistory.value = invoices.items
  } catch {
    financialDataError.value = true
    pendingInterestData.value = null
    interestHistory.value = []
    principalContextData.value = null
    paymentEvents.value = []
  } finally {
    financialDataLoading.value = false
  }
}

const handleCreateCustomer = async () => {
  try {
    const result = await createCustomer({ ...form })
    report(result, t)

    if (result.ok) {
      form.fullName = ''
      form.documentType = 'CC'
      form.documentNumber = ''
      form.phone = ''
      form.city = ''
      closeCreateModal()
    }
  } catch {
    fail(t('messages.operationFailed'))
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

    report(result, t)
    if (result.ok) {
      syncEditForm()
    }
  } catch {
    fail(t('messages.operationFailed'))
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

    report(result, t)
    if (result.ok) {
      editForm.status = statusValue
      syncEditForm()
    }
  } catch {
    fail(t('messages.operationFailed'))
  } finally {
    isSaving.value = false
  }
}

const handleArchiveCustomer = async () => {
  if (!selectedCustomer.value) {
    return
  }

  const confirmed = await confirm(t('customers.archiveCustomerConfirm'))
  if (!confirmed) {
    return
  }

  await updateSelectedCustomerStatus('archived')
}

const handleActivateCustomer = async () => {
  if (!selectedCustomer.value) {
    return
  }

  const confirmed = await confirm(t('customers.activateCustomerConfirm'))
  if (!confirmed) {
    return
  }

  await updateSelectedCustomerStatus('active')
}

const handleDeleteCustomer = async () => {
  if (!selectedCustomer.value || isSaving.value) {
    return
  }

  const confirmed = await confirm(t('customers.deleteCustomerConfirm'))
  if (!confirmed) {
    return
  }

  isSaving.value = true
  try {
    const result = await deleteCustomer(selectedCustomer.value.id)
    report(result, t)

    if (result.ok) {
      selectedCustomerId.value = null
      closeCustomerLoanDetail()
      closeDetail()
    }
  } catch {
    fail(t('messages.operationFailed'))
  } finally {
    isSaving.value = false
  }
}

const handleUpdateLoan = async () => {
  if (selectedLoanForEditId.value === null || isSaving.value) {
    return
  }

  if (loanEditForm.outstandingPrincipal > loanEditForm.principalAmount) {
    fail(t('messages.loanOutstandingExceedsPrincipal'))
    return
  }

  const disbursementDate = toIsoDate(loanEditForm.disbursementDate)
  if (!disbursementDate) {
    fail(t('messages.invalidDateFormat'))
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
      status: loanEditForm.status
    })

    report(result, t)
    closeLoanEditModal()
    if (result.ok) {
      // Editing the rate or the dates recalculates the interest charges server-side.
      await reloadSelectedCustomerFinancials()
    }
  } catch {
    fail(t('messages.operationFailed'))
  } finally {
    isSaving.value = false
  }
}

const handleDeleteLoan = async (loanId: number) => {
  if (isSaving.value) {
    return
  }

  const confirmed = await confirm(t('customers.deleteLoanConfirm'))
  if (!confirmed) {
    return
  }

  isSaving.value = true
  try {
    const result = await deleteLoan(loanId)
    report(result, t)

    if (result.ok) {
      if (selectedLoanDetailId.value === loanId) {
        closeCustomerLoanDetail()
      }
      await reloadSelectedCustomerFinancials()
    }
  } catch {
    fail(t('messages.operationFailed'))
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
      storageLocation: collateralEditForm.storageLocation
    })

    report(result, t)
    closeCollateralEditModal()
  } catch {
    fail(t('messages.operationFailed'))
  } finally {
    isSaving.value = false
  }
}

const paymentPendingReversal = ref<Payment | null>(null)

/**
 * Pending interest, principal context and the traceability events all come from their own
 * fetches, not from the store, so  does not touch them. Every mutation that
 * changes a customer credit picture has to call this or the tables keep showing figures for
 * data that no longer exists — deleting a loan left its payment events on screen.
 */
const reloadSelectedCustomerFinancials = async () => {
  if (selectedCustomer.value) {
    await loadCustomerFinancialData(selectedCustomer.value.id)
  }
}

const onPaymentDeleted = async (paymentId: number) => {
  notify(t('payments.paymentDeleted', { id: paymentId }))
  if (selectedCustomer.value) {
    await loadCustomerFinancialData(selectedCustomer.value.id)
  }
}

/* Voiding forgives billed interest, which is the same class of decision as disposing of a
   pledge — so it matches the API, which refuses anyone but an administrator. Hiding the
   control for everyone else means a loan officer never discovers the action by being
   refused by it. */
const canVoidCharges = computed(() => hasRole([UserRole.Administrator]))
const chargeToVoid = ref<VoidableCharge | null>(null)

/* One open at a time. Several expanded rows would push the row being read off screen,
   and the panel answers a question about one payment, not a comparison between them. */
/* ── Invoices ────────────────────────────────────────────────────────────────────────────
 *
 * One table for every billing period, filtered — not a second table beside the pending one.
 * The pending-only view was all this screen had, so a customer's paid invoices existed
 * nowhere in the application; adding a separate "paid" table would have recreated the same
 * money in two grids, which is exactly what the payments section was just cured of.
 *
 * It defaults to pending because that is what someone opening a customer is usually chasing.
 */
type InvoiceFilter = 'pending' | 'settled' | 'voided' | 'all'

interface InterestHistoryItem {
  interest_charge_id: number
  loan_id: number
  billing_period: string
  due_date: string
  charge_amount: number
  penalty_amount: number
  paid_amount: number
  outstanding: number
  settled: boolean
  overdue: boolean
  voided: boolean
  void_reason: string
}

const interestHistory = ref<InterestHistoryItem[]>([])
const invoiceFilter = ref<InvoiceFilter>('pending')

const invoiceFilterOptions = computed(() => [
  { value: 'pending', label: t('customers.invoiceFilterPending') },
  { value: 'settled', label: t('customers.invoiceFilterSettled') },
  { value: 'voided', label: t('customers.invoiceFilterVoided') },
  { value: 'all', label: t('customers.invoiceFilterAll') }
])

const filteredInvoices = computed(() =>
  interestHistory.value.filter((item) => {
    if (invoiceFilter.value === 'all') return true
    if (invoiceFilter.value === 'voided') return item.voided
    if (invoiceFilter.value === 'settled') return item.settled
    // Pending: still owes and was not cancelled.
    return !item.voided && !item.settled
  })
)

/* Settled and voided are facts about the invoice; anything else is a period, and it gets the
   shared three-state answer rather than a flat "pending" — otherwise this screen would be the
   one place that stops saying "vence hoy". */
const invoiceStatusKey = (item: InterestHistoryItem) => {
  if (item.voided) return 'customers.invoiceVoided'
  if (item.settled) return 'customers.invoiceSettled'
  return interestPeriodKey(item)
}

const invoiceStatusClass = (item: InterestHistoryItem) => {
  if (item.voided) return 'pill-upcoming'
  if (item.settled) return 'pill-current'
  return interestPeriodClass(item)
}

/* The void modal speaks the collection screen's shape, so the record's row is translated
   rather than the modal taught a second one. */
const toVoidable = (item: InterestHistoryItem): VoidableCharge => ({
  interest_charge_id: item.interest_charge_id,
  loan_id: item.loan_id,
  billing_period: item.billing_period,
  current_outstanding_balance: item.outstanding
})

const expandedPaymentId = ref<number | null>(null)
const togglePaymentAllocation = (paymentId: number) => {
  expandedPaymentId.value = expandedPaymentId.value === paymentId ? null : paymentId
}

const onChargeVoided = async (chargeId: number) => {
  notify(t('interest.chargeVoided', { id: chargeId }))
  // The pending-interest table comes from its own fetch, not from the store, so nothing
  // else reloads it — the voided period would stay on screen until the tab was reopened.
  await reloadSelectedCustomerFinancials()
}

const handleUpdatePayment = async () => {
  if (selectedPaymentForEditId.value === null || isSaving.value) {
    return
  }

  const paymentDate = toIsoDate(paymentEditForm.paymentDate)
  if (!paymentDate) {
    fail(t('messages.invalidDateFormat'))
    return
  }

  isSaving.value = true
  try {
    const result = await updatePayment({
      id: selectedPaymentForEditId.value,
      paymentDate,
      paymentMethod: paymentEditForm.paymentMethod,
      notes: paymentEditForm.notes
    })

    report(result, t)
    if (result.ok && selectedCustomer.value) {
      closePaymentEditModal()
      await loadCustomerFinancialData(selectedCustomer.value.id)
    }
  } catch {
    fail(t('messages.operationFailed'))
  } finally {
    isSaving.value = false
  }
}

const getLoanById = (loanId: number) => allSelectedCustomerLoans.value.find((loan) => loan.id === loanId) ?? null

const getLoanTypeLabel = (loanId: number) => {
  const loan = getLoanById(loanId)
  if (!loan) {
    return '-'
  }
  return loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal')
}

/* Was `window.print()`, which printed the application — sidebar, open modal, whatever tab
   was showing, in the operator's theme — instead of the payment-history document. The
   button 340 lines above it in the same modal already linked to the right route. */
const printHistory = () => {
  if (!selectedCustomer.value) {
    return
  }
  window.open(`/print/invoice/history/${selectedCustomer.value.id}`, '_blank')
}

const getLoanStatusLabel = (loanId: number) => {
  const loan = getLoanById(loanId)
  if (!loan) {
    return '-'
  }
  return t(`common.${loan.status}`)
}

const paymentMethodLabel = (method: string) => {
  const m = method.toLowerCase()
  if (m === 'cash') {
    return t('common.cash')
  }
  if (m === 'bank-transfer' || m === 'bank_transfer') {
    return t('common.bankTransfer')
  }
  return t('common.other')
}


const paymentTypeLabel = (paymentType: string) => t(paymentTypeKey(paymentType))

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

const { currentPage: customerCurrentPage, paginatedArray: paginatedCustomers } = usePagination(filteredCustomers)
const { currentPage: invoicesCurrentPage, paginatedArray: paginatedInvoices } = usePagination(filteredInvoices)
const { currentPage: loansCurrentPage, paginatedArray: paginatedCustomerLoans } = usePagination(allSelectedCustomerLoans)
const { currentPage: paymentsCurrentPage, paginatedArray: paginatedCustomerPayments } = usePagination(selectedCustomerPayments)
const { currentPage: collateralsCurrentPage, paginatedArray: paginatedCustomerCollateral } = usePagination(selectedCustomerCollateral)
const customerStatusFilterOptions = computed(() => [
  { value: 'all', label: t('loans.allStatuses') },
  { value: 'active', label: t('common.active') },
  { value: 'archived', label: t('common.archived') }
])

const customerStatusOptions = computed(() => [
  { value: 'active', label: t('common.active') },
  { value: 'archived', label: t('common.archived') }
])

const formattedDocumentTypeOptions = computed(() => 
  documentTypeOptions.map(o => ({ value: o, label: o }))
)

const auditLoanFilterOptions = computed(() => {
  const options = [{ value: 'all', label: t('customers.auditFilterAllLoans') }]
  loanAuditFilterOptions.value.forEach(loanId => {
    options.push({ value: String(loanId), label: '#' + loanId })
  })
  return options
})

const loanTypeOptions = computed(() => [
  { value: 'pawn', label: t('common.pawn') },
  { value: 'personal', label: t('common.personal') }
])

/* `loanStatusOptions` used to sit here. The payload still carries `status`, because the
   API's shape requires it — but it now always carries the value the loan already has, so
   it is a no-op rather than an edit. */

const collateralLoanIdOptions = computed(() => 
  allSelectedCustomerLoans.value.map(l => ({ value: l.id, label: '#' + l.id }))
)

const collateralStatusLabel = (status: string) => {
  switch (status) {
    case 'in-custody':
    case 'in_custody':
      return t('common.inCustody')
    case 'released':
      return t('common.released')
    case 'liquidated':
      return t('common.liquidated')
    case 'for_sale':
      return t('collaterals.statusForSale')
    case 'sold':
      return t('collaterals.statusSold')
    default:
      return status
  }
}

const paymentMethodOptions = computed(() => [
  { value: 'cash', label: t('common.cash') },
  { value: 'bank-transfer', label: t('common.bankTransfer') },
  { value: 'other', label: t('common.other') }
])

</script>
