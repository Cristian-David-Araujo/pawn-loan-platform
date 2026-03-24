<script setup>
import { reactive, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'

const store = useLoanStore()
const error = ref('')
const lastPayment = ref(null)

const form = reactive({
  loanId: '',
  totalAmount: 0,
  paymentMethod: 'cash',
  receivedBy: 'cashier',
  paymentDate: '',
})

function submit() {
  error.value = ''
  try {
    lastPayment.value = store.registerPayment(form)
    Object.assign(form, {
      loanId: '',
      totalAmount: 0,
      paymentMethod: 'cash',
      receivedBy: 'cashier',
      paymentDate: '',
    })
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Register Payment</h3>
      <div class="form-grid">
        <select v-model="form.loanId">
          <option value="">Select loan</option>
          <option v-for="loan in store.loansEnriched" :key="loan.id" :value="loan.id">
            {{ loan.id }} - {{ loan.customerName }}
          </option>
        </select>
        <input v-model.number="form.totalAmount" type="number" min="0" placeholder="Amount" />
        <select v-model="form.paymentMethod">
          <option value="cash">Cash</option>
          <option value="bank_transfer">Bank transfer</option>
          <option value="other">Other</option>
        </select>
        <input v-model="form.receivedBy" placeholder="Received by" />
        <input v-model="form.paymentDate" type="date" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary" @click="submit">Apply payment</button>

      <div v-if="lastPayment" class="allocation">
        <h4>Last Allocation</h4>
        <p>Penalty: {{ lastPayment.allocatedToPenalty }}</p>
        <p>Interest: {{ lastPayment.allocatedToInterest }}</p>
        <p>Fees: {{ lastPayment.allocatedToFees }}</p>
        <p>Principal: {{ lastPayment.allocatedToPrincipal }}</p>
      </div>
    </article>

    <article class="card">
      <h3>Payment History</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Loan</th>
              <th>Total</th>
              <th>Interest</th>
              <th>Principal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="payment in store.payments" :key="payment.id">
              <td>{{ payment.id }}</td>
              <td>{{ payment.loanId }}</td>
              <td>{{ payment.totalAmount }}</td>
              <td>{{ payment.allocatedToInterest }}</td>
              <td>{{ payment.allocatedToPrincipal }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </section>
</template>
