<template>
  <div ref="rootRef" class="date-field">
    <div class="date-input-control">
      <input
        :value="modelValue"
        class="date-text-input"
        :placeholder="placeholder"
        :required="required"
        :title="title"
        @input="onTextInput"
        @click="openCalendar"
      />
      <button
        class="date-picker-trigger"
        type="button"
        :title="title"
        :aria-label="`${label} (calendar)`"
        @click="toggleCalendar"
      >
        <CalendarDays :size="16" />
      </button>
    </div>

    <div v-if="isOpen" class="date-popover" role="dialog" :aria-label="`${label} calendar`">
      <div class="date-popover-head">
        <button class="date-nav-btn" type="button" @click="goPrevMonth" aria-label="Previous month">&lt;</button>
        <strong>{{ monthLabel }}</strong>
        <button class="date-nav-btn" type="button" @click="goNextMonth" aria-label="Next month">&gt;</button>
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
            'is-today': day.iso === todayIso
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
import { CalendarDays } from 'lucide-vue-next'
import { formatDateDMY, toIsoDate } from '../utils/date'

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
  }>(),
  {
    placeholder: '',
    title: '',
    required: false
  }
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
}>()

const { locale } = useI18n()
const rootRef = ref<HTMLElement | null>(null)
const isOpen = ref(false)

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
  new Intl.DateTimeFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
    month: 'long',
    year: 'numeric'
  }).format(monthCursor.value)
)

const weekdays = computed(() => {
  const formatter = new Intl.DateTimeFormat(locale.value === 'es' ? 'es-MX' : 'en-US', {
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

onMounted(() => {
  document.addEventListener('mousedown', handleDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleDocumentClick)
})
</script>