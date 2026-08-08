<template>
  <!--
    The Mutuum mark.

    A *mutuum* is the Roman-law contract this product runs on: a loan of fungible goods where
    ownership passes and an **equivalent** must come back. The mark says exactly that — an M
    whose two outer stems are drawn to the same height, resting on a ledger rule.

    Built on lucide's grid (24×24, stroke 2, round caps and joins) so it sits in the sidebar
    beside the navigation icons without looking like a different set. It paints in
    `currentColor`, so the sidebar, the login card and a print header each get it in their
    own ink without a second copy existing anywhere.
  -->
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    role="img"
    :aria-label="title"
  >
    <title>{{ title }}</title>
    <!-- The M: equal stems, centre dipping to the rule. -->
    <path d="M5 17.5V6.5L12 13l7-6.5v11" />
    <!-- The ledger rule the figures are written on. -->
    <path d="M4 21h16" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number | string
    title?: string
  }>(),
  {
    size: 20,
    title: 'Mutuum'
  }
)
</script>
