<template>
  <section>
    <h2>{{ t('loans.title') }}</h2>
    <p class="muted">{{ t('loans.subtitle') }}</p>

    <form class="card form mt-16" @submit.prevent="handleCreateLoan">
      <div class="grid grid-3">
        <label>
          {{ t('common.customer') }}
          <select v-model.number="form.customerId" required>
            <option v-for="customer in state.customers" :key="customer.id" :value="customer.id">
              {{ customer.fullName }}
            </option>
          </select>
        </label>
        <label>
          {{ t('loans.loanType') }}
          <select v-model="form.loanType" required>
            <option value="pawn">{{ t('common.pawn') }}</option>
            <option value="personal">{{ t('common.personal') }}</option>
          </select>
        </label>
        <label>
          {{ t('loans.principalAmount') }}
          <input v-model.number="form.principalAmount" type="number" min="1" required />
        </label>
        <label>
          {{ t('loans.monthlyInterestRate') }}
          <input v-model.number="form.monthlyInterestRate" type="number" min="0" step="0.1" required />
        </label>
        <label>
          {{ t('loans.dueDay') }}
          <input v-model.number="form.dueDay" type="number" min="1" max="28" required />
        </label>
      </div>
      <button class="btn" type="submit">{{ t('loans.createLoan') }}</button>
    </form>

    <div class="card mt-16">
      <table>
        <thead>
          <tr>
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.customer') }}</th>
            <th>{{ t('common.type') }}</th>
            <th>{{ t('common.principal') }}</th>
            <th>{{ t('loans.outstanding') }}</th>
            <th>{{ t('loans.rate') }}</th>
            <th>{{ t('common.status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="loan in state.loans" :key="loan.id">
            <td>{{ loan.id }}</td>
            <td>{{ getCustomerName(loan.customerId) }}</td>
            <td>{{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
            <td>{{ formatCurrency(loan.principalAmount) }}</td>
            <td>{{ formatCurrency(loan.outstandingPrincipal) }}</td>
            <td>{{ loan.monthlyInterestRate }}%</td>
            <td>{{ t(`common.${loan.status}`) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, createLoan, getCustomerName } = useMockPlatformStore()
const { t, locale } = useI18n()

const form = reactive({
  customerId: state.customers[0]?.id ?? 1,
  loanType: 'pawn' as 'pawn' | 'personal',
  principalAmount: 1000,
  monthlyInterestRate: 8,
  dueDay: 5
})

const handleCreateLoan = () => {
  createLoan({ ...form })
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )
</script>
