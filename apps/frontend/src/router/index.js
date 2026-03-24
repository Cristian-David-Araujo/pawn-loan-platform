import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import CustomersView from '../views/CustomersView.vue'
import ApplicationsView from '../views/ApplicationsView.vue'
import LoansView from '../views/LoansView.vue'
import CollateralView from '../views/CollateralView.vue'
import PaymentsView from '../views/PaymentsView.vue'
import ReportsView from '../views/ReportsView.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: DashboardView },
  { path: '/customers', component: CustomersView },
  { path: '/applications', component: ApplicationsView },
  { path: '/loans', component: LoansView },
  { path: '/collateral', component: CollateralView },
  { path: '/payments', component: PaymentsView },
  { path: '/reports', component: ReportsView },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
