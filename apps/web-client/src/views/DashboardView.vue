<template>
  <section>
    <PageHeader :title="t('dashboard.title')" :subtitle="t('dashboard.subtitle')">
      <template #icon>
        <LayoutDashboard :size="18" />
      </template>
    </PageHeader>

    <div class="grid grid-3 mt-16">
      <StatCard :label="t('dashboard.customers')" :value="stats.customers" :icon="Users" tone="indigo" />
      <StatCard :label="t('dashboard.activeLoans')" :value="stats.activeLoans" :icon="BadgeDollarSign" tone="green" />
      <StatCard :label="t('dashboard.overdueLoans')" :value="stats.overdueLoans" :icon="ClockAlert" tone="amber" />
      <StatCard :label="t('dashboard.collateralInCustody')" :value="stats.collateralInCustody" :icon="ShieldCheck" tone="blue" />
      <StatCard
        :label="t('dashboard.outstandingPortfolio')"
        :value="formatCurrency(stats.portfolioOutstanding)"
        :icon="HandCoins"
        tone="amber"
      />
      <StatCard :label="t('dashboard.cashCollected')" :value="formatCurrency(stats.cashCollected)" :icon="Wallet" tone="green" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  BadgeDollarSign,
  ClockAlert,
  HandCoins,
  LayoutDashboard,
  ShieldCheck,
  Users,
  Wallet
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
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
