import { createRouter, createWebHistory } from 'vue-router'
import { useAuthState } from '../modules/authentication/authState'
import AppLayout from '../layouts/AppLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import CustomersView from '../views/CustomersView.vue'
import LoansView from '../views/LoansView.vue'
import LoginView from '../views/LoginView.vue'
import PaymentsView from '../views/PaymentsView.vue'
import ReportingView from '../views/ReportingView.vue'
import SettingsView from '../views/SettingsView.vue'

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
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', name: 'dashboard', component: DashboardView, meta: { labelKey: 'app.dashboard' } },
        { path: 'customers', name: 'customers', component: CustomersView, meta: { labelKey: 'app.customers' } },
        { path: 'loans', name: 'loans', component: LoansView, meta: { labelKey: 'app.loans' } },
        { path: 'collateral', redirect: '/loans' },
        { path: 'payments', name: 'payments', component: PaymentsView, meta: { labelKey: 'app.payments' } },
        { path: 'reporting', name: 'reporting', component: ReportingView, meta: { labelKey: 'app.reporting' } },
        { path: 'settings', name: 'settings', component: SettingsView, meta: { labelKey: 'app.settings' } }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const { isAuthenticated } = useAuthState()

  if (to.matched.some((record) => record.meta.requiresAuth) && !isAuthenticated.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guestOnly && isAuthenticated.value) {
    return { path: '/dashboard' }
  }

  return true
})

export default router
