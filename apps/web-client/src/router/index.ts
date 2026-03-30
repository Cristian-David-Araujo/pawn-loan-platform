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
        { path: 'dashboard', name: 'dashboard', component: DashboardView },
        { path: 'customers', name: 'customers', component: CustomersView },
        { path: 'loans', name: 'loans', component: LoansView },
        { path: 'collateral', name: 'collateral', component: CollateralView },
        { path: 'payments', name: 'payments', component: PaymentsView },
        { path: 'reporting', name: 'reporting', component: ReportingView }
      ]
    }
  ]
})

export default router
