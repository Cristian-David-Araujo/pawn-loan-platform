<template>
  <section>
    <h2>{{ t('payments.title') }}</h2>
    <p class="muted">{{ t('payments.subtitle') }}</p>

    <form class="card form mt-16" @submit.prevent="handleCreatePayment">
      <div class="grid grid-3">
        <label>
          {{ t('common.loan') }}
          <select v-model.number="form.loanId" required>
            <option v-for="loan in payableLoans" :key="loan.id" :value="loan.id">
              {{ t('payments.loanOption', { id: loan.id, customer: getCustomerLabel(loan.customerId) }) }}
            </option>
          </select>
        </label>
        <label>
          {{ t('payments.totalAmount') }}
          <input v-model.number="form.totalAmount" type="number" min="1" required />
        </label>
        <label>
          {{ t('payments.paymentMethod') }}
          <select v-model="form.paymentMethod" required>
            <option value="cash">{{ t('common.cash') }}</option>
            <option value="bank-transfer">{{ t('common.bankTransfer') }}</option>
            <option value="other">{{ t('common.other') }}</option>
          </select>
        </label>
        <label>
          {{ t('payments.penalty') }}
          <input v-model.number="form.allocatedToPenalty" type="number" min="0" required />
        </label>
        <label>
          {{ t('common.interest') }}
          <input v-model.number="form.allocatedToInterest" type="number" min="0" required />
        </label>
        <label>
          {{ t('common.fees') }}
          <input v-model.number="form.allocatedToFees" type="number" min="0" required />
        </label>
        <label>
          {{ t('common.principal') }}
          <input v-model.number="form.allocatedToPrincipal" type="number" min="0" required />
        </label>
      </div>
      <button class="btn" type="submit">{{ t('payments.registerPayment') }}</button>
      <p class="notice">{{ t('payments.allocationSummary', { sum: allocationSum, total: form.totalAmount }) }}</p>
      <p v-if="message" class="notice">{{ message }}</p>
    </form>

    <div class="card mt-16">
      <div class="table-toolbar">
        <input v-model="search" class="table-search" type="text" :placeholder="t('payments.searchPlaceholder')" />
        <select v-model="methodFilter" class="table-select">
          <option value="all">{{ t('payments.allMethods') }}</option>
          <option value="cash">{{ t('common.cash') }}</option>
          <option value="bank-transfer">{{ t('common.bankTransfer') }}</option>
          <option value="other">{{ t('common.other') }}</option>
        </select>
        <span class="table-count">{{ t('payments.totalPayments', { count: filteredPayments.length }) }}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.loan') }}</th>
            <th>{{ t('common.date') }}</th>
            <th>{{ t('common.total') }}</th>
            <th>{{ t('common.principal') }}</th>
            <th>{{ t('common.interest') }}</th>
            <th>{{ t('common.method') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="payment in filteredPayments" :key="payment.id">
            <td>{{ payment.id }}</td>
            <td>#{{ payment.loanId }}</td>
            <td>{{ payment.paymentDate }}</td>
            <td>{{ formatCurrency(payment.totalAmount) }}</td>
            <td>{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
            <td>{{ formatCurrency(payment.allocatedToInterest) }}</td>
            <td>
              {{
                payment.paymentMethod === 'cash'
                  ? t('common.cash')
                  : payment.paymentMethod === 'bank-transfer'
                    ? t('common.bankTransfer')
                    : t('common.other')
              }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, createPayment, getCustomerName } = useMockPlatformStore()
const { t, locale } = useI18n()
const message = ref('')
const search = ref('')
const methodFilter = ref<'all' | 'cash' | 'bank-transfer' | 'other'>('all')

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
  message.value = t(result.messageKey)
}

const getCustomerLabel = (customerId: number) => {
  const value = getCustomerName(customerId)
  return value === '__UNKNOWN_CUSTOMER__' ? t('messages.unknownCustomer') : value
}

const filteredPayments = computed(() => {
  const query = search.value.trim().toLowerCase()

  return state.payments.filter((payment) => {
    const methodMatches = methodFilter.value === 'all' || payment.paymentMethod === methodFilter.value
    const loan = state.loans.find((item) => item.id === payment.loanId)
    const customer = getCustomerLabel(loan?.customerId ?? 0).toLowerCase()
    const text = `${payment.id} ${payment.loanId} ${customer}`.toLowerCase()
    const queryMatches = !query || text.includes(query)
    return methodMatches && queryMatches
  })
})

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )
</script>
