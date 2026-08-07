<template>
  <section>
    <PageHeader :title="t('reporting.title')" :subtitle="t('reporting.subtitle')">
      <template #icon>
        <ChartNoAxesCombined :size="18" />
      </template>
    </PageHeader>

    <div class="card customer-gate mt-16">
      <label>
        {{ t('reporting.fromDate') }}
        <DateInputField v-model="fromDate" :label="t('reporting.fromDate')" :placeholder="datePlaceholder" :title="t('reporting.fromDate')" />
      </label>
      <label>
        {{ t('reporting.toDate') }}
        <DateInputField v-model="toDate" :label="t('reporting.toDate')" :placeholder="datePlaceholder" :title="t('reporting.toDate')" />
      </label>
      <button class="btn btn-secondary" type="button" @click="resetDates">
        <RotateCcw :size="16" />
        {{ t('reporting.resetDates') }}
      </button>
    </div>

    <div class="grid grid-4 mt-16">
      <StatCard :label="t('reporting.parLabel')" :value="formatPercent(portfolioHealth.par)" :icon="AlertTriangle" :tone="portfolioHealth.par > 15 ? 'amber' : 'green'" />
      <StatCard :label="t('reporting.pendingInterestLabel')" :value="formatCurrency(portfolioHealth.pendingInterest)" :icon="HandCoins" tone="indigo" />
      <StatCard :label="t('reporting.topConcentrationLabel')" :value="formatPercent(portfolioHealth.topConcentration)" :icon="PieChart" :tone="portfolioHealth.topConcentration > 40 ? 'amber' : 'blue'" />
      <StatCard :label="t('reporting.collateralCoverageLabel')" :value="formatPercent(portfolioHealth.collateralCoverage)" :icon="ShieldCheck" :tone="portfolioHealth.collateralCoverage < 100 ? 'amber' : 'green'" />
    </div>

    <div class="grid grid-3 mt-16">
      <StatCard :label="t('reporting.totalCollectedLabel')" :value="formatCurrency(totalCollected)" :icon="Wallet" tone="green" />
      <StatCard :label="t('reporting.totalInterestCollectedLabel')" :value="formatCurrency(totalInterestCollected)" :icon="BadgeDollarSign" tone="blue" />
      <StatCard :label="t('reporting.totalPenaltyCollectedLabel')" :value="formatCurrency(totalPenaltyCollected)" :icon="ClockAlert" tone="amber" />
      <StatCard :label="t('reporting.disbursedInRange')" :value="formatCurrency(cashFlow.disbursed)" :icon="HandCoins" tone="indigo" />
      <StatCard :label="t('reporting.netCashFlow')" :value="formatCurrency(cashFlow.net)" :icon="CircleDollarSign" :tone="cashFlow.net >= 0 ? 'green' : 'amber'" />
      <StatCard :label="t('reporting.realizedYield')" :value="formatPercent(realizedYield)" :icon="TrendingUp" tone="blue" />
    </div>

    <div class="grid grid-2 mt-16">
      <article class="card">
        <h3>{{ t('reporting.collectionTrend') }}</h3>
        <p class="muted">{{ t('reporting.collectionTrendHint') }}</p>
        <div v-if="incomeChart.bars.length" class="report-chart mt-16">
          <svg class="chart-svg" viewBox="0 0 100 64" role="img" :aria-label="t('reporting.collectionTrend')">
            <line class="chart-axis" x1="12" y1="50" x2="96" y2="50" />
            <line class="chart-axis" x1="12" y1="4" x2="12" y2="50" />
            <line
              v-for="tick in incomeChart.yTicks"
              :key="`income-y-${tick.value}`"
              class="chart-grid"
              x1="12"
              :y1="tick.y"
              x2="96"
              :y2="tick.y"
            />
            <text v-for="tick in incomeChart.yTicks" :key="`income-y-label-${tick.value}`" class="chart-y-label" x="10" :y="tick.y">
              {{ formatCompactNumber(tick.value) }}
            </text>
            <rect
              v-for="bar in incomeChart.bars"
              :key="`income-bar-${bar.label}`"
              class="chart-bar"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
            >
              <title>{{ t('reporting.chartTooltip', { period: bar.label, value: formatCurrency(bar.value) }) }}</title>
            </rect>
            <text v-for="tick in incomeChart.xTicks" :key="`income-x-${tick.index}`" class="chart-x-label" :x="tick.x" y="58">
              {{ tick.label }}
            </text>
          </svg>
        </div>
        <p v-else class="muted mt-16">{{ t('reporting.noDataRange') }}</p>
      </article>

      <article class="card">
        <h3>{{ t('reporting.collectionComposition') }}</h3>
        <p class="muted">{{ t('reporting.collectionCompositionHint') }}</p>
        <div v-if="collectionCompositionChart.bars.length" class="report-chart mt-16">
          <svg class="chart-svg" viewBox="0 0 100 64" role="img" :aria-label="t('reporting.collectionComposition')">
            <line class="chart-axis" x1="12" y1="50" x2="96" y2="50" />
            <line class="chart-axis" x1="12" y1="4" x2="12" y2="50" />
            <line
              v-for="tick in collectionCompositionChart.yTicks"
              :key="`composition-y-${tick.value}`"
              class="chart-grid"
              x1="12"
              :y1="tick.y"
              x2="96"
              :y2="tick.y"
            />
            <text
              v-for="tick in collectionCompositionChart.yTicks"
              :key="`composition-y-label-${tick.value}`"
              class="chart-y-label"
              x="10"
              :y="tick.y"
            >
              {{ formatCompactNumber(tick.value) }}
            </text>
            <rect
              v-for="bar in collectionCompositionChart.bars"
              :key="`composition-bar-${bar.label}`"
              class="chart-bar"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
            >
              <title>{{ t('reporting.chartTooltip', { period: bar.label, value: formatCurrency(bar.value) }) }}</title>
            </rect>
            <text v-for="tick in collectionCompositionChart.xTicks" :key="`composition-x-${tick.index}`" class="chart-x-label" :x="tick.x" y="58">
              {{ tick.label }}
            </text>
          </svg>
        </div>
        <p v-else class="muted mt-16">{{ t('reporting.noDataRange') }}</p>
      </article>
    </div>

    <div class="grid grid-3 mt-16">
      <article class="card">
        <h3>{{ t('reporting.disbursementTrend') }}</h3>
        <p class="muted">{{ t('reporting.disbursementTrendHint') }}</p>
        <div v-if="disbursementChart.bars.length" class="report-chart mt-16">
          <svg class="chart-svg" viewBox="0 0 100 64" role="img" :aria-label="t('reporting.disbursementTrend')">
            <line class="chart-axis" x1="12" y1="50" x2="96" y2="50" />
            <line class="chart-axis" x1="12" y1="4" x2="12" y2="50" />
            <line
              v-for="tick in disbursementChart.yTicks"
              :key="`disbursement-y-${tick.value}`"
              class="chart-grid"
              x1="12"
              :y1="tick.y"
              x2="96"
              :y2="tick.y"
            />
            <text
              v-for="tick in disbursementChart.yTicks"
              :key="`disbursement-y-label-${tick.value}`"
              class="chart-y-label"
              x="10"
              :y="tick.y"
            >
              {{ formatCompactNumber(tick.value) }}
            </text>
            <rect
              v-for="bar in disbursementChart.bars"
              :key="`disbursement-bar-${bar.label}`"
              class="chart-bar"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
            >
              <title>{{ t('reporting.chartTooltip', { period: bar.label, value: formatCurrency(bar.value) }) }}</title>
            </rect>
            <text v-for="tick in disbursementChart.xTicks" :key="`disbursement-x-${tick.index}`" class="chart-x-label" :x="tick.x" y="58">
              {{ tick.label }}
            </text>
          </svg>
        </div>
        <p v-else class="muted mt-16">{{ t('reporting.noDataRange') }}</p>
      </article>

      <article class="card">
        <h3>{{ t('reporting.loanCreationTrend') }}</h3>
        <p class="muted">{{ t('reporting.loanCreationTrendHint') }}</p>
        <div v-if="loanCreationChart.bars.length" class="report-chart mt-16">
          <svg class="chart-svg" viewBox="0 0 100 64" role="img" :aria-label="t('reporting.loanCreationTrend')">
            <line class="chart-axis" x1="12" y1="50" x2="96" y2="50" />
            <line class="chart-axis" x1="12" y1="4" x2="12" y2="50" />
            <line
              v-for="tick in loanCreationChart.yTicks"
              :key="`loan-creation-y-${tick.value}`"
              class="chart-grid"
              x1="12"
              :y1="tick.y"
              x2="96"
              :y2="tick.y"
            />
            <text
              v-for="tick in loanCreationChart.yTicks"
              :key="`loan-creation-y-label-${tick.value}`"
              class="chart-y-label"
              x="10"
              :y="tick.y"
            >
              {{ formatCompactNumber(tick.value) }}
            </text>
            <rect
              v-for="bar in loanCreationChart.bars"
              :key="`loan-creation-bar-${bar.label}`"
              class="chart-bar"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
            >
              <title>{{ t('reporting.chartTooltipCount', { period: bar.label, value: formatInteger(bar.value) }) }}</title>
            </rect>
            <text v-for="tick in loanCreationChart.xTicks" :key="`loan-creation-x-${tick.index}`" class="chart-x-label" :x="tick.x" y="58">
              {{ tick.label }}
            </text>
          </svg>
        </div>
        <p v-else class="muted mt-16">{{ t('reporting.noDataRange') }}</p>
      </article>

      <article class="card">
        <h3>{{ t('reporting.principalRecoveryTrend') }}</h3>
        <p class="muted">{{ t('reporting.principalRecoveryTrendHint') }}</p>
        <div v-if="principalRecoveryChart.bars.length" class="report-chart mt-16">
          <svg class="chart-svg" viewBox="0 0 100 64" role="img" :aria-label="t('reporting.principalRecoveryTrend')">
            <line class="chart-axis" x1="12" y1="50" x2="96" y2="50" />
            <line class="chart-axis" x1="12" y1="4" x2="12" y2="50" />
            <line
              v-for="tick in principalRecoveryChart.yTicks"
              :key="`principal-recovery-y-${tick.value}`"
              class="chart-grid"
              x1="12"
              :y1="tick.y"
              x2="96"
              :y2="tick.y"
            />
            <text
              v-for="tick in principalRecoveryChart.yTicks"
              :key="`principal-recovery-y-label-${tick.value}`"
              class="chart-y-label"
              x="10"
              :y="tick.y"
            >
              {{ formatCompactNumber(tick.value) }}
            </text>
            <rect
              v-for="bar in principalRecoveryChart.bars"
              :key="`principal-recovery-bar-${bar.label}`"
              class="chart-bar"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
            >
              <title>{{ t('reporting.chartTooltip', { period: bar.label, value: formatCurrency(bar.value) }) }}</title>
            </rect>
            <text
              v-for="tick in principalRecoveryChart.xTicks"
              :key="`principal-recovery-x-${tick.index}`"
              class="chart-x-label"
              :x="tick.x"
              y="58"
            >
              {{ tick.label }}
            </text>
          </svg>
        </div>
        <p v-else class="muted mt-16">{{ t('reporting.noDataRange') }}</p>
      </article>
    </div>

    <div class="grid grid-2 mt-16">
      <article class="card">
        <h3>{{ t('reporting.topDebtors') }}</h3>
        <p class="muted">{{ t('reporting.topDebtorsHint') }}</p>
        <div class="table-wrap mt-16">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.customer') }}</th>
                <th class="text-center">{{ t('reporting.loansCount') }}</th>
                <th class="text-right">{{ t('reporting.outstandingBalance') }}</th>
                <th class="text-right">{{ t('reporting.pendingInterestLabel') }}</th>
                <th class="text-right">{{ t('reporting.portfolioShare') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="debtor in topDebtors" :key="debtor.customerId">
                <td>{{ debtor.customerName }}</td>
                <td class="text-center">{{ debtor.loansCount }}</td>
                <td class="text-right">{{ formatCurrency(debtor.outstanding) }}</td>
                <td class="text-right">{{ formatCurrency(debtor.pendingInterest) }}</td>
                <td class="text-right">
                  <span :class="['pill', debtor.share > 20 ? 'pill-warning' : 'pill-upcoming']">{{ formatPercent(debtor.share) }}</span>
                </td>
              </tr>
              <tr v-if="!topDebtors.length">
                <td colspan="5" class="muted">{{ t('reporting.noDataRange') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="card">
        <h3>{{ t('reporting.overdueLoans') }}</h3>
        <p class="muted">{{ t('reporting.overdueLoansHint') }}</p>
        <div class="table-wrap mt-16">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.id') }}</th>
                <th>{{ t('common.customer') }}</th>
                <th class="text-right">{{ t('reporting.outstandingBalance') }}</th>
                <th class="text-right">{{ t('reporting.pendingInterestLabel') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="loan in topOverdueLoans" :key="loan.id">
                <td>#{{ loan.id }}</td>
                <td>{{ getCustomerLabel(loan.customerId) }}</td>
                <td class="text-right">{{ formatCurrency(loan.outstandingPrincipal) }}</td>
                <td class="text-right text-warning-dark fw-bold">{{ formatCurrency(loan.interestDue ?? 0) }}</td>
              </tr>
              <tr v-if="!topOverdueLoans.length">
                <td colspan="4" class="muted">{{ t('reporting.noDataRange') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="card">
        <h3>{{ t('reporting.collateralAndForeclosure') }}</h3>
        <p class="muted">{{ t('reporting.collateralAndForeclosureHint') }}</p>
        <div class="table-wrap mt-16">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.status') }}</th>
                <th class="text-center">{{ t('reporting.itemsCount') }}</th>
                <th class="text-right">{{ t('reporting.appraisedValue') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="pill pill-upcoming">{{ t('collaterals.statusInCustody') }}</span></td>
                <td class="text-center">{{ collateralSummary.custodyCount }}</td>
                <td class="text-right">{{ formatCurrency(collateralSummary.custodyValue) }}</td>
              </tr>
              <tr>
                <td><span class="pill pill-warning">{{ t('collaterals.statusForSale') }}</span></td>
                <td class="text-center">{{ collateralSummary.forSaleCount }}</td>
                <td class="text-right">{{ formatCurrency(collateralSummary.forSaleValue) }}</td>
              </tr>
              <tr>
                <td><span class="pill pill-current">{{ t('collaterals.statusSold') }}</span></td>
                <td class="text-center">{{ collateralSummary.soldCount }}</td>
                <td class="text-right">{{ formatCurrency(collateralSummary.soldRecovered) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted mt-16">
          {{ t('reporting.saleVsAppraisal', { value: formatPercent(collateralSummary.saleVsAppraisal) }) }}
        </p>
      </article>

      <article class="card">
        <h3>{{ t('reporting.topCollectors') }}</h3>
        <p class="muted">{{ t('reporting.topCollectorsHint') }}</p>
        <div class="table-wrap mt-16">
          <table>
            <thead>
              <tr>
                <th>{{ t('common.customer') }}</th>
                <th class="text-right">{{ t('reporting.totalCollectedLabel') }}</th>
                <th class="text-right">{{ t('reporting.collectedShare') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in topCustomersByCollection" :key="item.customerId">
                <td>{{ item.customerName }}</td>
                <td class="text-right">{{ formatCurrency(item.totalCollected) }}</td>
                <td class="text-right">
                  <span class="pill pill-current">{{ formatPercent(totalCollected ? (item.totalCollected / totalCollected) * 100 : 0) }}</span>
                </td>
              </tr>
              <tr v-if="!topCustomersByCollection.length">
                <td colspan="3" class="muted">{{ t('reporting.noDataRange') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </div>

    <article class="card mt-16">
      <h3>{{ t('reporting.actionableInsights') }}</h3>
      <p class="muted">{{ t('reporting.actionableInsightsHint') }}</p>
      <ul class="insight-list mt-16">
        <li v-for="insight in actionableInsights" :key="insight.text" class="insight-item">
          <component :is="insight.icon" :size="16" :class="`insight-icon insight-${insight.level}`" />
          <span>{{ insight.text }}</span>
        </li>
      </ul>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  AlertTriangle,
  BadgeDollarSign,
  ChartNoAxesCombined,
  CheckCircle2,
  CircleDollarSign,
  ClockAlert,
  HandCoins,
  Info,
  PieChart,
  RotateCcw,
  ShieldCheck,
  TrendingUp,
  Wallet
} from 'lucide-vue-next'
import DateInputField from '../components/DateInputField.vue'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { usePlatformStore } from '../stores/platformStore'
import { useCustomerLabel } from '../composables/useCustomerLabel'
import { formatCompactNumber, formatCurrency, formatInteger } from '../utils/currency'
import { formatDateDMY, getGlobalDateFormat, toIsoDate } from '../utils/date'

const { state, ensureInitialized } = usePlatformStore()
const { customerLabel: getCustomerLabel } = useCustomerLabel()
const { t, locale } = useI18n()

interface ChartEntry {
  label: string
  amount: number
}

interface ChartTick {
  value: number
  y: number
}

interface ChartXTick {
  index: number
  label: string
  x: number
}

interface ChartBar {
  label: string
  value: number
  x: number
  y: number
  width: number
  height: number
}

interface ChartModel {
  yTicks: ChartTick[]
  xTicks: ChartXTick[]
  bars: ChartBar[]
}

const today = new Date().toISOString().slice(0, 10)
const firstDayOfMonth = `${today.slice(0, 7)}-01`
const fromDate = ref(formatDateDMY(firstDayOfMonth))
const toDate = ref(formatDateDMY(today))
const datePlaceholder = computed(() => getGlobalDateFormat())

const fromDateIso = computed(() => toIsoDate(fromDate.value))
const toDateIso = computed(() => toIsoDate(toDate.value) ?? today)

onMounted(async () => {
  await ensureInitialized()
})

const overdueLoans = computed(() =>
  [...state.loans.filter((loan) => loan.status === 'overdue')].sort(
    (a, b) => new Date(b.disbursementDate).getTime() - new Date(a.disbursementDate).getTime()
  )
)
const custodyItems = computed(() => state.collateralItems.filter((item) => item.status === 'in-custody'))
const filteredLoansByDisbursement = computed(() =>
  state.loans.filter((loan) => {
    const loanIso = toIsoDate(loan.disbursementDate)
    if (!loanIso) {
      return false
    }

    return isInSelectedRange(loanIso)
  })
)

const isInSelectedRange = (isoDate: string) => {
  const afterFrom = !fromDate.value || !fromDateIso.value || isoDate >= fromDateIso.value
  const beforeTo = !toDate.value || !toDateIso.value || isoDate <= toDateIso.value
  return afterFrom && beforeTo
}

const filteredPayments = computed(() => {
  return state.payments
    .filter((payment) => {
      const paymentIso = toIsoDate(payment.paymentDate)
      if (!paymentIso) {
        return false
      }

      return isInSelectedRange(paymentIso)
    })
    .sort((a, b) => new Date(b.paymentDate).getTime() - new Date(a.paymentDate).getTime())
})

const totalCollected = computed(() => filteredPayments.value.reduce((sum, payment) => sum + payment.totalAmount, 0))
const totalInterestCollected = computed(() =>
  filteredPayments.value.reduce((sum, payment) => sum + payment.allocatedToInterest, 0)
)
const totalPenaltyCollected = computed(() =>
  filteredPayments.value.reduce((sum, payment) => sum + payment.allocatedToPenalty, 0)
)

const openLoans = computed(() => state.loans.filter((loan) => loan.status === 'active' || loan.status === 'overdue'))

const portfolioHealth = computed(() => {
  const outstandingTotal = openLoans.value.reduce((sum, loan) => sum + loan.outstandingPrincipal, 0)
  const overdueOutstanding = overdueLoans.value.reduce((sum, loan) => sum + loan.outstandingPrincipal, 0)
  const pendingInterest = openLoans.value.reduce((sum, loan) => sum + (loan.interestDue ?? 0), 0)

  const byCustomer = new Map<number, number>()
  for (const loan of openLoans.value) {
    byCustomer.set(loan.customerId, (byCustomer.get(loan.customerId) ?? 0) + loan.outstandingPrincipal)
  }
  const topFive = [...byCustomer.values()].sort((a, b) => b - a).slice(0, 5)
  const topConcentration = outstandingTotal ? (topFive.reduce((sum, v) => sum + v, 0) / outstandingTotal) * 100 : 0

  const custodyValue = custodyItems.value.reduce((sum, item) => sum + item.appraisedValue, 0)
  const collateralCoverage = outstandingTotal ? (custodyValue / outstandingTotal) * 100 : 0

  return {
    par: outstandingTotal ? (overdueOutstanding / outstandingTotal) * 100 : 0,
    pendingInterest,
    topConcentration,
    collateralCoverage,
    outstandingTotal,
    overdueOutstanding
  }
})

const cashFlow = computed(() => {
  const disbursed = filteredLoansByDisbursement.value.reduce((sum, loan) => sum + loan.principalAmount, 0)
  return {
    disbursed,
    collected: totalCollected.value,
    net: totalCollected.value - disbursed
  }
})

const realizedYield = computed(() => {
  const outstanding = portfolioHealth.value.outstandingTotal
  if (!outstanding) {
    return 0
  }
  return (totalInterestCollected.value / outstanding) * 100
})

const topDebtors = computed(() => {
  const byCustomer = new Map<number, { outstanding: number; pendingInterest: number; loansCount: number }>()

  for (const loan of openLoans.value) {
    const entry = byCustomer.get(loan.customerId) ?? { outstanding: 0, pendingInterest: 0, loansCount: 0 }
    entry.outstanding += loan.outstandingPrincipal
    entry.pendingInterest += loan.interestDue ?? 0
    entry.loansCount += 1
    byCustomer.set(loan.customerId, entry)
  }

  const outstandingTotal = portfolioHealth.value.outstandingTotal

  return [...byCustomer.entries()]
    .map(([customerId, entry]) => ({
      customerId,
      customerName: getCustomerLabel(customerId),
      ...entry,
      share: outstandingTotal ? (entry.outstanding / outstandingTotal) * 100 : 0
    }))
    .sort((a, b) => b.outstanding - a.outstanding)
    .slice(0, 5)
})

const topOverdueLoans = computed(() =>
  [...overdueLoans.value].sort((a, b) => (b.interestDue ?? 0) - (a.interestDue ?? 0)).slice(0, 5)
)

const collateralSummary = computed(() => {
  const custody = state.collateralItems.filter((item) => item.status === 'in-custody')
  const forSale = state.collateralItems.filter((item) => item.status === 'for_sale')
  const sold = state.collateralItems.filter((item) => item.status === 'sold')

  const soldAppraised = sold.reduce((sum, item) => sum + item.appraisedValue, 0)
  const soldRecovered = sold.reduce((sum, item) => sum + (item.salePrice ?? 0), 0)

  return {
    custodyCount: custody.length,
    custodyValue: custody.reduce((sum, item) => sum + item.appraisedValue, 0),
    forSaleCount: forSale.length,
    forSaleValue: forSale.reduce((sum, item) => sum + item.appraisedValue, 0),
    soldCount: sold.length,
    soldRecovered,
    saleVsAppraisal: soldAppraised ? (soldRecovered / soldAppraised) * 100 : 0
  }
})

const incomeSeries = computed(() => {
  const byMonth = new Map<string, number>()

  for (const payment of filteredPayments.value) {
    const paymentIso = toIsoDate(payment.paymentDate)
    if (!paymentIso) {
      continue
    }

    const monthKey = paymentIso.slice(0, 7)
    byMonth.set(monthKey, (byMonth.get(monthKey) ?? 0) + payment.totalAmount)
  }

  return mapMonthlySeries(byMonth)
})

const disbursementSeries = computed(() => {
  const byMonth = new Map<string, number>()

  for (const loan of filteredLoansByDisbursement.value) {
    const disbursementIso = toIsoDate(loan.disbursementDate)
    if (!disbursementIso) {
      continue
    }

    const monthKey = disbursementIso.slice(0, 7)
    byMonth.set(monthKey, (byMonth.get(monthKey) ?? 0) + loan.principalAmount)
  }

  return mapMonthlySeries(byMonth)
})

const loanCreationSeries = computed(() => {
  const byMonth = new Map<string, number>()

  for (const loan of filteredLoansByDisbursement.value) {
    const disbursementIso = toIsoDate(loan.disbursementDate)
    if (!disbursementIso) {
      continue
    }

    const monthKey = disbursementIso.slice(0, 7)
    byMonth.set(monthKey, (byMonth.get(monthKey) ?? 0) + 1)
  }

  return mapMonthlySeries(byMonth)
})

const principalRecoverySeries = computed(() => {
  const byMonth = new Map<string, number>()

  for (const payment of filteredPayments.value) {
    const paymentIso = toIsoDate(payment.paymentDate)
    if (!paymentIso) {
      continue
    }

    const monthKey = paymentIso.slice(0, 7)
    byMonth.set(monthKey, (byMonth.get(monthKey) ?? 0) + payment.allocatedToPrincipal)
  }

  return mapMonthlySeries(byMonth)
})

const collectionBreakdown = computed(() => {
  return [
    { label: t('common.interest'), amount: totalInterestCollected.value },
    { label: t('payments.penalty'), amount: totalPenaltyCollected.value },
    {
      label: t('common.principal'),
      amount: filteredPayments.value.reduce((sum, payment) => sum + payment.allocatedToPrincipal, 0)
    }
  ]
})

const incomeChart = computed(() => createBarChartModel(incomeSeries.value))
const collectionCompositionChart = computed(() => createBarChartModel(collectionBreakdown.value))
const disbursementChart = computed(() => createBarChartModel(disbursementSeries.value))
const loanCreationChart = computed(() => createBarChartModel(loanCreationSeries.value))
const principalRecoveryChart = computed(() => createBarChartModel(principalRecoverySeries.value))

const topCustomersByCollection = computed(() => {
  const byCustomer = new Map<number, number>()

  for (const payment of filteredPayments.value) {
    const loan = state.loans.find((item) => item.id === payment.loanId)
    if (!loan) {
      continue
    }

    byCustomer.set(loan.customerId, (byCustomer.get(loan.customerId) ?? 0) + payment.totalAmount)
  }

  return [...byCustomer.entries()]
    .map(([customerId, total]) => ({
      customerId,
      customerName: getCustomerLabel(customerId),
      totalCollected: total
    }))
    .sort((a, b) => b.totalCollected - a.totalCollected)
    .slice(0, 5)
})

const actionableInsights = computed(() => {
  const insights: { text: string; icon: typeof Info; level: 'good' | 'warning' | 'info' }[] = []
  const health = portfolioHealth.value

  insights.push({
    icon: health.par > 15 ? AlertTriangle : CheckCircle2,
    level: health.par > 15 ? 'warning' : 'good',
    text: t('reporting.insightPar', { value: formatPercent(health.par), amount: formatCurrency(health.overdueOutstanding) })
  })

  if (health.pendingInterest > totalInterestCollected.value) {
    insights.push({
      icon: AlertTriangle,
      level: 'warning',
      text: t('reporting.insightPendingInterest', { amount: formatCurrency(health.pendingInterest) })
    })
  } else {
    insights.push({
      icon: CheckCircle2,
      level: 'good',
      text: t('reporting.insightInterestHealthy', { amount: formatCurrency(totalInterestCollected.value) })
    })
  }

  insights.push({
    icon: health.topConcentration > 40 ? AlertTriangle : Info,
    level: health.topConcentration > 40 ? 'warning' : 'info',
    text: t('reporting.insightConcentration', { value: formatPercent(health.topConcentration) })
  })

  insights.push({
    icon: health.collateralCoverage < 100 ? AlertTriangle : CheckCircle2,
    level: health.collateralCoverage < 100 ? 'warning' : 'good',
    text: t('reporting.insightCollateralCoverage', { value: formatPercent(health.collateralCoverage) })
  })

  insights.push({
    icon: cashFlow.value.net >= 0 ? CheckCircle2 : Info,
    level: cashFlow.value.net >= 0 ? 'good' : 'info',
    text: t('reporting.insightNetFlow', {
      collected: formatCurrency(cashFlow.value.collected),
      disbursed: formatCurrency(cashFlow.value.disbursed),
      net: formatCurrency(cashFlow.value.net)
    })
  })

  const avgTicket = filteredPayments.value.length ? totalCollected.value / filteredPayments.value.length : 0
  insights.push({
    icon: Info,
    level: 'info',
    text: t('reporting.insightAverageTicket', { amount: formatCurrency(avgTicket) })
  })

  return insights
})

const formatMonthLabel = (month: string) =>
  new Intl.DateTimeFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    month: 'short',
    year: 'numeric'
  }).format(new Date(`${month}-01T00:00:00`))

const mapMonthlySeries = (seriesByMonth: Map<string, number>) => {
  const entries = [...seriesByMonth.entries()].sort(([a], [b]) => a.localeCompare(b))

  return entries.map(([month, amount]) => ({
    label: formatMonthLabel(month),
    amount
  }))
}

const toNiceMax = (value: number) => {
  if (value <= 0) {
    return 1
  }

  const exponent = Math.floor(Math.log10(value))
  const base = 10 ** exponent
  const normalized = value / base

  if (normalized <= 1) {
    return base
  }

  if (normalized <= 2) {
    return 2 * base
  }

  if (normalized <= 5) {
    return 5 * base
  }

  return 10 * base
}

const createBarChartModel = (series: ChartEntry[]): ChartModel => {
  if (!series.length) {
    return { yTicks: [], xTicks: [], bars: [] }
  }

  const left = 12
  const right = 96
  const top = 4
  const bottom = 50
  const chartHeight = bottom - top
  const chartWidth = right - left

  const maxValue = series.reduce((max, item) => Math.max(max, item.amount), 0)
  const yMax = toNiceMax(maxValue)
  const ySteps = 4

  const yTicks = Array.from({ length: ySteps + 1 }, (_, index) => {
    const value = (yMax / ySteps) * index
    const y = bottom - (value / yMax) * chartHeight
    return { value, y }
  })

  const slotWidth = chartWidth / series.length
  const barWidth = Math.max(Math.min(slotWidth * 0.62, 7.5), 1.5)

  const bars = series.map((item, index) => {
    const normalized = yMax > 0 ? item.amount / yMax : 0
    const height = Math.max(normalized * chartHeight, 0)
    const x = left + index * slotWidth + (slotWidth - barWidth) / 2
    const y = bottom - height
    return {
      label: item.label,
      value: item.amount,
      x,
      y,
      width: barWidth,
      height
    }
  })

  const targetXLabels = 6
  const tickStep = Math.max(Math.ceil(series.length / targetXLabels), 1)
  const xTicks: ChartXTick[] = []

  for (let index = 0; index < series.length; index += tickStep) {
    const x = left + index * slotWidth + slotWidth / 2
    xTicks.push({
      index,
      label: series[index].label,
      x
    })
  }

  if (series.length > 1) {
    const lastIndex = series.length - 1
    if (!xTicks.some((tick) => tick.index === lastIndex)) {
      const x = left + lastIndex * slotWidth + slotWidth / 2
      xTicks.push({ index: lastIndex, label: series[lastIndex].label, x })
    }
  }

  return {
    yTicks,
    xTicks,
    bars
  }
}

const formatPercent = (value: number) => `${value.toFixed(1)}%`

const resetDates = () => {
  fromDate.value = formatDateDMY(firstDayOfMonth)
  toDate.value = formatDateDMY(today)
}
</script>
