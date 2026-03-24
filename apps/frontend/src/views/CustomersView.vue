<script setup>
import { reactive, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'

const store = useLoanStore()
const error = ref('')

const form = reactive({
  firstName: '',
  lastName: '',
  documentType: 'ID',
  documentNumber: '',
  phone: '',
  email: '',
  city: '',
})

function submit() {
  error.value = ''
  try {
    store.createCustomer(form)
    Object.assign(form, {
      firstName: '',
      lastName: '',
      documentType: 'ID',
      documentNumber: '',
      phone: '',
      email: '',
      city: '',
    })
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Create Customer</h3>
      <div class="form-grid">
        <input v-model="form.firstName" placeholder="First name" />
        <input v-model="form.lastName" placeholder="Last name" />
        <input v-model="form.documentNumber" placeholder="Document number" />
        <input v-model="form.phone" placeholder="Phone" />
        <input v-model="form.email" placeholder="Email" />
        <input v-model="form.city" placeholder="City" />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn btn-primary" @click="submit">Save customer</button>
    </article>

    <article class="card">
      <h3>Customer List</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Document</th>
              <th>City</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in store.customers" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.firstName }} {{ item.lastName }}</td>
              <td>{{ item.documentNumber }}</td>
              <td>{{ item.city }}</td>
              <td>{{ item.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </section>
</template>
