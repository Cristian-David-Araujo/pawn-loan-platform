<script setup>
import { reactive, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'
import StatusBadge from '../components/StatusBadge.vue'

const store = useLoanStore()
const error = ref('')

const form = reactive({
  loanId: '',
  action: '',
  outcome: '',
})

function submitAction() {
  error.value = ''
  try {
    store.addCollectionAction(form)
    form.action = ''
    form.outcome = ''
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Overdue Portfolio</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Loan</th>
              <th>Customer</th>
              <th>Days Overdue</th>
              <th>Balance</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="loan in store.delinquentLoans" :key="loan.id">
              <td>{{ loan.id }}</td>
              <td>{{ loan.customerName }}</td>
              <td>{{ loan.daysOverdue }}</td>
              <td>{{ loan.balance.toFixed(2) }}</td>
              <td><StatusBadge :status="loan.status" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>

    <article class="card">
      <h3>Collection Action</h3>
      <div class="form-grid">
        <select v-model="form.loanId">
          <option value="">Select overdue loan</option>
          <option v-for="loan in store.delinquentLoans" :key="loan.id" :value="loan.id">
            {{ loan.id }} - {{ loan.customerName }}
          </option>
        </select>
        <input v-model="form.action" placeholder="Action (call, visit, email)" />
        <input v-model="form.outcome" placeholder="Outcome" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary" @click="submitAction">Add action</button>

      <h4>Action Log</h4>
      <ul class="plain-list">
        <li v-for="item in store.collectionActions.slice(0, 8)" :key="item.id">
          {{ item.createdAt }} | {{ item.loanId }} | {{ item.action }} -> {{ item.outcome }}
        </li>
      </ul>
    </article>
  </section>
</template>
