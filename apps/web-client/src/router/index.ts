import { createRouter, createWebHistory } from 'vue-router'
import { useAuthState, UserRole } from '../modules/authentication/authState'
import AppLayout from '../layouts/AppLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import CustomersView from '../views/CustomersView.vue'
import LoansView from '../views/LoansView.vue'
import LoginView from '../views/LoginView.vue'
import PaymentsView from '../views/PaymentsView.vue'
import ReportingView from '../views/ReportingView.vue'
import SettingsView from '../views/SettingsView.vue'
import InvoicePrintView from '../views/InvoicePrintView.vue'
import UsersView from '../views/UsersView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true }
    },
    {
      path: '/print/invoice/:type/:id',
      name: 'print-invoice',
      component: InvoicePrintView,
      meta: { requiresAuth: true }
    },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
    {
      path: '/inventory',
      name: 'inventory',
      component: () => import('../views/InventoryView.vue'),
      meta: { requiresAuth: true, labelKey: 'app.inventory' }
    },

        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', name: 'dashboard', component: DashboardView, meta: { labelKey: 'app.dashboard' } },
        { path: 'customers', name: 'customers', component: CustomersView, meta: { labelKey: 'app.customers' } },
        { path: 'loans', name: 'loans', component: LoansView, meta: { labelKey: 'app.loans' } },
        { path: 'collateral', redirect: '/loans' },
        { path: 'payments', name: 'payments', component: PaymentsView, meta: { labelKey: 'app.payments' } },
        { path: 'reporting', name: 'reporting', component: ReportingView, meta: { labelKey: 'app.reporting', roles: [UserRole.Administrator, UserRole.LoanOfficer] } },
        { path: 'settings', name: 'settings', component: SettingsView, meta: { labelKey: 'app.settings', roles: [UserRole.Administrator] } },
        { path: 'users', name: 'users', component: UsersView, meta: { labelKey: 'app.users', roles: [UserRole.Administrator] } }
      ]
    }
  ]
})

router.beforeEach(async (to) => {
  const { isAuthenticated, state, fetchCurrentUser, hasRole } = useAuthState()

  if (to.matched.some((record) => record.meta.requiresAuth) && !isAuthenticated.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (isAuthenticated.value && !state.currentUser) {
    await fetchCurrentUser()
  }

  if (to.meta.guestOnly && isAuthenticated.value) {
    return { path: '/dashboard' }
  }

  if (to.meta.roles && Array.isArray(to.meta.roles)) {
    if (!hasRole(to.meta.roles)) {
      return { path: '/dashboard' }
    }
  }

  return true
})

export default router
