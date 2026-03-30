import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import CustomersView from '../views/CustomersView.vue'
import LoansView from '../views/LoansView.vue'
import CollateralView from '../views/CollateralView.vue'
import PaymentsView from '../views/PaymentsView.vue'
import ReportingView from '../views/ReportingView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', name: 'dashboard', component: DashboardView, meta: { labelKey: 'app.dashboard' } },
        { path: 'customers', name: 'customers', component: CustomersView, meta: { labelKey: 'app.customers' } },
        { path: 'loans', name: 'loans', component: LoansView, meta: { labelKey: 'app.loans' } },
        { path: 'collateral', name: 'collateral', component: CollateralView, meta: { labelKey: 'app.collateral' } },
        { path: 'payments', name: 'payments', component: PaymentsView, meta: { labelKey: 'app.payments' } },
        { path: 'reporting', name: 'reporting', component: ReportingView, meta: { labelKey: 'app.reporting' } }
      ]
    }
  ]
})

export default router
