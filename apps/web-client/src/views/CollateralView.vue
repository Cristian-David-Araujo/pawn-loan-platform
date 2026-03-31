<template>
  <section>
    <h2>{{ t('collateral.title') }}</h2>
    <p class="muted">{{ t('collateral.subtitle') }}</p>

    <form class="card form mt-16" @submit.prevent="handleCreateCollateral">
      <div class="grid grid-3">
        <label>
          {{ t('common.loan') }}
          <select v-model.number="form.loanId" required>
            <option v-for="loan in pawnLoans" :key="loan.id" :value="loan.id">
              {{ t('collateral.loanOption', { id: loan.id, customer: getCustomerLabel(loan.customerId) }) }}
            </option>
          </select>
        </label>
        <label>
          {{ t('common.description') }}
          <input v-model="form.description" required />
        </label>
        <label>
          {{ t('collateral.appraisedValue') }}
          <input v-model.number="form.appraisedValue" type="number" min="1" required />
        </label>
        <label>
          {{ t('collateral.storageLocation') }}
          <input v-model="form.storageLocation" required />
        </label>
      </div>
      <button class="btn" type="submit">{{ t('collateral.registerCollateralItem') }}</button>
    </form>

    <div class="card mt-16">
      <div class="table-toolbar">
        <input v-model="search" class="table-search" type="text" :placeholder="t('collateral.searchPlaceholder')" />
        <span class="table-count">{{ t('collateral.totalItems', { count: filteredCollateral.length }) }}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.loan') }}</th>
            <th>{{ t('common.description') }}</th>
            <th>{{ t('collateral.appraisedValue') }}</th>
            <th>{{ t('collateral.custodyCode') }}</th>
            <th>{{ t('collateral.location') }}</th>
            <th>{{ t('common.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredCollateral" :key="item.id">
            <td>{{ item.id }}</td>
            <td>#{{ item.loanId }}</td>
            <td>{{ item.description }}</td>
            <td>{{ formatCurrency(item.appraisedValue) }}</td>
            <td>{{ item.custodyCode }}</td>
            <td>{{ item.storageLocation }}</td>
            <td>{{ item.status === 'in-custody' ? t('common.inCustody') : t(`common.${item.status}`) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, createCollateral, getCustomerName, ensureInitialized } = useMockPlatformStore()
const { t, locale } = useI18n()
const search = ref('')

onMounted(async () => {
  await ensureInitialized()
  if (pawnLoans.value.length) {
    form.loanId = pawnLoans.value[0].id
  }
})

const pawnLoans = computed(() => state.loans.filter((loan) => loan.loanType === 'pawn'))

const form = reactive({
  loanId: pawnLoans.value[0]?.id ?? 1,
  description: '',
  appraisedValue: 1000,
  storageLocation: 'Vault A-01'
})

const handleCreateCollateral = async () => {
  if (!pawnLoans.value.length) {
    return
  }
  await createCollateral({ ...form })
  form.description = ''
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )

const getCustomerLabel = (customerId: number) => {
  const value = getCustomerName(customerId)
  return value === '__UNKNOWN_CUSTOMER__' ? t('messages.unknownCustomer') : value
}

const filteredCollateral = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) {
    return state.collateralItems
  }

  return state.collateralItems.filter((item) => {
    const customer = getCustomerLabel(state.loans.find((loan) => loan.id === item.loanId)?.customerId ?? 0).toLowerCase()
    const text = `${item.id} ${item.description} ${item.custodyCode} ${item.storageLocation} ${customer}`.toLowerCase()
    return text.includes(query)
  })
})
</script>
