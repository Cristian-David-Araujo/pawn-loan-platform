<template>
  <section>
    <h2>{{ t('customers.title') }}</h2>
    <p class="muted">{{ t('customers.subtitle') }}</p>

    <form class="card form mt-16" @submit.prevent="handleCreateCustomer">
      <div class="grid grid-3">
        <label>
          {{ t('customers.fullName') }}
          <input v-model="form.fullName" required />
        </label>
        <label>
          {{ t('customers.documentType') }}
          <input v-model="form.documentType" required />
        </label>
        <label>
          {{ t('customers.documentNumber') }}
          <input v-model="form.documentNumber" required />
        </label>
        <label>
          {{ t('common.phone') }}
          <input v-model="form.phone" required />
        </label>
        <label>
          {{ t('common.city') }}
          <input v-model="form.city" required />
        </label>
      </div>
      <button class="btn" type="submit">{{ t('customers.createCustomer') }}</button>
      <p v-if="message" class="notice">{{ message }}</p>
    </form>

    <div class="card mt-16">
      <table>
        <thead>
          <tr>
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('customers.document') }}</th>
            <th>{{ t('common.phone') }}</th>
            <th>{{ t('common.city') }}</th>
            <th>{{ t('common.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="customer in state.customers" :key="customer.id">
            <td>{{ customer.id }}</td>
            <td>{{ customer.fullName }}</td>
            <td>{{ customer.documentType }} / {{ customer.documentNumber }}</td>
            <td>{{ customer.phone }}</td>
            <td>{{ customer.city }}</td>
            <td>{{ customer.status === 'active' ? t('common.active') : customer.status }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, createCustomer } = useMockPlatformStore()
const { t } = useI18n()
const message = ref('')

const form = reactive({
  fullName: '',
  documentType: 'ID',
  documentNumber: '',
  phone: '',
  city: ''
})

const handleCreateCustomer = () => {
  const result = createCustomer({ ...form })
  message.value = t(result.messageKey)

  if (result.ok) {
    form.fullName = ''
    form.documentType = 'ID'
    form.documentNumber = ''
    form.phone = ''
    form.city = ''
  }
}
</script>
