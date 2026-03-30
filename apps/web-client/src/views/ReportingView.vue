<template>
  <section>
    <h2>Reporting</h2>
    <p class="muted">Basic operational reports with mock data.</p>

    <div class="grid grid-2 mt-16">
      <article class="card">
        <h3>Active Loans</h3>
        <ul>
          <li v-for="loan in activeLoans" :key="loan.id">
            Loan #{{ loan.id }} - {{ getCustomerName(loan.customerId) }} - {{ formatCurrency(loan.outstandingPrincipal) }}
          </li>
        </ul>
      </article>

      <article class="card">
        <h3>Overdue Loans</h3>
        <ul>
          <li v-for="loan in overdueLoans" :key="loan.id">
            Loan #{{ loan.id }} - {{ getCustomerName(loan.customerId) }} - Due day {{ loan.dueDay }}
          </li>
        </ul>
      </article>

      <article class="card">
        <h3>Collateral In Custody</h3>
        <ul>
          <li v-for="item in custodyItems" :key="item.id">
            {{ item.custodyCode }} - Loan #{{ item.loanId }} - {{ item.description }}
          </li>
        </ul>
      </article>

      <article class="card">
        <h3>Cash Summary</h3>
        <p>Total payments registered: {{ state.payments.length }}</p>
        <p>Total collected: {{ formatCurrency(totalCollected) }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, getCustomerName } = useMockPlatformStore()

const activeLoans = computed(() => state.loans.filter((loan) => loan.status === 'active'))
const overdueLoans = computed(() => state.loans.filter((loan) => loan.status === 'overdue'))
const custodyItems = computed(() => state.collateralItems.filter((item) => item.status === 'in-custody'))
const totalCollected = computed(() => state.payments.reduce((sum, payment) => sum + payment.totalAmount, 0))

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
</script>
