import { createRouter, createWebHistory } from 'vue-router'
import { useAuthState, UserRole } from '../modules/authentication/authState'
import AppLayout from '../layouts/AppLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import CustomersView from '../views/CustomersView.vue'
import LoansView from '../views/LoansView.vue'
import LoginView from '../views/LoginView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
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
      path: '/forgot-password',
      name: 'forgot-password',
      component: ForgotPasswordView,
      meta: { guestOnly: true }
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: ResetPasswordView,
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
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', name: 'dashboard', component: DashboardView, meta: { labelKey: 'app.dashboard' } },
        { path: 'customers', name: 'customers', component: CustomersView, meta: { labelKey: 'app.customers' } },
        /* A record with its own identity gets its own address.
         *
         * The customer detail was a modal, and modals stack: from inside it an operator could
         * open a loan detail, and from that an edit form, and from that a confirmation — up to
         * eight backdrops deep. It also could not be linked to, and the browser's back button
         * left the whole screen rather than the tab.
         *
         * The tab is in the path for the same reason the id is: "the payments of customer 7"
         * is a place, and back should return to the tab before it. */
        {
          path: 'customers/:id/:tab?',
          name: 'customer-detail',
          component: CustomersView,
          meta: { labelKey: 'app.customers' }
        },
        { path: 'loans', name: 'loans', component: LoansView, meta: { labelKey: 'app.loans' } },
        { path: 'loans/:id', name: 'loan-detail', component: LoansView, meta: { labelKey: 'app.loans' } },
        {
          path: 'collaterals',
          name: 'collaterals',
          component: () => import('../views/CollateralsView.vue'),
          meta: { labelKey: 'app.collateral' }
        },
        /* The singular spelling is the obvious guess and whatever older links exist. It used
           to redirect to /loans, which put an operator looking for the vault on the loan
           list with nothing saying they were on the wrong screen. */
        { path: 'collateral', redirect: '/collaterals' },
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

  /* Verify the stored token BEFORE deciding whether the route may be entered.
   *
   * These two steps used to be the other way round, and the order was the whole bug: a
   * token left in localStorage from an expired session made `isAuthenticated` true, so the
   * guard admitted the navigation, and only then awaited `/auth/me`. That call clears the
   * session on rejection — but the entry decision had already been made and was never
   * revisited, so the app opened straight onto a dashboard whose every request then failed,
   * showing a full screen of zeros. Reloading re-ran the guard, now with no token, and
   * finally landed on the sign-in screen: the "just refresh it" that made this look flaky
   * rather than broken.
   *
   * Having the token is not the same as having a session, and this is the line where the
   * difference is settled. */
  if (isAuthenticated.value && !state.currentUser) {
    await fetchCurrentUser()
  }

  if (to.matched.some((record) => record.meta.requiresAuth) && !isAuthenticated.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
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
