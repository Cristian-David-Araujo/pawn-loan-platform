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
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import StatCard from '../components/StatCard.vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { dashboardStats } = useMockPlatformStore()
const { t, locale } = useI18n()
const stats = computed(() => dashboardStats.value)

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )
</script>
