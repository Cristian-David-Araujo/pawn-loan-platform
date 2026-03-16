<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="page-title" style="margin-bottom:0">Payments</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">+ Register Payment</button>
    </div>
    <div class="card">
      <div v-if="loading" class="loading">Loading...</div>
      <table v-else class="table">
        <thead>
          <tr><th>Date</th><th>Loan ID</th><th>Amount</th><th>Method</th><th>Status</th><th>Actions</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in payments" :key="p.id">
            <td>{{ p.payment_date }}</td>
            <td style="font-family:monospace;font-size:0.8rem">{{ p.loan_id.slice(0,8) }}...</td>
            <td>{{ formatCurrency(p.total_amount) }}</td>
            <td>{{ p.payment_method }}</td>
            <td><span :class="`badge badge-${p.status === 'completed' ? 'active' : 'inactive'}`">{{ p.status }}</span></td>
            <td>
              <button v-if="p.status === 'completed'" class="btn btn-sm btn-danger" @click="reversePayment(p.id)">Reverse</button>
            </td>
          </tr>
          <tr v-if="payments.length === 0"><td colspan="6" style="text-align:center;color:#718096;">No payments found</td></tr>
        </tbody>
      </table>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h2 style="margin-bottom:20px">Register Payment</h2>
        <div v-if="formError" class="alert alert-error">{{ formError }}</div>
        <form @submit.prevent="createPayment">
          <div class="form-group"><label>Loan ID *</label><input v-model="form.loan_id" required placeholder="UUID" /></div>
          <div class="grid-2">
            <div class="form-group"><label>Payment Date *</label><input v-model="form.payment_date" type="date" required /></div>
            <div class="form-group"><label>Total Amount *</label><input v-model="form.total_amount" type="number" step="0.01" required /></div>
          </div>
          <div class="grid-2">
            <div class="form-group"><label>To Interest</label><input v-model="form.to_interest" type="number" step="0.01" /></div>
            <div class="form-group"><label>To Principal</label><input v-model="form.to_principal" type="number" step="0.01" /></div>
          </div>
          <div class="grid-2">
            <div class="form-group"><label>To Penalty</label><input v-model="form.to_penalty" type="number" step="0.01" /></div>
            <div class="form-group">
              <label>Method *</label>
              <select v-model="form.method" required>
                <option value="">Select...</option>
                <option value="cash">Cash</option>
                <option value="bank_transfer">Bank Transfer</option>
                <option value="check">Check</option>
              </select>
            </div>
          </div>
          <div class="flex gap-2" style="justify-content:flex-end;margin-top:16px;">
            <button type="button" class="btn" style="border:1px solid #e2e8f0" @click="showCreateModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? 'Saving...' : 'Save' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { paymentsApi } from '@/services/api'

interface Payment {
  id: string
  loan_id: string
  payment_date: string
  total_amount: number
  payment_method: string
  status: string
}

const payments = ref<Payment[]>([])
const loading = ref(true)
const showCreateModal = ref(false)
const saving = ref(false)
const formError = ref('')
const form = ref({ loan_id: '', payment_date: '', total_amount: '', to_interest: '', to_principal: '', to_penalty: '', method: '' })

function formatCurrency(v: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0)
}

async function loadPayments() {
  loading.value = true
  try {
    const data = await paymentsApi.list({ limit: 100 })
    payments.value = data.items || []
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function createPayment() {
  saving.value = true
  formError.value = ''
  try {
    await paymentsApi.create({
      loan_id: form.value.loan_id,
      payment_date: form.value.payment_date,
      total_amount: parseFloat(form.value.total_amount),
      allocated_to_interest: parseFloat(form.value.to_interest) || 0,
      allocated_to_principal: parseFloat(form.value.to_principal) || 0,
      allocated_to_penalty: parseFloat(form.value.to_penalty) || 0,
      payment_method: form.value.method
    })
    showCreateModal.value = false
    await loadPayments()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail || 'Failed to register payment'
  } finally {
    saving.value = false
  }
}

async function reversePayment(id: string) {
  const reason = prompt('Reason for reversal?')
  if (!reason) return
  try {
    await paymentsApi.reverse(id, reason)
    await loadPayments()
  } catch {
    alert('Failed to reverse payment')
  }
}

onMounted(loadPayments)
</script>

<style scoped>
.modal-overlay { position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:1000; }
.modal { background:white;border-radius:8px;padding:32px;width:100%;max-width:560px;max-height:90vh;overflow-y:auto; }
</style>
