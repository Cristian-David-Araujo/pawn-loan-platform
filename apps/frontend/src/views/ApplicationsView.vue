<script setup>
import { reactive, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'
import StatusBadge from '../components/StatusBadge.vue'

const store = useLoanStore()
const error = ref('')

const form = reactive({
  customerId: '',
  loanType: 'pawn',
  requestedAmount: 500,
  monthlyInterestRate: 6,
  termMonths: 6,
  notes: '',
})

function submit() {
  error.value = ''
  try {
    store.createApplication(form)
    form.notes = ''
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Create Loan Application</h3>
      <div class="form-grid">
        <select v-model="form.customerId">
          <option value="">Select customer</option>
          <option v-for="item in store.customers" :key="item.id" :value="item.id">
            {{ item.firstName }} {{ item.lastName }}
          </option>
        </select>
        <select v-model="form.loanType">
          <option value="pawn">Pawn-backed</option>
          <option value="personal">Personal</option>
        </select>
        <input v-model.number="form.requestedAmount" type="number" min="1" placeholder="Requested amount" />
        <input v-model.number="form.monthlyInterestRate" type="number" min="0" step="0.1" placeholder="Monthly rate" />
        <input v-model.number="form.termMonths" type="number" min="1" placeholder="Term months" />
        <input v-model="form.notes" placeholder="Notes" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary" @click="submit">Create application</button>
    </article>

    <article class="card">
      <h3>Application Workflow</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Customer</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="app in store.applicationsEnriched" :key="app.id">
              <td>{{ app.id }}</td>
              <td>{{ app.customerName }}</td>
              <td>{{ app.loanType }}</td>
              <td>{{ app.requestedAmount }}</td>
              <td><StatusBadge :status="app.status" /></td>
              <td>
                <div class="button-row">
                  <button class="btn btn-success" :disabled="app.status !== 'submitted'" @click="store.reviewApplication(app.id, 'approve')">
                    Approve
                  </button>
                  <button class="btn btn-danger" :disabled="app.status !== 'submitted'" @click="store.reviewApplication(app.id, 'reject')">
                    Reject
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </section>
</template>
