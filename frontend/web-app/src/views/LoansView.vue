<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="page-title" style="margin-bottom:0">Loans</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">+ New Application</button>
    </div>

    <div class="card">
      <div class="flex gap-2 mb-4">
        <select v-model="statusFilter" style="padding:8px 12px;border:1px solid #e2e8f0;border-radius:4px;" @change="loadLoans">
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="overdue">Overdue</option>
          <option value="closed">Closed</option>
          <option value="defaulted">Defaulted</option>
        </select>
        <select v-model="typeFilter" style="padding:8px 12px;border:1px solid #e2e8f0;border-radius:4px;" @change="loadLoans">
          <option value="">All Types</option>
          <option value="pawn">Pawn</option>
          <option value="personal">Personal</option>
        </select>
      </div>

      <div v-if="loading" class="loading">Loading...</div>
      <table v-else class="table">
        <thead>
          <tr><th>ID</th><th>Type</th><th>Principal</th><th>Outstanding</th><th>Rate</th><th>Status</th><th>Actions</th></tr>
        </thead>
        <tbody>
          <tr v-for="loan in loans" :key="loan.id">
            <td style="font-family:monospace;font-size:0.8rem">{{ loan.id.slice(0,8) }}...</td>
            <td>{{ loan.loan_type }}</td>
            <td>{{ formatCurrency(loan.principal_amount) }}</td>
            <td>{{ formatCurrency(loan.outstanding_principal) }}</td>
            <td>{{ (Number(loan.monthly_interest_rate) * 100).toFixed(1) }}%</td>
            <td><span :class="`badge badge-${loan.status}`">{{ loan.status }}</span></td>
            <td><router-link :to="`/loans/${loan.id}`" class="btn btn-sm btn-primary">View</router-link></td>
          </tr>
          <tr v-if="loans.length === 0"><td colspan="7" style="text-align:center;color:#718096;">No loans found</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Loan Application Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h2 style="margin-bottom:20px">New Loan Application</h2>
        <div v-if="formError" class="alert alert-error">{{ formError }}</div>
        <form @submit.prevent="createApplication">
          <div class="form-group"><label>Customer ID *</label><input v-model="appForm.customer_id" required placeholder="UUID of customer" /></div>
          <div class="grid-2">
            <div class="form-group">
              <label>Loan Type *</label>
              <select v-model="appForm.loan_type" required>
                <option value="">Select...</option>
                <option value="pawn">Pawn-backed</option>
                <option value="personal">Personal</option>
              </select>
            </div>
            <div class="form-group"><label>Amount *</label><input v-model="appForm.requested_amount" type="number" step="0.01" required /></div>
          </div>
          <div class="grid-2">
            <div class="form-group"><label>Monthly Rate (e.g. 0.05) *</label><input v-model="appForm.monthly_interest_rate" type="number" step="0.001" required /></div>
            <div class="form-group"><label>Term (months) *</label><input v-model="appForm.term_months" type="number" required /></div>
          </div>
          <div class="form-group"><label>Notes</label><textarea v-model="appForm.notes" rows="2"></textarea></div>
          <div class="flex gap-2" style="justify-content:flex-end;margin-top:16px;">
            <button type="button" class="btn" style="border:1px solid #e2e8f0" @click="showCreateModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? 'Submitting...' : 'Submit' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { loansApi, loanApplicationsApi } from '@/services/api'

interface Loan {
  id: string
  loan_type: string
  principal_amount: number
  outstanding_principal: number
  monthly_interest_rate: number | string
  status: string
}

const loans = ref<Loan[]>([])
const loading = ref(true)
const statusFilter = ref('')
const typeFilter = ref('')
const showCreateModal = ref(false)
const saving = ref(false)
const formError = ref('')

const appForm = ref({ customer_id: '', loan_type: '', requested_amount: '', monthly_interest_rate: '', term_months: '', notes: '' })

function formatCurrency(v: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0)
}

async function loadLoans() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (typeFilter.value) params.loan_type = typeFilter.value
    const data = await loansApi.list({ ...params, limit: 100 })
    loans.value = data.items || []
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function createApplication() {
  saving.value = true
  formError.value = ''
  try {
    await loanApplicationsApi.create({
      customer_id: appForm.value.customer_id,
      loan_type: appForm.value.loan_type,
      requested_amount: parseFloat(appForm.value.requested_amount),
      monthly_interest_rate: parseFloat(appForm.value.monthly_interest_rate),
      term_months: parseInt(appForm.value.term_months),
      notes: appForm.value.notes || undefined
    })
    showCreateModal.value = false
    await loadLoans()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail || 'Failed to submit application'
  } finally {
    saving.value = false
  }
}

onMounted(loadLoans)
</script>

<style scoped>
.modal-overlay { position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:1000; }
.modal { background:white;border-radius:8px;padding:32px;width:100%;max-width:560px;max-height:90vh;overflow-y:auto; }
</style>
