<template>
  <header class="page-header">
    <div class="page-header-main">
      <!-- Conditional: an empty tile beside a heading is decoration pretending to be an icon. -->
      <span v-if="$slots.icon" class="page-header-icon" aria-hidden="true">
        <slot name="icon" />
      </span>
      <div>
        <h2 class="page-title">{{ title }}</h2>
        <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle: string
}>()
</script>
