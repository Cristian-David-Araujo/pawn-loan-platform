<template>
  <div id="app">
    <nav v-if="authStore.isAuthenticated" class="navbar">
      <div class="navbar-brand">
        <span class="logo">💰 Pawn Loan Platform</span>
      </div>
      <div class="navbar-menu">
        <router-link to="/dashboard">Dashboard</router-link>
        <router-link to="/customers">Customers</router-link>
        <router-link to="/loans">Loans</router-link>
        <router-link to="/payments">Payments</router-link>
        <router-link to="/collateral">Collateral</router-link>
        <router-link to="/reports">Reports</router-link>
      </div>
      <div class="navbar-end">
        <span class="user-name">{{ authStore.user?.username }}</span>
        <button class="btn btn-sm btn-outline" @click="logout">Logout</button>
      </div>
    </nav>
    <main :class="{ 'with-nav': authStore.isAuthenticated }">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; }
#app { min-height: 100vh; }
.navbar {
  background: #1a365d;
  color: white;
  padding: 0 24px;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 24px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}
.navbar-brand .logo { font-size: 1.2rem; font-weight: 700; }
.navbar-menu { display: flex; gap: 8px; flex: 1; }
.navbar-menu a { color: #bee3f8; text-decoration: none; padding: 4px 12px; border-radius: 4px; font-size: 0.9rem; }
.navbar-menu a:hover, .navbar-menu a.router-link-active { background: rgba(255,255,255,0.15); color: white; }
.navbar-end { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 0.9rem; color: #bee3f8; }
main.with-nav { padding: 24px; }
.btn { cursor: pointer; padding: 6px 12px; border-radius: 4px; font-size: 0.875rem; border: none; }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }
.btn-primary { background: #2b6cb0; color: white; }
.btn-primary:hover { background: #2c5282; }
.btn-outline { background: transparent; color: white; border: 1px solid rgba(255,255,255,0.5); }
.btn-outline:hover { background: rgba(255,255,255,0.1); }
.btn-danger { background: #e53e3e; color: white; }
.btn-success { background: #38a169; color: white; }
.card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 24px; margin-bottom: 24px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 4px; color: #4a5568; }
.form-group input, .form-group select, .form-group textarea {
  width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 0.875rem;
}
.form-group input:focus, .form-group select:focus { outline: none; border-color: #4299e1; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 0.875rem; }
.table th { background: #f7fafc; font-weight: 600; color: #4a5568; }
.table tr:hover { background: #f7fafc; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 500; }
.badge-active { background: #c6f6d5; color: #276749; }
.badge-inactive { background: #fed7d7; color: #9b2c2c; }
.badge-pending { background: #feebc8; color: #7b341e; }
.badge-overdue { background: #fed7d7; color: #9b2c2c; }
.badge-closed { background: #e2e8f0; color: #4a5568; }
.alert { padding: 12px 16px; border-radius: 4px; margin-bottom: 16px; }
.alert-error { background: #fff5f5; border: 1px solid #fc8181; color: #c53030; }
.alert-success { background: #f0fff4; border: 1px solid #68d391; color: #276749; }
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 24px; color: #1a365d; }
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.gap-2 { gap: 8px; }
.mt-2 { margin-top: 8px; }
.mb-4 { margin-bottom: 16px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.stat-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }
.stat-card .stat-value { font-size: 2rem; font-weight: 700; color: #2b6cb0; }
.stat-card .stat-label { font-size: 0.875rem; color: #718096; margin-top: 4px; }
</style>
