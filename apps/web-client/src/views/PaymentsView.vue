<template>
  <section>
    <h2>Payments</h2>
    <p class="muted">Register payments with configurable allocation.</p>

    <form class="card form mt-16" @submit.prevent="handleCreatePayment">
      <div class="grid grid-3">
        <label>
          Loan
          <select v-model.number="form.loanId" required>
            <option v-for="loan in payableLoans" :key="loan.id" :value="loan.id">
              Loan #{{ loan.id }} - {{ getCustomerName(loan.customerId) }}
            </option>
          </select>
        </label>
        <label>
          Total amount
          <input v-model.number="form.totalAmount" type="number" min="1" required />
        </label>
        <label>
          Payment method
          <select v-model="form.paymentMethod" required>
            <option value="cash">Cash</option>
            <option value="bank-transfer">Bank transfer</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>
          Penalty
          <input v-model.number="form.allocatedToPenalty" type="number" min="0" required />
        </label>
        <label>
          Interest
          <input v-model.number="form.allocatedToInterest" type="number" min="0" required />
        </label>
        <label>
          Fees
          <input v-model.number="form.allocatedToFees" type="number" min="0" required />
        </label>
        <label>
          Principal
          <input v-model.number="form.allocatedToPrincipal" type="number" min="0" required />
        </label>
      </div>
      <button class="btn" type="submit">Register payment</button>
      <p class="notice">Allocation sum: {{ allocationSum }} / Total: {{ form.totalAmount }}</p>
      <p v-if="message" class="notice">{{ message }}</p>
    </form>

    <div class="card mt-16">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Loan</th>
            <th>Date</th>
            <th>Total</th>
            <th>Principal</th>
            <th>Interest</th>
            <th>Method</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="payment in state.payments" :key="payment.id">
            <td>{{ payment.id }}</td>
            <td>#{{ payment.loanId }}</td>
            <td>{{ payment.paymentDate }}</td>
            <td>{{ formatCurrency(payment.totalAmount) }}</td>
            <td>{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
            <td>{{ formatCurrency(payment.allocatedToInterest) }}</td>
            <td>{{ payment.paymentMethod }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, createPayment, getCustomerName } = useMockPlatformStore()
const message = ref('')

const payableLoans = computed(() => state.loans.filter((loan) => loan.status !== 'closed'))

const form = reactive({
  loanId: payableLoans.value[0]?.id ?? 1,
  totalAmount: 200,
  allocatedToPenalty: 0,
  allocatedToInterest: 50,
  allocatedToFees: 10,
  allocatedToPrincipal: 140,
  paymentMethod: 'cash' as 'cash' | 'bank-transfer' | 'other'
})

const allocationSum = computed(
  () => form.allocatedToPenalty + form.allocatedToInterest + form.allocatedToFees + form.allocatedToPrincipal
)

const handleCreatePayment = () => {
  const result = createPayment({ ...form })
  message.value = result.message
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
</script>
