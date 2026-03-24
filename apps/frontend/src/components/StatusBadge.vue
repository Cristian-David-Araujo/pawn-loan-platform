<script setup>
const props = defineProps({
  status: {
    type: String,
    required: true,
  },
})

function normalizedStatus(value) {
  return String(value || '').toLowerCase().replace(/\s+/g, '-')
}
</script>

<template>
  <span class="status-badge" :class="normalizedStatus(props.status)">
    {{ props.status }}
  </span>
</template>
