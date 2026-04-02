<template>
  <section>
    <PageHeader :title="t('reporting.title')" :subtitle="t('reporting.subtitle')">
      <template #icon>
        <ChartNoAxesCombined :size="18" />
      </template>
    </PageHeader>

    <div class="card mt-16 form-inline">
      <label>
        {{ t('reporting.fromDate') }}
        <input v-model="fromDate" type="date" />
      </label>
      <label>
        {{ t('reporting.toDate') }}
        <input v-model="toDate" type="date" />
      </label>
      <button class="btn btn-secondary" type="button" @click="resetDates">
        <RotateCcw :size="16" />
        {{ t('reporting.resetDates') }}
      </button>
    </div>

    <div class="stats-inline mt-16">
      <span class="pill">{{ t('reporting.totalPaymentsRegistered', { count: filteredPayments.length }) }}</span>
      <span class="pill">{{ t('reporting.totalCollected', { amount: formatCurrency(totalCollected) }) }}</span>
    </div>

    <div class="grid grid-2 mt-16">
      <article class="card">
        <h3>{{ t('reporting.activeLoans') }}</h3>
        <ul>
          <li v-for="loan in activeLoans" :key="loan.id">
            {{
              t('reporting.activeLoanLine', {
                id: loan.id,
                customer: getCustomerLabel(loan.customerId),
                amount: formatCurrency(loan.outstandingPrincipal)
              })
            }}
          </li>
        </ul>
      </article>

      <article class="card">
        <h3>{{ t('reporting.overdueLoans') }}</h3>
        <ul>
          <li v-for="loan in overdueLoans" :key="loan.id">
            {{ t('reporting.overdueLoanLine', { id: loan.id, customer: getCustomerLabel(loan.customerId), day: loan.dueDay }) }}
          </li>
        </ul>
      </article>

      <article class="card">
        <h3>{{ t('reporting.collateralInCustody') }}</h3>
        <ul>
          <li v-for="item in custodyItems" :key="item.id">
            {{ t('reporting.custodyLine', { code: item.custodyCode, loanId: item.loanId, description: item.description }) }}
          </li>
        </ul>
      </article>

      <article class="card">
        <h3>{{ t('reporting.cashSummary') }}</h3>
        <p>{{ t('reporting.totalPaymentsRegistered', { count: filteredPayments.length }) }}</p>
        <p>{{ t('reporting.totalCollected', { amount: formatCurrency(totalCollected) }) }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChartNoAxesCombined, RotateCcw } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, getCustomerName, ensureInitialized } = useMockPlatformStore()
const { t, locale } = useI18n()
const currencyCode = computed(() => state.globalSettings?.currencyCode ?? 'COP')
const today = new Date().toISOString().slice(0, 10)
const fromDate = ref('')
const toDate = ref(today)

onMounted(async () => {
  await ensureInitialized()
})

const activeLoans = computed(() => state.loans.filter((loan) => loan.status === 'active'))
const overdueLoans = computed(() => state.loans.filter((loan) => loan.status === 'overdue'))
const custodyItems = computed(() => state.collateralItems.filter((item) => item.status === 'in-custody'))
const filteredPayments = computed(() => {
  return state.payments.filter((payment) => {
    const afterFrom = !fromDate.value || payment.paymentDate >= fromDate.value
    const beforeTo = !toDate.value || payment.paymentDate <= toDate.value
    return afterFrom && beforeTo
  })
})

const totalCollected = computed(() => filteredPayments.value.reduce((sum, payment) => sum + payment.totalAmount, 0))

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    style: 'currency',
    currency: currencyCode.value
  }).format(
    amount
  )

const getCustomerLabel = (customerId: number) => {
  const value = getCustomerName(customerId)
  return value === '__UNKNOWN_CUSTOMER__' ? t('messages.unknownCustomer') : value
}

const resetDates = () => {
  fromDate.value = ''
  toDate.value = today
}
</script>
