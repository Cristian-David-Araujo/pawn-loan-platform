<template>
  <div>
    <h1 class="page-title">Reports</h1>
    <div class="grid-2">
      <div class="card">
        <h3 style="margin-bottom:16px">Active Loans Summary</h3>
        <div v-if="loadingActive" class="loading">Loading...</div>
        <div v-else-if="activeReport">
          <div class="grid-2">
            <div class="stat-card"><div class="stat-value">{{ activeReport.total_active_loans }}</div><div class="stat-label">Active Loans</div></div>
            <div class="stat-card"><div class="stat-value">{{ formatCurrency(activeReport.total_outstanding_principal as number) }}</div><div class="stat-label">Outstanding Principal</div></div>
          </div>
          <div style="margin-top:12px">
            <strong>By Type:</strong>
            <div v-for="(count, type) in activeReport.by_loan_type" :key="type" style="margin-top:4px;font-size:0.875rem">
              {{ type }}: {{ count }}
            </div>
          </div>
        </div>
        <div v-else class="empty-state">Report unavailable</div>
        <button class="btn btn-primary btn-sm" style="margin-top:12px" @click="loadActiveReport">Refresh</button>
      </div>
      <div class="card">
        <h3 style="margin-bottom:16px">Overdue Loans</h3>
        <div v-if="loadingOverdue" class="loading">Loading...</div>
        <div v-else-if="overdueReport">
          <div style="text-align:center;font-size:2rem;font-weight:700;color:#e53e3e">{{ overdueReport.total_overdue_loans }}</div>
          <div style="text-align:center;color:#718096;margin-bottom:12px">Total Overdue</div>
          <table style="width:100%">
            <tr><td>1-30 days</td><td style="text-align:right;font-weight:600">{{ overdueReport.aging_1_30 }}</td></tr>
            <tr><td>31-60 days</td><td style="text-align:right;font-weight:600">{{ overdueReport.aging_31_60 }}</td></tr>
            <tr><td>61-90 days</td><td style="text-align:right;font-weight:600">{{ overdueReport.aging_61_90 }}</td></tr>
            <tr><td>90+ days</td><td style="text-align:right;font-weight:600">{{ overdueReport.aging_91_plus }}</td></tr>
          </table>
        </div>
        <div v-else class="empty-state">Report unavailable</div>
        <button class="btn btn-primary btn-sm" style="margin-top:12px" @click="loadOverdueReport">Refresh</button>
      </div>
      <div class="card">
        <h3 style="margin-bottom:16px">Collateral Custody</h3>
        <div v-if="loadingCollateral" class="loading">Loading...</div>
        <div v-else-if="collateralReport">
          <table style="width:100%">
            <tr><td>In Custody</td><td style="text-align:right;font-weight:600">{{ collateralReport.total_in_custody }}</td></tr>
            <tr><td>Released</td><td style="text-align:right;font-weight:600">{{ collateralReport.total_released }}</td></tr>
            <tr><td>Under Liquidation</td><td style="text-align:right;font-weight:600">{{ collateralReport.total_under_liquidation }}</td></tr>
            <tr><td>Sold</td><td style="text-align:right;font-weight:600">{{ collateralReport.total_sold }}</td></tr>
          </table>
        </div>
        <div v-else class="empty-state">Report unavailable</div>
        <button class="btn btn-primary btn-sm" style="margin-top:12px" @click="loadCollateralReport">Refresh</button>
      </div>
      <div class="card">
        <h3 style="margin-bottom:16px">Cash Summary</h3>
        <div v-if="loadingCash" class="loading">Loading...</div>
        <div v-else-if="cashReport">
          <table style="width:100%">
            <tr><td>Total Collected</td><td style="text-align:right;font-weight:600">{{ formatCurrency(cashReport.total_collected as number) }}</td></tr>
            <tr><td>Interest</td><td style="text-align:right">{{ formatCurrency(cashReport.total_interest_collected as number) }}</td></tr>
            <tr><td>Principal</td><td style="text-align:right">{{ formatCurrency(cashReport.total_principal_collected as number) }}</td></tr>
            <tr><td>Penalties</td><td style="text-align:right">{{ formatCurrency(cashReport.total_penalty_collected as number) }}</td></tr>
          </table>
        </div>
        <div v-else class="empty-state">Report unavailable</div>
        <button class="btn btn-primary btn-sm" style="margin-top:12px" @click="loadCashReport">Refresh</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { reportsApi } from '@/services/api'

const activeReport = ref<Record<string, unknown> | null>(null)
const overdueReport = ref<Record<string, unknown> | null>(null)
const collateralReport = ref<Record<string, unknown> | null>(null)
const cashReport = ref<Record<string, unknown> | null>(null)
const loadingActive = ref(false)
const loadingOverdue = ref(false)
const loadingCollateral = ref(false)
const loadingCash = ref(false)

function formatCurrency(v: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0)
}

async function loadActiveReport() {
  loadingActive.value = true
  try { activeReport.value = await reportsApi.activeLoans() } catch { activeReport.value = null } finally { loadingActive.value = false }
}
async function loadOverdueReport() {
  loadingOverdue.value = true
  try { overdueReport.value = await reportsApi.overdueLoans() } catch { overdueReport.value = null } finally { loadingOverdue.value = false }
}
async function loadCollateralReport() {
  loadingCollateral.value = true
  try { collateralReport.value = await reportsApi.collateralCustody() } catch { collateralReport.value = null } finally { loadingCollateral.value = false }
}
async function loadCashReport() {
  loadingCash.value = true
  try { cashReport.value = await reportsApi.cashSummary() } catch { cashReport.value = null } finally { loadingCash.value = false }
}

onMounted(() => {
  loadActiveReport()
  loadOverdueReport()
  loadCollateralReport()
  loadCashReport()
})
</script>
