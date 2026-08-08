<template>
  <!--
    The Mutuum mark, on its own.

    Two brackets holding a solid form. It says the one thing that separates this business
    from a generic lender: something of the customer's is *held* while the debt lives, and
    handed back when it is paid. Not a letterform — the wordmark carries the name, so the
    mark is free to carry the meaning.

    Drawn on lucide's grid (24×24, stroke 2, round caps and joins) so it sits beside the
    navigation icons without reading as a different set, and painted in `currentColor` so
    the sidebar and the login card each get it in their own ink. Legible down to 16px.

    The full logo — this plus the wordmark — is BrandLockup.vue.
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
    <path d="M8.5 3.5H5v17h3.5M15.5 3.5H19v17h-3.5" />
    <circle cx="12" cy="12" r="3.2" fill="currentColor" stroke="none" />
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
