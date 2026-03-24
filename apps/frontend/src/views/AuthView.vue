<script setup>
import { ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'

const store = useLoanStore()
const username = ref('admin')
const error = ref('')

function doLogin() {
  error.value = ''
  try {
    store.login(username.value)
  } catch (err) {
    error.value = err.message
  }
}

function doLogout() {
  store.logout()
}
</script>

<template>
  <section class="content-grid">
    <article class="card">
      <h3>Authentication (Demo)</h3>
      <p class="muted">Switch user to test role-based permissions across actions.</p>
      <div class="form-grid">
        <select v-model="username">
          <option v-for="user in store.users" :key="user.id" :value="user.username">
            {{ user.username }} - {{ user.role }}
          </option>
        </select>
      </div>
      <div class="button-row">
        <button class="btn btn-primary" @click="doLogin">Login</button>
        <button class="btn" @click="doLogout">Logout</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </article>

    <article class="card">
      <h3>Current Session</h3>
      <ul class="plain-list">
        <li>Username: <strong>{{ store.currentUser?.username || 'None' }}</strong></li>
        <li>Role: <strong>{{ store.currentUser?.role || 'None' }}</strong></li>
        <li>Status: <strong>{{ store.currentUser?.status || 'Logged out' }}</strong></li>
      </ul>
    </article>
  </section>
</template>
