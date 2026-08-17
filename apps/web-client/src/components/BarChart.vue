<template>
  <figure class="bar-chart">
    <div class="bar-chart-frame">
      <div class="bar-chart-y-axis" aria-hidden="true">
        <span
          v-for="tick in model.yTicks"
          :key="`y-${tick.value}`"
          class="bar-chart-y-label"
          :style="{ bottom: `${tick.pct}%` }"
        >
          {{ formatTick(tick.value) }}
        </span>
      </div>

      <div class="bar-chart-plot">
        <div
          v-for="tick in model.yTicks"
          :key="`grid-${tick.value}`"
          class="bar-chart-grid"
          :style="{ bottom: `${tick.pct}%` }"
        ></div>

        <div class="bar-chart-bars">
          <div v-for="bar in model.bars" :key="`slot-${bar.label}`" class="bar-chart-slot">
            <div
              class="bar-chart-bar"
              :style="{ height: `${bar.pct}%` }"
              :title="tooltip(bar.label, bar.value)"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <div class="bar-chart-x-axis" aria-hidden="true">
      <span v-for="bar in model.bars" :key="`x-${bar.label}`" class="bar-chart-x-label">
        {{ bar.showLabel ? bar.label : '' }}
      </span>
    </div>

    <!-- The same numbers as a table, reachable by a screen reader and by anyone who cannot
         read the bars. A `role="img"` with an aria-label can only announce the title; this
         announces the data. -->
    <figcaption class="bar-chart-table">
      <table>
        <caption>{{ ariaLabel }}</caption>
        <thead>
          <tr>
            <th scope="col">{{ periodLabel }}</th>
            <th scope="col">{{ valueLabel }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="bar in model.bars" :key="`row-${bar.label}`">
            <th scope="row">{{ bar.label }}</th>
            <td>{{ formatValue(bar.value) }}</td>
          </tr>
        </tbody>
      </table>
    </figcaption>
  </figure>
</template>

<script setup lang="ts">
/**
 * A single-series bar chart, drawn in HTML rather than SVG.
 *
 * Five of these were written inline in `ReportingView`, each a 25-line block of `<svg>` with
 * the same geometry retyped — the shape that this codebase has been bitten by repeatedly
 * (`formatCurrency` in nine files, the payment-type map in three views).
 *
 * **Why not SVG.** The old markup put the axis labels *inside* `viewBox="0 0 100 64"`, so
 * their `font-size` was a viewBox unit and had to be written as `2.7px` to render at a
 * readable size — a number that means nothing on the type scale, that the design detector
 * flagged on every run, and that would silently change size the day the viewBox did. In HTML
 * the labels take `--fs-xs` like every other label in the app, and the bars are divs whose
 * heights are percentages, so the whole thing is responsive without a coordinate system.
 *
 * There is no legend: one series, and the card's own heading names it.
 */
import { computed } from 'vue'

export interface BarChartEntry {
  label: string
  value: number
}

const props = withDefaults(
  defineProps<{
    series: BarChartEntry[]
    /** Formats an axis tick — usually a compact number. */
    formatTick: (value: number) => string
    /** Formats a value in full, for the tooltip and the table. */
    formatValue: (value: number) => string
    tooltip: (label: string, value: number) => string
    ariaLabel: string
    periodLabel: string
    valueLabel: string
    /** How many x labels to aim for before thinning them out. */
    maxXLabels?: number
  }>(),
  { maxXLabels: 6 }
)

const Y_STEPS = 4

/** Rounds the axis maximum up to a 1/2/5 × 10ⁿ figure, so ticks land on readable numbers. */
const niceMax = (value: number): number => {
  if (value <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const normalized = value / magnitude
  if (normalized <= 1) return magnitude
  if (normalized <= 2) return 2 * magnitude
  if (normalized <= 5) return 5 * magnitude
  return 10 * magnitude
}

const model = computed(() => {
  const series = props.series
  if (!series.length) {
    return { yTicks: [], bars: [] }
  }

  const yMax = niceMax(series.reduce((max, item) => Math.max(max, item.value), 0))

  const yTicks = Array.from({ length: Y_STEPS + 1 }, (_, index) => {
    const value = (yMax / Y_STEPS) * index
    return { value, pct: (value / yMax) * 100 }
  })

  // Thin the labels rather than the bars: every period keeps its bar, only some are named.
  const step = Math.max(Math.ceil(series.length / props.maxXLabels), 1)

  const bars = series.map((item, index) => ({
    label: item.label,
    value: item.value,
    pct: yMax > 0 ? Math.max((item.value / yMax) * 100, 0) : 0,
    // The last period always keeps its label: it is the one the reader is looking for.
    showLabel: index % step === 0 || index === series.length - 1
  }))

  return { yTicks, bars }
})
</script>
