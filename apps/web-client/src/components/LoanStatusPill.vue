<template>
  <span class="pill-group">
    <span class="pill" :class="loanStatusPillClass(status)">{{ t(loanStatusKey(status)) }}</span>
    <!-- The reason rides along as the tooltip: it is the one thing an operator wants next
         after seeing the chip, and fetching it costs nothing because the list already has it. -->
    <span v-if="paused" class="pill pill-paused" :title="pauseReason || undefined">
      <Pause :size="11" aria-hidden="true" />
      {{ t('loans.interestPausedShort') }}
    </span>
  </span>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Pause } from 'lucide-vue-next'
import { loanStatusKey, loanStatusPillClass } from '../utils/loanStatus'

/**
 * A loan's state in a table cell: the status, plus the pause when there is one.
 *
 * **A pause is a second chip, never a replacement for the first.** It is a flag orthogonal to
 * the status — a loan can be paused *and* overdue, and that combination is exactly the one an
 * operator needs to see, since the arrears are real but they have stopped growing. Rendering
 * "Pausado" in place of the status would hide the half that says whether money is at risk.
 *
 * It was visible nowhere but inside the loan detail, and there only as the *label of a
 * button* — so the only way to find out whether a loan was still accruing was to open it and
 * read whether the control offered to pause or to resume.
 *
 * The chip carries no status hue on purpose. The three that exist are spent on money at risk
 * (green in order, amber late, red foreclosed), and a fourth beside them would dilute all
 * three. A dashed neutral border reads as "suspended" without claiming this is a problem —
 * pausing is a deliberate decision, not a warning.
 */
defineProps<{
  status: string
  paused?: boolean
  pauseReason?: string
}>()

const { t } = useI18n()
</script>
