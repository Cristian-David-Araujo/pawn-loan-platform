<template>
  <section>
    <PageHeader :title="t('dashboard.title')" :subtitle="t('dashboard.subtitle')">
      <template #icon>
        <LayoutDashboard :size="18" />
      </template>
    </PageHeader>

    <!-- The book: what is owed to the business right now, and how much of it is late.
         These two are the reason anyone opens this screen, so they lead and they are the
         only tiles that carry a figure at display size. -->
    <h3 class="group-title">{{ t('dashboard.theBook') }}</h3>
    <div class="grid grid-2">
      <StatCard
        :label="t('dashboard.outstandingPortfolio')"
        :value="formatCurrency(stats.portfolioOutstanding)"
        :icon="HandCoins"
        tone="indigo"
      />
      <StatCard
        :label="t('dashboard.overdueLoans')"
        :value="String(stats.overdueLoans)"
        :caption="stats.overdueLoans ? t('dashboard.overdueAmount', { amount: formatCurrency(overdueOutstanding) }) : t('dashboard.nothingOverdue')"
        :icon="ClockAlert"
        :tone="stats.overdueLoans ? 'danger' : 'green'"
        :to="stats.overdueLoans ? { path: '/loans', query: { status: 'overdue' } } : undefined"
      />
    </div>

    <!-- This month: the pulse. Quieter than the book, because it reports rather than asks. -->
    <h3 class="group-title mt-24">{{ t('dashboard.thisMonth') }}</h3>
    <div class="grid grid-3">
      <StatCard :label="t('dashboard.cashCollectedMonth')" :value="formatCurrency(stats.cashCollectedMonth)" :icon="Wallet" tone="green" />
      <StatCard :label="t('dashboard.interestCollectedMonth')" :value="formatCurrency(stats.interestCollectedMonth)" :icon="TrendingUp" tone="green" />
      <StatCard :label="t('dashboard.lentThisMonth')" :value="formatCurrency(stats.lentThisMonth)" :icon="HandCoins" tone="blue" />
    </div>

    <!-- Counts, last: they are context, not a call to act. -->
    <h3 class="group-title mt-24">{{ t('dashboard.portfolio') }}</h3>
    <div class="grid grid-3">
      <StatCard
        :label="t('dashboard.activeLoans')"
        :value="String(stats.activeLoans)"
        :icon="BadgeDollarSign"
        tone="blue"
        :to="{ path: '/loans' }"
      />
      <StatCard
        :label="t('dashboard.customers')"
        :value="String(stats.customers)"
        :icon="Users"
        tone="blue"
        :to="{ path: '/customers' }"
      />
      <StatCard
        :label="t('dashboard.collateralInCustody')"
        :value="String(stats.collateralInCustody)"
        :icon="ShieldCheck"
        tone="blue"
        :to="{ path: '/collaterals' }"
      />
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
  TrendingUp,
  Users,
  Wallet
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { usePlatformStore } from '../stores/platformStore'
import { formatCurrency } from '../utils/currency'

/**
 * The landing screen used to be eight identical tiles in a three-column grid — a ragged
 * 3+3+2 that mixed counts with money and gave the overdue figure exactly the same weight as
 * the customer count. Nothing was clickable, so a number that named a problem was a dead
 * end, and a "Quick actions" card underneath duplicated four sidebar links verbatim.
 *
 * It is now three named groups in descending order of "does this ask me to do something":
 * the book, this month, the portfolio. Tiles that correspond to a list link to it.
 */
const { state, dashboardStats, ensureInitialized } = usePlatformStore()
const { t } = useI18n()
const stats = computed(() => dashboardStats.value)

/* A count of overdue loans does not say how much is at stake. Nine small ones and one large
   one are not the same morning. */
const overdueOutstanding = computed(() =>
  state.loans
    .filter((loan) => loan.status === 'overdue')
    .reduce((sum, loan) => sum + loan.outstandingPrincipal, 0)
)

onMounted(async () => {
  await ensureInitialized()
})
</script>

<!-- `.dashboard-group-title` lived here as a scoped copy until the settings page needed the
     same thing. It is `.group-title` in main.css now. -->
