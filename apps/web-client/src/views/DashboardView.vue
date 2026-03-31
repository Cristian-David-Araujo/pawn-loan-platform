<template>
  <section>
    <h2>{{ t('dashboard.title') }}</h2>
    <p class="muted">{{ t('dashboard.subtitle') }}</p>

    <div class="grid grid-3 mt-16">
      <StatCard :label="t('dashboard.customers')" :value="stats.customers" />
      <StatCard :label="t('dashboard.activeLoans')" :value="stats.activeLoans" />
      <StatCard :label="t('dashboard.overdueLoans')" :value="stats.overdueLoans" />
      <StatCard :label="t('dashboard.collateralInCustody')" :value="stats.collateralInCustody" />
      <StatCard :label="t('dashboard.outstandingPortfolio')" :value="formatCurrency(stats.portfolioOutstanding)" />
      <StatCard :label="t('dashboard.cashCollected')" :value="formatCurrency(stats.cashCollected)" />
    </div>

    <div class="card mt-16">
      <h3>{{ t('dashboard.quickActions') }}</h3>
      <div class="quick-actions mt-16">
        <RouterLink class="btn" to="/customers">{{ t('dashboard.goCustomers') }}</RouterLink>
        <RouterLink class="btn" to="/loans">{{ t('dashboard.goLoans') }}</RouterLink>
        <RouterLink class="btn" to="/payments">{{ t('dashboard.goPayments') }}</RouterLink>
        <RouterLink class="btn" to="/reporting">{{ t('dashboard.goReporting') }}</RouterLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import StatCard from '../components/StatCard.vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { dashboardStats, ensureInitialized } = useMockPlatformStore()
const { t, locale } = useI18n()
const stats = computed(() => dashboardStats.value)

onMounted(async () => {
  await ensureInitialized()
})

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )
</script>
