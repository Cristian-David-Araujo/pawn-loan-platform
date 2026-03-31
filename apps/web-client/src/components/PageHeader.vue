<template>
  <header class="page-header">
    <div class="page-header-main">
      <span class="page-header-icon">
        <slot name="icon" />
      </span>
      <div>
        <h2 class="page-title">{{ title }}</h2>
        <p class="page-subtitle">{{ subtitle }}</p>
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
