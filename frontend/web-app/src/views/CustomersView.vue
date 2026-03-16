<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="page-title" style="margin-bottom:0">Customers</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">+ New Customer</button>
    </div>

    <div class="card">
      <div class="flex gap-2 mb-4">
        <input v-model="search" placeholder="Search by name, document, email..." style="flex:1;padding:8px 12px;border:1px solid #e2e8f0;border-radius:4px;" @input="loadCustomers" />
      </div>

      <div v-if="loading" class="loading">Loading...</div>
      <table v-else class="table">
        <thead>
          <tr><th>Name</th><th>Document</th><th>Phone</th><th>City</th><th>Status</th><th>Actions</th></tr>
        </thead>
        <tbody>
          <tr v-for="c in customers" :key="c.id">
            <td>{{ c.first_name }} {{ c.last_name }}</td>
            <td>{{ c.document_type }}: {{ c.document_number }}</td>
            <td>{{ c.phone || '-' }}</td>
            <td>{{ c.city || '-' }}</td>
            <td><span :class="`badge badge-${c.status}`">{{ c.status }}</span></td>
            <td><router-link :to="`/customers/${c.id}`" class="btn btn-sm btn-primary">View</router-link></td>
          </tr>
          <tr v-if="customers.length === 0">
            <td colspan="6" style="text-align:center;color:#718096;">No customers found</td>
          </tr>
        </tbody>
      </table>
      <div v-if="total > 0" style="margin-top:12px;color:#718096;font-size:0.875rem;">Total: {{ total }} customers</div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h2 style="margin-bottom:20px">Register Customer</h2>
        <div v-if="formError" class="alert alert-error">{{ formError }}</div>
        <form @submit.prevent="createCustomer">
          <div class="grid-2">
            <div class="form-group"><label>First Name *</label><input v-model="form.first_name" required /></div>
            <div class="form-group"><label>Last Name *</label><input v-model="form.last_name" required /></div>
          </div>
          <div class="grid-2">
            <div class="form-group">
              <label>Document Type *</label>
              <select v-model="form.document_type" required>
                <option value="">Select...</option>
                <option value="CC">CC - Cédula</option>
                <option value="CE">CE - Cédula Extranjería</option>
                <option value="PASSPORT">Passport</option>
                <option value="NIT">NIT</option>
              </select>
            </div>
            <div class="form-group"><label>Document Number *</label><input v-model="form.document_number" required /></div>
          </div>
          <div class="grid-2">
            <div class="form-group"><label>Phone</label><input v-model="form.phone" /></div>
            <div class="form-group"><label>Email</label><input v-model="form.email" type="email" /></div>
          </div>
          <div class="grid-2">
            <div class="form-group"><label>City</label><input v-model="form.city" /></div>
            <div class="form-group"><label>Address</label><input v-model="form.address" /></div>
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
import { customersApi } from '@/services/api'

interface Customer {
  id: string
  first_name: string
  last_name: string
  document_type: string
  document_number: string
  phone?: string
  city?: string
  status: string
}

const customers = ref<Customer[]>([])
const total = ref(0)
const loading = ref(true)
const search = ref('')
const showCreateModal = ref(false)
const saving = ref(false)
const formError = ref('')

const form = ref({
  first_name: '', last_name: '', document_type: '', document_number: '',
  phone: '', email: '', city: '', address: ''
})

async function loadCustomers() {
  loading.value = true
  try {
    const data = await customersApi.list({ search: search.value || undefined, limit: 100 })
    customers.value = data.items || []
    total.value = data.total || 0
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function createCustomer() {
  saving.value = true
  formError.value = ''
  try {
    const payload = Object.fromEntries(Object.entries(form.value).filter(([, v]) => v !== ''))
    await customersApi.create(payload)
    showCreateModal.value = false
    form.value = { first_name: '', last_name: '', document_type: '', document_number: '', phone: '', email: '', city: '', address: '' }
    await loadCustomers()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail || 'Failed to create customer'
  } finally {
    saving.value = false
  }
}

onMounted(loadCustomers)
</script>

<style scoped>
.modal-overlay { position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:1000; }
.modal { background:white;border-radius:8px;padding:32px;width:100%;max-width:600px;max-height:90vh;overflow-y:auto; }
</style>
