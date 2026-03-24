<script setup>
import { reactive, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'
import StatusBadge from '../components/StatusBadge.vue'

const store = useLoanStore()
const error = ref('')

const form = reactive({
  applicationId: '',
  principalAmount: 0,
  monthlyInterestRate: 0,
  disbursementDate: '',
  nextDueDate: '',
})

function createLoan() {
  error.value = ''
  try {
    store.createLoanFromApplication(form.applicationId, form)
    Object.assign(form, {
      applicationId: '',
      principalAmount: 0,
      monthlyInterestRate: 0,
      disbursementDate: '',
      nextDueDate: '',
    })
  } catch (err) {
    error.value = err.message
  }
}

function renew(id) {
  error.value = ''
  try {
    store.renewLoan(id)
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Create Loan from Approved Application</h3>
      <div class="form-grid">
        <select v-model="form.applicationId">
          <option value="">Select approved application</option>
          <option
            v-for="app in store.applicationsEnriched.filter((item) => item.status === 'approved')"
            :key="app.id"
            :value="app.id"
          >
            {{ app.id }} - {{ app.customerName }}
          </option>
        </select>
        <input v-model.number="form.principalAmount" type="number" min="0" placeholder="Principal amount (optional)" />
        <input v-model.number="form.monthlyInterestRate" type="number" min="0" step="0.1" placeholder="Monthly rate (optional)" />
        <input v-model="form.disbursementDate" type="date" />
        <input v-model="form.nextDueDate" type="date" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary" @click="createLoan">Create loan</button>
    </article>

    <article class="card">
      <h3>Loan Portfolio</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Customer</th>
              <th>Principal</th>
              <th>Balance</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="loan in store.loansEnriched" :key="loan.id">
              <td>{{ loan.id }}</td>
              <td>{{ loan.customerName }}</td>
              <td>{{ loan.principalAmount }}</td>
              <td>{{ loan.balance.toFixed(2) }}</td>
              <td><StatusBadge :status="loan.status" /></td>
              <td>
                <button class="btn" :disabled="loan.status !== 'active' && loan.status !== 'overdue'" @click="renew(loan.id)">
                  Renew
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </section>
</template>
