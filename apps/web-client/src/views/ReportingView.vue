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
        <input v-model="fromDate" :placeholder="datePlaceholder" />
      </label>
      <label>
        {{ t('reporting.toDate') }}
        <input v-model="toDate" :placeholder="datePlaceholder" />
      </label>
      <button class="btn btn-secondary" type="button" @click="resetDates">
        <RotateCcw :size="16" />
        {{ t('reporting.resetDates') }}
      </button>
    </div>

    <div class="grid grid-3 mt-16">
      <StatCard :label="t('reporting.totalCollectedLabel')" :value="formatCurrency(totalCollected)" :icon="Wallet" tone="green" />
      <StatCard :label="t('reporting.totalInterestCollectedLabel')" :value="formatCurrency(totalInterestCollected)" :icon="BadgeDollarSign" tone="blue" />
      <StatCard :label="t('reporting.totalPenaltyCollectedLabel')" :value="formatCurrency(totalPenaltyCollected)" :icon="ClockAlert" tone="amber" />
      <StatCard :label="t('reporting.estimatedPendingInterest')" :value="formatCurrency(estimatedPendingInterest)" :icon="HandCoins" tone="indigo" />
      <StatCard :label="t('reporting.estimatedPendingPenalty')" :value="formatCurrency(estimatedPendingPenalty)" :icon="ClockAlert" tone="amber" />
      <StatCard :label="t('reporting.collectionCoverage')" :value="formatPercent(collectionCoverage)" :icon="CircleDollarSign" tone="blue" />
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
        <p>{{ t('reporting.totalInterestCollected', { amount: formatCurrency(totalInterestCollected) }) }}</p>
        <p>{{ t('reporting.totalPenaltyCollected', { amount: formatCurrency(totalPenaltyCollected) }) }}</p>
        <p>{{ t('reporting.estimatedPendingInterestWithAmount', { amount: formatCurrency(estimatedPendingInterest) }) }}</p>
        <p>{{ t('reporting.estimatedPendingPenaltyWithAmount', { amount: formatCurrency(estimatedPendingPenalty) }) }}</p>
      </article>
    </div>

    <div class="grid grid-2 mt-16">
      <article class="card">
        <h3>{{ t('reporting.actionableInsights') }}</h3>
        <ul>
          <li v-for="insight in actionableInsights" :key="insight">{{ insight }}</li>
        </ul>
      </article>

      <article class="card">
        <h3>{{ t('reporting.topCollectors') }}</h3>
        <ul>
          <li v-for="item in topCustomersByCollection" :key="item.customerId">
            {{ t('reporting.topCollectorLine', { customer: item.customerName, amount: formatCurrency(item.totalCollected) }) }}
          </li>
          <li v-if="!topCustomersByCollection.length">{{ t('reporting.noDataRange') }}</li>
        </ul>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  BadgeDollarSign,
  ChartNoAxesCombined,
  CircleDollarSign,
  ClockAlert,
  HandCoins,
  RotateCcw,
  Wallet
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'
import { formatDateDMY, getGlobalDateFormat, toIsoDate } from '../utils/date'

const { state, getCustomerName, ensureInitialized } = useMockPlatformStore()
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

const currencyCode = computed(() => state.globalSettings?.currencyCode ?? 'COP')
const today = new Date().toISOString().slice(0, 10)
const fromDate = ref('')
const toDate = ref(formatDateDMY(today))
const datePlaceholder = computed(() => getGlobalDateFormat())

const fromDateIso = computed(() => toIsoDate(fromDate.value))
const toDateIso = computed(() => toIsoDate(toDate.value) ?? today)

onMounted(async () => {
  await ensureInitialized()
})

const activeLoans = computed(() =>
  [...state.loans.filter((loan) => loan.status === 'active')].sort(
    (a, b) => new Date(b.disbursementDate).getTime() - new Date(a.disbursementDate).getTime()
  )
)
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

const rangeEndIso = computed(() => (toDateIso.value > today ? today : toDateIso.value))

const getLaterIso = (a: string, b: string) => (a >= b ? a : b)
const getEarlierIso = (a: string, b: string) => (a <= b ? a : b)

const countMonthsInRange = (startIso: string, endIso: string) => {
  const start = new Date(`${startIso}T00:00:00`)
  const end = new Date(`${endIso}T00:00:00`)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) {
    return 0
  }

  return (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth()) + 1
}

const expectedChargesInRange = computed(() => {
  let expectedInterest = 0
  let expectedPenalty = 0

  const fromIso = fromDateIso.value
  const toIso = rangeEndIso.value

  for (const loan of state.loans) {
    if (loan.status === 'closed' || loan.outstandingPrincipal <= 0) {
      continue
    }

    const loanStart = fromIso ? getLaterIso(loan.disbursementDate, fromIso) : loan.disbursementDate
    const loanEnd = getEarlierIso(toIso, today)

    if (loanEnd < loanStart) {
      continue
    }

    const periods = countMonthsInRange(loanStart, loanEnd)
    if (!periods) {
      continue
    }

    expectedInterest += periods * loan.outstandingPrincipal * (loan.monthlyInterestRate / 100)

    if (loan.status === 'overdue') {
      expectedPenalty += periods * loan.outstandingPrincipal * (loan.latePenaltyRate / 100)
    }
  }

  return { expectedInterest, expectedPenalty }
})

const estimatedPendingInterest = computed(() =>
  Math.max(expectedChargesInRange.value.expectedInterest - totalInterestCollected.value, 0)
)
const estimatedPendingPenalty = computed(() =>
  Math.max(expectedChargesInRange.value.expectedPenalty - totalPenaltyCollected.value, 0)
)

const collectionCoverage = computed(() => {
  const pendingTotal = estimatedPendingInterest.value + estimatedPendingPenalty.value
  const denominator = totalCollected.value + pendingTotal
  if (!denominator) {
    return 0
  }

  return (totalCollected.value / denominator) * 100
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
  const overdueShare = state.loans.length ? (overdueLoans.value.length / state.loans.length) * 100 : 0
  const avgTicket = filteredPayments.value.length ? totalCollected.value / filteredPayments.value.length : 0
  const portfolioOutstanding = state.loans.reduce((sum, loan) => sum + loan.outstandingPrincipal, 0)
  const collateralCoverage = portfolioOutstanding
    ? (custodyItems.value.reduce((sum, item) => sum + item.appraisedValue, 0) / portfolioOutstanding) * 100
    : 0

  return [
    t('reporting.insightCollectionCoverage', { value: formatPercent(collectionCoverage.value) }),
    t('reporting.insightAverageTicket', { amount: formatCurrency(avgTicket) }),
    t('reporting.insightOverdueShare', { value: formatPercent(overdueShare) }),
    t('reporting.insightCollateralCoverage', { value: formatPercent(collateralCoverage) })
  ]
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

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    style: 'currency',
    currency: currencyCode.value
  }).format(
    amount
  )

const formatPercent = (value: number) => `${value.toFixed(1)}%`
const formatCompactNumber = (value: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    notation: 'compact',
    maximumFractionDigits: 1
  }).format(value)
const formatInteger = (value: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    maximumFractionDigits: 0
  }).format(value)

const getCustomerLabel = (customerId: number) => {
  const value = getCustomerName(customerId)
  return value === '__UNKNOWN_CUSTOMER__' ? t('messages.unknownCustomer') : value
}

const resetDates = () => {
  fromDate.value = ''
  toDate.value = formatDateDMY(today)
}
</script>
