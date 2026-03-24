<script setup>
import { computed, ref } from 'vue'
import { useLoanStore } from '../stores/loanStore'
import DashboardView from '../views/DashboardView.vue'
import AuthView from '../views/AuthView.vue'
import UsersRolesView from '../views/UsersRolesView.vue'
import CustomersView from '../views/CustomersView.vue'
import ApplicationsView from '../views/ApplicationsView.vue'
import LoansView from '../views/LoansView.vue'
import CollateralView from '../views/CollateralView.vue'
import PaymentsView from '../views/PaymentsView.vue'
import DelinquencyView from '../views/DelinquencyView.vue'
import ReportsView from '../views/ReportsView.vue'
import AuditView from '../views/AuditView.vue'
import NotificationsView from '../views/NotificationsView.vue'

const store = useLoanStore()

const navItems = [
  { label: 'Auth', key: 'auth' },
  { label: 'Dashboard', key: 'dashboard' },
  { label: 'Users & Roles', key: 'users-roles' },
  { label: 'Customers', key: 'customers' },
  { label: 'Applications', key: 'applications' },
  { label: 'Loans', key: 'loans' },
  { label: 'Collateral', key: 'collateral' },
  { label: 'Payments', key: 'payments' },
  { label: 'Delinquency', key: 'delinquency' },
  { label: 'Notifications', key: 'notifications' },
  { label: 'Reports', key: 'reports' },
  { label: 'Audit', key: 'audit' },
]

const active = ref('dashboard')

const viewMap = {
  auth: AuthView,
  dashboard: DashboardView,
  'users-roles': UsersRolesView,
  customers: CustomersView,
  applications: ApplicationsView,
  loans: LoansView,
  collateral: CollateralView,
  payments: PaymentsView,
  delinquency: DelinquencyView,
  notifications: NotificationsView,
  reports: ReportsView,
  audit: AuditView,
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
        <div class="chip">
          User: {{ store.currentUser?.username || 'guest' }} | Role: {{ store.currentUser?.role || 'none' }} | Mode: demo
        </div>
      </header>
      <component :is="currentView" />
    </main>
  </div>
</template>
