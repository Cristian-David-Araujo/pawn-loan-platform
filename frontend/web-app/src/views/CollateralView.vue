<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="page-title" style="margin-bottom:0">Collateral Items</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">+ Register Item</button>
    </div>
    <div class="card">
      <div class="flex gap-2 mb-4">
        <select v-model="statusFilter" style="padding:8px 12px;border:1px solid #e2e8f0;border-radius:4px;" @change="loadItems">
          <option value="">All Statuses</option>
          <option value="received">Received</option>
          <option value="in_custody">In Custody</option>
          <option value="released">Released</option>
          <option value="under_liquidation">Under Liquidation</option>
          <option value="sold">Sold</option>
        </select>
      </div>
      <div v-if="loading" class="loading">Loading...</div>
      <table v-else class="table">
        <thead>
          <tr><th>Code</th><th>Type</th><th>Description</th><th>Appraised Value</th><th>Status</th><th>Actions</th></tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.custody_code || '-' }}</td>
            <td>{{ item.item_type }}</td>
            <td>{{ item.description }}</td>
            <td>{{ formatCurrency(item.appraised_value) }}</td>
            <td><span :class="`badge badge-${item.status === 'in_custody' || item.status === 'received' ? 'active' : 'inactive'}`">{{ item.status }}</span></td>
            <td class="flex gap-2">
              <button v-if="item.status !== 'released'" class="btn btn-sm btn-success" @click="releaseItem(item.id)">Release</button>
              <button v-if="item.status !== 'released' && item.status !== 'sold'" class="btn btn-sm btn-danger" @click="liquidateItem(item.id)">Liquidate</button>
            </td>
          </tr>
          <tr v-if="items.length === 0"><td colspan="6" style="text-align:center;color:#718096;">No items found</td></tr>
        </tbody>
      </table>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h2 style="margin-bottom:20px">Register Collateral Item</h2>
        <div v-if="formError" class="alert alert-error">{{ formError }}</div>
        <form @submit.prevent="createItem">
          <div class="form-group"><label>Loan ID *</label><input v-model="form.loan_id" required placeholder="UUID" /></div>
          <div class="grid-2">
            <div class="form-group"><label>Item Type *</label><input v-model="form.item_type" required /></div>
            <div class="form-group"><label>Appraised Value *</label><input v-model="form.appraised_value" type="number" step="0.01" required /></div>
          </div>
          <div class="form-group"><label>Description *</label><input v-model="form.description" required /></div>
          <div class="grid-2">
            <div class="form-group"><label>Serial Number</label><input v-model="form.serial_number" /></div>
            <div class="form-group"><label>Custody Code</label><input v-model="form.custody_code" /></div>
          </div>
          <div class="grid-2">
            <div class="form-group"><label>Physical Condition</label><input v-model="form.physical_condition" placeholder="good / fair / poor" /></div>
            <div class="form-group"><label>Storage Location</label><input v-model="form.storage_location" /></div>
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
import { collateralApi } from '@/services/api'

interface CollateralItem {
  id: string
  custody_code?: string
  item_type: string
  description: string
  appraised_value: number
  status: string
}

const items = ref<CollateralItem[]>([])
const loading = ref(true)
const statusFilter = ref('')
const showCreateModal = ref(false)
const saving = ref(false)
const formError = ref('')
const form = ref({ loan_id: '', item_type: '', description: '', appraised_value: '', serial_number: '', custody_code: '', physical_condition: '', storage_location: '' })

function formatCurrency(v: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0)
}

async function loadItems() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (statusFilter.value) params.status = statusFilter.value
    const data = await collateralApi.list({ ...params, limit: 100 })
    items.value = data.items || []
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function createItem() {
  saving.value = true
  formError.value = ''
  try {
    const payload: Record<string, unknown> = Object.fromEntries(Object.entries(form.value).filter(([, v]) => v !== ''))
    payload.appraised_value = parseFloat(form.value.appraised_value)
    await collateralApi.create(payload)
    showCreateModal.value = false
    await loadItems()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail || 'Failed to register item'
  } finally {
    saving.value = false
  }
}

async function releaseItem(id: string) {
  if (!confirm('Release this collateral item?')) return
  try {
    await collateralApi.release(id)
    await loadItems()
  } catch {
    alert('Failed to release item')
  }
}

async function liquidateItem(id: string) {
  const amount = prompt('Sale amount (leave empty to mark as under liquidation):')
  try {
    await collateralApi.liquidate(id, amount ? parseFloat(amount) : undefined)
    await loadItems()
  } catch {
    alert('Failed to liquidate item')
  }
}

onMounted(loadItems)
</script>

<style scoped>
.modal-overlay { position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:1000; }
.modal { background:white;border-radius:8px;padding:32px;width:100%;max-width:560px;max-height:90vh;overflow-y:auto; }
</style>
