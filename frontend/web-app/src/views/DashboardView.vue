<template>
  <div>
    <h1 class="page-title">Dashboard</h1>
    <div class="grid-3 mb-4">
      <div class="stat-card">
        <div class="stat-value">{{ stats.activeLoans }}</div>
        <div class="stat-label">Active Loans</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.overdueLoans }}</div>
        <div class="stat-label">Overdue Loans</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ formatCurrency(stats.totalOutstanding) }}</div>
        <div class="stat-label">Total Outstanding</div>
      </div>
    </div>
    <div class="grid-2">
      <div class="card">
        <h3 style="margin-bottom:16px;color:#1a365d;">Quick Actions</h3>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <router-link to="/customers" class="btn btn-primary">Register Customer</router-link>
          <router-link to="/loans" class="btn btn-primary">Create Loan Application</router-link>
          <router-link to="/payments" class="btn btn-primary">Register Payment</router-link>
          <router-link to="/collateral" class="btn btn-primary">Register Collateral</router-link>
        </div>
      </div>
      <div class="card">
        <h3 style="margin-bottom:16px;color:#1a365d;">Recent Activity</h3>
        <div v-if="loading" class="loading">Loading...</div>
        <div v-else-if="recentLoans.length === 0" class="empty-state">No recent loans</div>
        <table v-else class="table">
          <thead>
            <tr><th>Loan ID</th><th>Type</th><th>Amount</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="loan in recentLoans" :key="loan.id">
              <td><router-link :to="`/loans/${loan.id}`">{{ loan.id.slice(0,8) }}...</router-link></td>
              <td>{{ loan.loan_type }}</td>
              <td>{{ formatCurrency(loan.principal_amount) }}</td>
              <td><span :class="`badge badge-${loan.status}`">{{ loan.status }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { loansApi } from '@/services/api'

interface Loan {
  id: string
  loan_type: string
  principal_amount: number
  outstanding_principal: number
  status: string
}

const loading = ref(true)
const recentLoans = ref<Loan[]>([])
const stats = ref({ activeLoans: 0, overdueLoans: 0, totalOutstanding: 0 })

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value || 0)
}

onMounted(async () => {
  try {
    const [activeData, overdueData] = await Promise.all([
      loansApi.list({ status: 'active', limit: 5 }),
      loansApi.list({ status: 'overdue', limit: 1 })
    ])
    recentLoans.value = activeData.items || []
    stats.value = {
      activeLoans: activeData.total || 0,
      overdueLoans: overdueData.total || 0,
      totalOutstanding: (activeData.items as Loan[] || []).reduce((sum: number, l: Loan) => sum + Number(l.outstanding_principal || 0), 0)
    }
  } catch {
    // ignore errors - show empty state
  } finally {
    loading.value = false
  }
})
</script>
