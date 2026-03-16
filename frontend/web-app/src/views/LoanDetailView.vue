<template>
  <div>
    <div class="flex items-center gap-2 mb-4">
      <router-link to="/loans" style="color:#4a5568;text-decoration:none;">← Loans</router-link>
    </div>
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="loan">
      <div class="flex justify-between items-center mb-4">
        <h1 class="page-title" style="margin-bottom:0">Loan Details</h1>
        <div class="flex gap-2">
          <span :class="`badge badge-${loan.status}`" style="font-size:0.9rem;padding:4px 12px;">{{ loan.status }}</span>
          <button v-if="loan.status === 'active'" class="btn btn-danger btn-sm" @click="closeLoan">Close Loan</button>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <h3 style="margin-bottom:16px">Loan Information</h3>
          <table style="width:100%">
            <tr><td style="color:#718096;padding:4px 0">Type</td><td><strong>{{ loan.loan_type }}</strong></td></tr>
            <tr><td style="color:#718096;padding:4px 0">Principal</td><td><strong>{{ formatCurrency(loan.principal_amount as number) }}</strong></td></tr>
            <tr><td style="color:#718096;padding:4px 0">Outstanding</td><td><strong>{{ formatCurrency(loan.outstanding_principal as number) }}</strong></td></tr>
            <tr><td style="color:#718096;padding:4px 0">Monthly Rate</td><td><strong>{{ (Number(loan.monthly_interest_rate) * 100).toFixed(2) }}%</strong></td></tr>
            <tr><td style="color:#718096;padding:4px 0">Term</td><td><strong>{{ loan.term_months }} months</strong></td></tr>
            <tr><td style="color:#718096;padding:4px 0">Due Day</td><td><strong>Day {{ loan.due_day }}</strong></td></tr>
            <tr v-if="loan.disbursement_date"><td style="color:#718096;padding:4px 0">Disbursed</td><td>{{ new Date(loan.disbursement_date as string).toLocaleDateString() }}</td></tr>
          </table>
        </div>
        <div class="card">
          <h3 style="margin-bottom:16px">ID &amp; Reference</h3>
          <div style="font-family:monospace;font-size:0.8rem;word-break:break-all;color:#4a5568">{{ loan.id }}</div>
          <div v-if="loan.renewal_of" style="margin-top:8px;font-size:0.875rem;color:#718096">Renewal of: {{ loan.renewal_of }}</div>
        </div>
      </div>
    </div>
    <div v-else class="card"><p>Loan not found.</p></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loansApi } from '@/services/api'

const route = useRoute()
const router = useRouter()
const loan = ref<Record<string, unknown> | null>(null)
const loading = ref(true)

function formatCurrency(v: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0)
}

async function closeLoan() {
  if (!loan.value || !confirm('Close this loan?')) return
  try {
    await loansApi.close(loan.value.id as string)
    router.push('/loans')
  } catch {
    alert('Failed to close loan')
  }
}

onMounted(async () => {
  try {
    loan.value = await loansApi.get(route.params.id as string)
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
})
</script>
