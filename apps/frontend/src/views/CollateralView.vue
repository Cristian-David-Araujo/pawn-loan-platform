<script setup>
import { reactive, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'
import StatusBadge from '../components/StatusBadge.vue'

const store = useLoanStore()
const error = ref('')

const form = reactive({
  loanId: '',
  description: '',
  serialNumber: '',
  appraisedValue: 0,
  physicalCondition: 'good',
  custodyCode: '',
  storageLocation: '',
})

function submit() {
  error.value = ''
  try {
    store.registerCollateral(form)
    Object.assign(form, {
      loanId: '',
      description: '',
      serialNumber: '',
      appraisedValue: 0,
      physicalCondition: 'good',
      custodyCode: '',
      storageLocation: '',
    })
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Register Collateral (Pawn Loans)</h3>
      <div class="form-grid">
        <select v-model="form.loanId">
          <option value="">Select pawn loan</option>
          <option
            v-for="loan in store.loansEnriched.filter((item) => item.loanType === 'pawn')"
            :key="loan.id"
            :value="loan.id"
          >
            {{ loan.id }} - {{ loan.customerName }}
          </option>
        </select>
        <input v-model="form.description" placeholder="Description" />
        <input v-model="form.serialNumber" placeholder="Serial/Reference" />
        <input v-model.number="form.appraisedValue" type="number" min="0" placeholder="Appraised value" />
        <input v-model="form.custodyCode" placeholder="Custody code" />
        <input v-model="form.storageLocation" placeholder="Storage location" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary" @click="submit">Save collateral</button>
    </article>

    <article class="card">
      <h3>Collateral Inventory</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Loan</th>
              <th>Description</th>
              <th>Appraised</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in store.collateralItems" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.loanId }}</td>
              <td>{{ item.description }}</td>
              <td>{{ item.appraisedValue }}</td>
              <td><StatusBadge :status="item.status" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </section>
</template>
