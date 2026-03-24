<script setup>
import { computed, ref } from 'vue'
import DashboardView from '../views/DashboardView.vue'
import CustomersView from '../views/CustomersView.vue'
import ApplicationsView from '../views/ApplicationsView.vue'
import LoansView from '../views/LoansView.vue'
import CollateralView from '../views/CollateralView.vue'
import PaymentsView from '../views/PaymentsView.vue'
import ReportsView from '../views/ReportsView.vue'

const navItems = [
  { label: 'Dashboard', key: 'dashboard' },
  { label: 'Customers', key: 'customers' },
  { label: 'Applications', key: 'applications' },
  { label: 'Loans', key: 'loans' },
  { label: 'Collateral', key: 'collateral' },
  { label: 'Payments', key: 'payments' },
  { label: 'Reports', key: 'reports' },
]

const active = ref('dashboard')

const viewMap = {
  dashboard: DashboardView,
  customers: CustomersView,
  applications: ApplicationsView,
  loans: LoansView,
  collateral: CollateralView,
  payments: PaymentsView,
  reports: ReportsView,
}

const currentView = computed(() => viewMap[active.value] || DashboardView)
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar card">
      <h1 class="brand">Pawn Loan OS</h1>
      <p class="tag">Operational frontend prototype</p>
      <nav class="menu">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="menu-link menu-button"
          :class="{ active: active === item.key }"
          @click="active = item.key"
        >
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <main class="main-content">
      <header class="topbar card">
        <div>
          <h2 class="page-title">Loan Management Platform</h2>
          <p class="page-subtitle">Business rules simulated on frontend state (fake demo data)</p>
        </div>
        <div class="chip">Role: administrator | Mode: demo</div>
      </header>
      <component :is="currentView" />
    </main>
  </div>
</template>
