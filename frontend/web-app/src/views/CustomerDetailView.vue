<template>
  <div>
    <div class="flex items-center gap-2 mb-4">
      <router-link to="/customers" style="color:#4a5568;text-decoration:none;">← Customers</router-link>
    </div>
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="customer">
      <div class="flex justify-between items-center mb-4">
        <h1 class="page-title" style="margin-bottom:0">{{ customer.first_name }} {{ customer.last_name }}</h1>
        <span :class="`badge badge-${customer.status}`" style="font-size:0.9rem;padding:4px 12px;">{{ customer.status }}</span>
      </div>
      <div class="card">
        <h3 style="margin-bottom:16px">Personal Information</h3>
        <div class="grid-2">
          <div><strong>Document:</strong> {{ customer.document_type }}: {{ customer.document_number }}</div>
          <div><strong>Phone:</strong> {{ customer.phone || '-' }}</div>
          <div><strong>Email:</strong> {{ customer.email || '-' }}</div>
          <div><strong>City:</strong> {{ customer.city || '-' }}</div>
          <div><strong>Address:</strong> {{ customer.address || '-' }}</div>
          <div><strong>Since:</strong> {{ new Date(customer.created_at as string).toLocaleDateString() }}</div>
        </div>
        <div v-if="customer.notes" style="margin-top:12px"><strong>Notes:</strong> {{ customer.notes }}</div>
      </div>
    </div>
    <div v-else class="card"><p>Customer not found.</p></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { customersApi } from '@/services/api'

const route = useRoute()
const customer = ref<Record<string, unknown> | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    customer.value = await customersApi.get(route.params.id as string)
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
})
</script>
