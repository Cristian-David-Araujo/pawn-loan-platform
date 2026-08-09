<template>
  <!--
    The full Mutuum logo: mark and wordmark as one vector.

    The wordmark is drawn, not typeset. MUTUUM is M-U-T-U-U-M — three identical bowls and
    two identical angles around a single upright — so the word has a rhythm of its own, and
    constructing it geometrically keeps the logo independent of whether Manrope happens to
    have loaded. Cap height 24, stroke 4, round caps.

    The mark is redrawn here at the wordmark's cap height and stroke rather than scaled down
    from BrandMark: at 24px tall with a stroke of 2 it read thin beside letters at 4, and the
    pair stopped looking like one object.

    This is the primary logo: the sidebar and the sign-in footer both use it. Reach for
    BrandMark alone only where there is no room for the word — the favicon, the square badge
    on the auth cards.

    It used to say the opposite: that the sidebar showed the *installation's* name, which an
    operator could change, so the product wordmark did not belong beside it. That stopped
    being true when the app name became fixed. What an installation calls itself is
    `companyName`, which sits under the logo as a subtitle — a caption to the product's mark,
    not a competing name.
  -->
  <svg
    :width="width"
    :height="height"
    viewBox="0 0 193 24"
    fill="none"
    stroke="currentColor"
    stroke-width="4"
    stroke-linecap="round"
    stroke-linejoin="round"
    role="img"
    aria-label="Mutuum"
  >
    <title>Mutuum</title>

    <!-- Mark: brackets holding a solid form. -->
    <path d="M7 2H2v20h5M21 2h5v20h-5" />
    <circle cx="14" cy="12" r="3" fill="currentColor" stroke="none" />

    <!-- Wordmark. Each letter is placed on the same 24-unit cap height. -->
    <g transform="translate(44,0)">
      <path d="M2 22V2l9 11 9-11v20" />
    </g>
    <g transform="translate(73,0)">
      <path d="M2 2v13a7 7 0 0 0 14 0V2" />
    </g>
    <g transform="translate(98,0)">
      <path d="M2 2h12M8 2v20" />
    </g>
    <g transform="translate(121,0)">
      <path d="M2 2v13a7 7 0 0 0 14 0V2" />
    </g>
    <g transform="translate(146,0)">
      <path d="M2 2v13a7 7 0 0 0 14 0V2" />
    </g>
    <g transform="translate(171,0)">
      <path d="M2 22V2l9 11 9-11v20" />
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/** Driven by height: the logo has one aspect ratio and should never be set to another. */
const props = withDefaults(defineProps<{ height?: number }>(), { height: 20 })

const RATIO = 193 / 24

const height = computed(() => props.height)
const width = computed(() => Math.round(props.height * RATIO))
</script>
