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
      <StatCard :label="t('dashboard.lentThisMonth')" :value="formatCurrency(stats.lentThisMonth)" :icon="HandCoins" tone="indigo" />
      <StatCard
        :label="t('dashboard.interestCollectedMonth')"
        :value="formatCurrency(stats.interestCollectedMonth)"
        :icon="TrendingUp"
        tone="green"
      />
      <StatCard :label="t('dashboard.cashCollectedMonth')" :value="formatCurrency(stats.cashCollectedMonth)" :icon="Wallet" tone="green" />
    </div>

    <article class="card mt-16">
      <h3>{{ t('dashboard.quickActions') }}</h3>
      <div class="quick-actions mt-16">
        <button class="btn btn-secondary" type="button" @click="goTo('/customers')">
          <Users :size="15" /> {{ t('dashboard.goCustomers') }}
        </button>
        <button class="btn btn-secondary" type="button" @click="goTo('/loans')">
          <HandCoins :size="15" /> {{ t('dashboard.goLoans') }}
        </button>
        <button class="btn btn-secondary" type="button" @click="goTo('/payments')">
          <Wallet :size="15" /> {{ t('dashboard.goPayments') }}
        </button>
        <button class="btn btn-secondary" type="button" @click="goTo('/reporting')">
          <BarChart3 :size="15" /> {{ t('dashboard.goReporting') }}
        </button>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  BadgeDollarSign,
  BarChart3,
  ClockAlert,
  HandCoins,
  LayoutDashboard,
  ShieldCheck,
  TrendingUp,
  Users,
  Wallet
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { usePlatformStore } from '../stores/platformStore'

const { state, dashboardStats, ensureInitialized } = usePlatformStore()
const { t, locale } = useI18n()
const router = useRouter()
const stats = computed(() => dashboardStats.value)
const currencyCode = computed(() => state.globalSettings?.currencyCode ?? 'COP')

onMounted(async () => {
  await ensureInitialized()
})

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    style: 'currency',
    currency: currencyCode.value
  }).format(
    amount
  )

const goTo = (path: string) => {
  void router.push(path)
}
</script>
