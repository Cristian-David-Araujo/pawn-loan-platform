<template>
  <div ref="rootRef" class="date-field">
    <div class="date-input-control">
      <input
        :value="modelValue"
        class="date-text-input"
        :placeholder="resolvedPlaceholder"
        :required="required"
        :title="title"
        @input="onTextInput"
        @click="openCalendar"
      />
      <button
        class="date-picker-trigger"
        type="button"
        :title="title"
        :aria-label="t('common.openCalendar', { field: label })"
        @click="toggleCalendar"
      >
        <CalendarDays :size="16" aria-hidden="true" />
      </button>
    </div>

    <div
      v-if="isOpen"
      class="date-popover"
      role="dialog"
      :aria-label="t('common.calendarFor', { field: label })"
    >
      <div class="date-popover-head">
        <!-- Drawn icons rather than the `<` and `>` glyphs these used to be: the rest of the
             app is one icon set at one stroke weight, and two stray characters broke it. -->
        <button
          class="date-nav-btn"
          type="button"
          :aria-label="t('common.previousMonth')"
          @click="goPrevMonth"
        >
          <ChevronLeft :size="15" aria-hidden="true" />
        </button>
        <strong>{{ monthLabel }}</strong>
        <button
          class="date-nav-btn"
          type="button"
          :aria-label="t('common.nextMonth')"
          @click="goNextMonth"
        >
          <ChevronRight :size="15" aria-hidden="true" />
        </button>
      </div>

      <div class="date-weekdays">
        <span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
      </div>

      <div class="date-days-grid">
        <button
          v-for="day in monthDays"
          :key="day.key"
          type="button"
          class="date-day-btn"
          :class="{
            'is-muted': !day.inCurrentMonth,
            'is-selected': day.iso === selectedIso,
            'is-today': day.iso === todayIso,
            'is-range-edge': isRangeEdge(day.iso),
            'is-in-range': isInsideRange(day.iso)
          }"
          @click="selectDay(day.iso)"
        >
          {{ day.dayNumber }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { formatDateDMY, getGlobalDateFormat, toIsoDate } from '../utils/date'

interface DayCell {
  key: string
  iso: string
  dayNumber: number
  inCurrentMonth: boolean
}

const props = withDefaults(
  defineProps<{
    modelValue: string
    label: string
    placeholder?: string
    title?: string
    required?: boolean
    /* The span this field belongs to, when it is one half of a from/to pair.
     *
     * Both fields receive the *same* two values, so opening either calendar shows the whole
     * range shaded rather than a single lit day — an operator picking "hasta" can see where
     * "desde" landed without closing the popover.
     *
     * They stay optional, so a lone date field (a disbursement, a payment date) is unchanged
     * and there is still exactly one date component in the app rather than a second one that
     * would drift from this one. */
    rangeStart?: string
    rangeEnd?: string
  }>(),
  {
    placeholder: '',
    title: '',
    required: false,
    rangeStart: '',
    rangeEnd: ''
  }
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
}>()

/* What the field shows when it is empty: the shape it expects, e.g. `DD/MM/YYYY`, taken from
   `GlobalSettings.dateFormat`.

   Defaulted here rather than passed in. Two of the four callers passed a computed wrapping
   `getGlobalDateFormat()` and the other two passed `t('settings.dateFormat')` — which is the
   *label* key, so the customer and payment filters prompted with the words "Formato de fecha"
   while the loan and report filters prompted with `DD/MM/YYYY`. Every date field in the app
   is this component, so the answer belongs to it and there is nothing left to keep in sync. */
const resolvedPlaceholder = computed(() => props.placeholder || getGlobalDateFormat())

/* The span, normalised to ISO and ordered, so a range typed backwards ("desde" later than
   "hasta") still shades rather than silently showing nothing. Both ends must be present:
   half a range is not a range, and shading from one date to nowhere would suggest the filter
   is doing something it is not. */
const rangeBounds = computed(() => {
  const start = toIsoDate(props.rangeStart)
  const end = toIsoDate(props.rangeEnd)
  if (!start || !end) return null
  return start <= end ? { start, end } : { start: end, end: start }
})

// ISO dates are lexicographically ordered, so string comparison is date comparison.
const isRangeEdge = (iso: string) => {
  const bounds = rangeBounds.value
  return !!bounds && (iso === bounds.start || iso === bounds.end)
}

const isInsideRange = (iso: string) => {
  const bounds = rangeBounds.value
  return !!bounds && iso > bounds.start && iso < bounds.end
}

const { t, locale } = useI18n()
const rootRef = ref<HTMLElement | null>(null)
const isOpen = ref(false)

/* Month and weekday names follow the interface language — unlike an amount, which follows
   its currency. `es-CO` rather than `es-MX` only to keep one Spanish locale in the app. */
const dateLocale = computed(() => (locale.value === 'es' ? 'es-CO' : 'en-US'))

const todayIso = new Date().toISOString().slice(0, 10)
const selectedIso = computed(() => toIsoDate(props.modelValue))
const displayedMonthIso = ref(selectedIso.value ?? todayIso)

watch(selectedIso, (value) => {
  if (value) {
    displayedMonthIso.value = value
  }
})

const monthCursor = computed(() => {
  const baseIso = displayedMonthIso.value || todayIso
  return new Date(`${baseIso.slice(0, 7)}-01T00:00:00`)
})

const monthLabel = computed(() =>
  new Intl.DateTimeFormat(dateLocale.value, {
    month: 'long',
    year: 'numeric'
  }).format(monthCursor.value)
)

const weekdays = computed(() => {
  const formatter = new Intl.DateTimeFormat(dateLocale.value, {
    weekday: 'short'
  })

  const start = new Date('2023-01-01T00:00:00')
  return Array.from({ length: 7 }, (_, index) => {
    const day = new Date(start)
    day.setDate(start.getDate() + index)
    return formatter.format(day).slice(0, 2).toUpperCase()
  })
})

const monthDays = computed<DayCell[]>(() => {
  const cursor = monthCursor.value
  const year = cursor.getFullYear()
  const month = cursor.getMonth()
  const firstDay = new Date(year, month, 1)
  const startWeekday = firstDay.getDay()
  const gridStart = new Date(year, month, 1 - startWeekday)

  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(gridStart)
    day.setDate(gridStart.getDate() + index)

    const iso = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`
    return {
      key: `${iso}-${index}`,
      iso,
      dayNumber: day.getDate(),
      inCurrentMonth: day.getMonth() === month
    }
  })
})

const onTextInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  emit('update:modelValue', value)
}

const selectDay = (iso: string) => {
  emit('update:modelValue', formatDateDMY(iso))
  displayedMonthIso.value = iso
  isOpen.value = false
}

const goPrevMonth = () => {
  const cursor = monthCursor.value
  const prev = new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1)
  displayedMonthIso.value = `${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, '0')}-01`
}

const goNextMonth = () => {
  const cursor = monthCursor.value
  const next = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1)
  displayedMonthIso.value = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-01`
}

const openCalendar = () => {
  if (selectedIso.value) {
    displayedMonthIso.value = selectedIso.value
  }
  isOpen.value = true
}

const toggleCalendar = () => {
  if (isOpen.value) {
    isOpen.value = false
    return
  }

  openCalendar()
}

const handleDocumentClick = (event: MouseEvent) => {
  if (!rootRef.value) {
    return
  }

  const target = event.target as Node | null
  if (target && !rootRef.value.contains(target)) {
    isOpen.value = false
  }
}

// The popover covers the field below it, so it has to be dismissible from the keyboard.
const handleKeydown = (event: KeyboardEvent) => {
  if (isOpen.value && event.key === 'Escape') {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleDocumentClick)
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleDocumentClick)
  document.removeEventListener('keydown', handleKeydown)
})
</script>