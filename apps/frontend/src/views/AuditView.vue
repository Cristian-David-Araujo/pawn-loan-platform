<script setup>
import { computed, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'

const store = useLoanStore()
const filter = ref('')

const filteredLogs = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!q) return store.auditLogs
  return store.auditLogs.filter((log) =>
    [log.action, log.entityType, log.entityId, log.userId]
      .join(' ')
      .toLowerCase()
      .includes(q),
  )
})
</script>

<template>
  <section class="card">
    <h3>Audit Log</h3>
    <div class="form-grid">
      <input v-model="filter" placeholder="Filter by action, entity, id or user" />
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>User</th>
            <th>Action</th>
            <th>Entity</th>
            <th>ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in filteredLogs.slice(0, 100)" :key="log.id">
            <td>{{ log.createdAt }}</td>
            <td>{{ log.userId }}</td>
            <td>{{ log.action }}</td>
            <td>{{ log.entityType }}</td>
            <td>{{ log.entityId }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
