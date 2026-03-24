<script setup>
import { useLoanStore } from '../stores/loanStore'

const store = useLoanStore()
const summary = store.dashboard

function money(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value || 0)
}

function runMonthlyCycle() {
  store.generateMonthlyInterest()
  store.applyOverdue(2)
}
</script>

<template>
  <section class="panel-grid">
    <article class="card metric">
      <p>Active Loans</p>
      <h3>{{ summary.active }}</h3>
    </article>
    <article class="card metric">
      <p>Overdue Loans</p>
      <h3>{{ summary.overdue }}</h3>
    </article>
    <article class="card metric">
      <p>Outstanding Principal</p>
      <h3>{{ money(summary.outstandingPrincipal) }}</h3>
    </article>
    <article class="card metric">
      <p>Accrued Interest</p>
      <h3>{{ money(summary.accruedInterest) }}</h3>
    </article>
    <article class="card metric">
      <p>Today Cash Collection</p>
      <h3>{{ money(store.cashSummary.total) }}</h3>
    </article>
    <article class="card metric">
      <p>Notifications Sent</p>
      <h3>{{ store.notifications.length }}</h3>
    </article>
  </section>

  <section class="content-grid">
    <article class="card">
      <h3>Operational Shortcuts</h3>
      <div class="button-row">
        <button class="btn btn-primary" @click="runMonthlyCycle">Run monthly cycle</button>
        <button class="btn" @click="store.applyOverdue(0)">Recalculate overdue</button>
      </div>
      <p class="muted">Monthly cycle generates interest once per active loan and updates delinquency.</p>
    </article>

    <article class="card">
      <h3>Aging Buckets</h3>
      <ul class="plain-list">
        <li>1-30 days: <strong>{{ store.agingBuckets['1-30'] }}</strong></li>
        <li>31-60 days: <strong>{{ store.agingBuckets['31-60'] }}</strong></li>
        <li>61-90 days: <strong>{{ store.agingBuckets['61-90'] }}</strong></li>
        <li>90+ days: <strong>{{ store.agingBuckets['90+'] }}</strong></li>
      </ul>
    </article>
  </section>
</template>
