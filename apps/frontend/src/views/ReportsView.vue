<script setup>
import { computed } from 'vue'
import { useLoanStore } from '../stores/loanStore'

const store = useLoanStore()

const totals = computed(() => {
  const outstanding = store.loans.value.reduce(
    (sum, item) => sum + item.outstandingPrincipal,
    0,
  )
  const interest = store.loans.value.reduce(
    (sum, item) => sum + item.accruedInterest,
    0,
  )
  return { outstanding, interest }
})
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Portfolio Report</h3>
      <ul class="plain-list">
        <li>Outstanding principal: <strong>{{ totals.outstanding.toFixed(2) }}</strong></li>
        <li>Accrued interest: <strong>{{ totals.interest.toFixed(2) }}</strong></li>
        <li>Active loans: <strong>{{ store.dashboard.active }}</strong></li>
        <li>Overdue loans: <strong>{{ store.dashboard.overdue }}</strong></li>
        <li>Collateral in custody: <strong>{{ store.dashboard.collateralInCustody }}</strong></li>
        <li>Payments count: <strong>{{ store.dashboard.paymentsCount }}</strong></li>
      </ul>
    </article>

    <article class="card">
      <h3>Aging Buckets</h3>
      <ul class="plain-list">
        <li>1-30: {{ store.agingBuckets['1-30'] }}</li>
        <li>31-60: {{ store.agingBuckets['31-60'] }}</li>
        <li>61-90: {{ store.agingBuckets['61-90'] }}</li>
        <li>90+: {{ store.agingBuckets['90+'] }}</li>
      </ul>
      <h4>Cash Summary Today</h4>
      <ul class="plain-list">
        <li>Total: {{ store.cashSummary.total.toFixed(2) }}</li>
        <li>Cash: {{ store.cashSummary.cash.toFixed(2) }}</li>
        <li>Transfer: {{ store.cashSummary.transfer.toFixed(2) }}</li>
        <li>Operations: {{ store.cashSummary.count }}</li>
      </ul>
    </article>
  </section>

  <section class="card">
    <h3>Audit Trail (latest)</h3>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Action</th>
            <th>Entity</th>
            <th>ID</th>
            <th>User</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in store.auditLogs.slice(0, 20)" :key="log.id">
            <td>{{ log.createdAt }}</td>
            <td>{{ log.action }}</td>
            <td>{{ log.entityType }}</td>
            <td>{{ log.entityId }}</td>
            <td>{{ log.userId }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
