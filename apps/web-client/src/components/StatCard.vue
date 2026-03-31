<template>
  <article class="card stat-card" :class="toneClass">
    <div class="stat-head">
      <p class="stat-label">{{ label }}</p>
      <span v-if="icon" class="stat-icon">
        <component :is="icon" :size="16" />
      </span>
    </div>
    <p class="stat-value">{{ value }}</p>
  </article>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    icon?: Component
    tone?: 'blue' | 'green' | 'amber' | 'indigo'
  }>(),
  {
    tone: 'blue'
  }
)

const toneClass = computed(() => `stat-accent-${props.tone}`)
</script>
