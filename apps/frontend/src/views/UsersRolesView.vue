<script setup>
import { computed } from 'vue'
import { useLoanStore } from '../stores/loanStore'

const store = useLoanStore()

const rolesWithUsers = computed(() =>
  store.roles.map((role) => ({
    ...role,
    users: store.users.filter((user) => user.role === role.id),
  })),
)
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Users</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Role</th>
              <th>Name</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in store.users" :key="user.id">
              <td>{{ user.id }}</td>
              <td>{{ user.username }}</td>
              <td>{{ user.role }}</td>
              <td>{{ user.fullName }}</td>
              <td>{{ user.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>

    <article class="card">
      <h3>Roles and Permissions</h3>
      <div v-for="role in rolesWithUsers" :key="role.id" class="role-block">
        <p><strong>{{ role.id }}</strong> ({{ role.users.length }} users)</p>
        <p class="muted">{{ role.permissions.join(', ') }}</p>
      </div>
    </article>
  </section>
</template>
