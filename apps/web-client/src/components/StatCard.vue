<template>
  <!--
    A tile that corresponds to a list becomes a link to that list. A figure naming a problem
    the operator cannot open is a dead end, and re-finding it through the sidebar is the
    context switch this screen exists to save.
  -->
  <component
    :is="to ? RouterLink : 'article'"
    :to="to"
    class="card stat-card"
    :class="[toneClass, { 'stat-card-link': to }]"
  >
    <div class="stat-head">
      <p class="stat-label">{{ label }}</p>
      <span v-if="icon" class="stat-icon" aria-hidden="true">
        <component :is="icon" :size="16" />
      </span>
    </div>
    <p class="stat-value">{{ value }}</p>
    <p v-if="caption" class="stat-caption">{{ caption }}</p>
  </component>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'

const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    /** A second line under the figure: what the figure is worth, or that there is nothing to do. */
    caption?: string
    icon?: Component
    tone?: 'blue' | 'green' | 'amber' | 'indigo' | 'danger'
    /** When present the whole tile is a link. */
    to?: RouteLocationRaw
  }>(),
  {
    tone: 'blue'
  }
)

const toneClass = computed(() => `stat-accent-${props.tone}`)
</script>

<style scoped>
.stat-caption {
  margin: 0;
  font-size: var(--fs-sm);
  color: var(--muted);
}

/* Only a tile that actually navigates reacts to the pointer. */
.stat-card-link {
  text-decoration: none;
  color: inherit;
  transition: border-color var(--transition), background-color var(--transition);
}

.stat-card-link:hover {
  border-color: var(--line-hover);
  background: var(--surface-soft);
}

.stat-card-link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
</style>
