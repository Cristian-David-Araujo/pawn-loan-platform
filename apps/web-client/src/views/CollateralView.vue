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
              {{ t('collateral.loanOption', { id: loan.id, customer: getCustomerName(loan.customerId) }) }}
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
          <tr v-for="item in state.collateralItems" :key="item.id">
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
import { computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, createCollateral, getCustomerName } = useMockPlatformStore()
const { t, locale } = useI18n()

const pawnLoans = computed(() => state.loans.filter((loan) => loan.loanType === 'pawn'))

const form = reactive({
  loanId: pawnLoans.value[0]?.id ?? 1,
  description: '',
  appraisedValue: 1000,
  storageLocation: 'Vault A-01'
})

const handleCreateCollateral = () => {
  if (!pawnLoans.value.length) {
    return
  }
  createCollateral({ ...form })
  form.description = ''
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )
</script>
