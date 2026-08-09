<template>
  <div class="app-shell">
    <a class="skip-link" href="#main-content">{{ t('app.skipToContent') }}</a>
    <aside class="sidebar" :class="{ 'sidebar-open': mobileMenuOpen }">
      <div class="brand-wrap">
        <!--
          The full lockup, the same one that signs off the sign-in screen: the wordmark drawn
          in the product's own letterforms rather than typeset in whatever the interface font
          happens to be.

          It replaced a mark beside an <h1> holding GlobalSettings.app_name. That field is no
          longer editable, so the text could only ever read "Mutuum" — a second, weaker
          rendering of a name the logo already carries.

          Still an <h1>: PageHeader's title is an <h2>, so dropping this one would leave every
          screen without a top-level heading. The SVG carries aria-label="Mutuum", which is
          what gives the heading its accessible name.
        -->
        <h1 class="brand">
          <BrandLockup :height="18" />
        </h1>
        <!-- Whose business this is. The product logo says what the tool is; this says whose
             book you are looking at — the same order the sign-in card puts them in, and the
             same name that heads every printed document.

             The rule between them is doing real work: set directly under the wordmark, the
             company name read as a tagline of Mutuum rather than as a separate party. The
             rule appears only when there is a name, so it never divides the logo from
             nothing. -->
        <template v-if="state.globalSettings?.companyName">
          <div class="brand-divider" role="presentation"></div>
          <p class="brand-company">{{ state.globalSettings.companyName }}</p>
        </template>
      </div>

      <nav class="nav" :aria-label="t('app.navigation')">
        <div v-for="group in navGroups" :key="group.titleKey" class="nav-group">
          <p class="nav-title">{{ t(group.titleKey) }}</p>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            @click="mobileMenuOpen = false"
          >
            <component :is="item.icon" :size="16" />
            <span>{{ t(item.labelKey) }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-user">
          <span class="sidebar-user-avatar">{{ userInitial }}</span>
          <div class="sidebar-user-info">
            <span class="sidebar-user-name">{{ currentUsername }}</span>
            <span class="sidebar-user-role">{{ authState.currentUser ? t('roles.' + authState.currentUser.role, authState.currentUser.role) : '' }}</span>
          </div>
        </div>
      </div>
    </aside>
    <div v-if="mobileMenuOpen" class="sidebar-backdrop" @click="mobileMenuOpen = false"></div>

    <div class="content">
      <header class="topbar">
        <div class="topbar-left">
          <button class="menu-toggle" type="button" @click="mobileMenuOpen = !mobileMenuOpen">
            <PanelLeft :size="16" />
            {{ t('app.menu') }}
          </button>
          <div class="breadcrumbs">
            <span>{{ t('app.home') }}</span>
            <span>/</span>
            <strong>{{ currentRouteLabel }}</strong>
          </div>
        </div>
        <div class="topbar-actions">
          <CustomerAutocomplete
            id="nav-filter"
            v-model="selectedCustomerId"
            :customers="state.customers"
            inputClass="topbar-search"
            :placeholder="t('customers.searchPlaceholder')"
            :aria-label="t('customers.searchPlaceholder')"
          />
          <LocaleSelect id="locale-select" inputClass="locale-select" />
          <!-- Cycles system → light → dark. The label names the state it is in and the one
               it will move to, because a lone icon cannot say which of the three applies. -->
          <button
            class="btn btn-secondary btn-icon"
            type="button"
            :title="themeLabel"
            :aria-label="themeLabel"
            @click="cycleTheme"
          >
            <Monitor v-if="preference === 'system'" :size="15" aria-hidden="true" />
            <Sun v-else-if="preference === 'light'" :size="15" aria-hidden="true" />
            <Moon v-else :size="15" aria-hidden="true" />
          </button>
          <button class="btn btn-secondary" type="button" :aria-label="t('app.signOut')" @click="handleLogout">
            <LogOut :size="15" aria-hidden="true" />
            <!-- The label is a real element so the mobile rule can hide it. It used to be a
                 bare text node, which left `font-size: 0` on the button as the only way to
                 suppress it — a trick that also silently shrank anything else inside. -->
            <span class="btn-label">{{ t('app.signOut') }}</span>
          </button>
        </div>
      </header>
      <main id="main-content" class="page fade-in-up" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  BarChart3,
  HandCoins,
  LayoutDashboard,
  LogOut,
  Monitor,
  Moon,
  PanelLeft,
  ReceiptText,
  Settings,
  Shield,
  Sun,
  UserCog,
  Users
} from 'lucide-vue-next'
import { useAuthState, UserRole } from '../modules/authentication/authState'
import { usePlatformStore } from '../stores/platformStore'
import BrandLockup from '../components/BrandLockup.vue'
import CustomerAutocomplete from '../components/CustomerAutocomplete.vue'
import LocaleSelect from '../components/LocaleSelect.vue'
import { useTheme, type ThemePreference } from '../composables/useTheme'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { state: authState, logout, hasRole } = useAuthState()

/*
 * Two groups, because the list is not one kind of thing.
 *
 * It used to be a single flat run of up to eight links with the role-gated ones appended to
 * the end, so the daily working screens and the administrative ones were told apart only by
 * where they happened to stop. The split is the one the permissions already make: the top
 * group is what a collector can reach, the bottom is what needs a loan officer or an
 * administrator. Each carries its own heading, replacing a single "Navigation" label that
 * named nothing a list of links does not already say.
 *
 * Dashboard leads. An earlier arrangement put Payments first on the argument that the
 * collector lives there and the dashboard only reports — but the panel is where everyone
 * lands after signing in and where the day gets oriented, and a home that is fifth in its own
 * menu reads as an afterthought.
 *
 * Users takes UserCog. It shared `Shield` with Collateral, and in a flat dark sidebar the
 * icon is the fastest scan target — two destinations rendering the same glyph is how someone
 * lands on the vault when they wanted permissions.
 */
const navGroups = computed(() => {
  const groups = [
    {
      titleKey: 'app.navOperation',
      items: [
        { to: '/dashboard', labelKey: 'app.dashboard', icon: LayoutDashboard },
        { to: '/payments', labelKey: 'app.payments', icon: ReceiptText },
        { to: '/customers', labelKey: 'app.customers', icon: Users },
        { to: '/loans', labelKey: 'app.loans', icon: HandCoins },
        { to: '/collaterals', labelKey: 'app.collateral', icon: Shield }
      ]
    }
  ]

  // Typed off the group above rather than spelled out, so the icon's component type stays
  // whatever lucide-vue-next exports and the two lists cannot drift apart.
  const management: (typeof groups)[0]['items'] = []
  if (hasRole([UserRole.Administrator, UserRole.LoanOfficer])) {
    management.push({ to: '/reporting', labelKey: 'app.reporting', icon: BarChart3 })
  }
  if (hasRole([UserRole.Administrator])) {
    management.push({ to: '/settings', labelKey: 'app.settings', icon: Settings })
    management.push({ to: '/users', labelKey: 'app.users', icon: UserCog })
  }

  // A collector sees no second group at all, rather than an empty heading over nothing.
  if (management.length) {
    groups.push({ titleKey: 'app.navManagement', items: management })
  }

  return groups
})

const { state } = usePlatformStore()

const customerSearch = ref('')
const selectedCustomerId = ref<number | null>(null)
const mobileMenuOpen = ref(false)
const currentUsername = computed(() => authState.currentUser?.full_name || authState.username || 'admin')
const userInitial = computed(() => currentUsername.value.charAt(0).toUpperCase())

const currentRouteLabel = computed(() => {
  const labelKey = (route.meta.labelKey as string | undefined) ?? 'app.dashboard'
  return t(labelKey)
})

const { preference, cycleTheme } = useTheme()

const THEME_ORDER: ThemePreference[] = ['system', 'light', 'dark']
const themeName = (value: ThemePreference) =>
  t(value === 'system' ? 'app.themeSystem' : value === 'light' ? 'app.themeLight' : 'app.themeDark')

const themeLabel = computed(() => {
  const next = THEME_ORDER[(THEME_ORDER.indexOf(preference.value) + 1) % THEME_ORDER.length]
  return t('app.themeSwitchTo', { current: themeName(preference.value), next: themeName(next) })
})

watch(
  () => route.query.q,
  (value) => {
    customerSearch.value = typeof value === 'string' ? value : ''
    // Try to auto-select customer if they match the query exactly
    if (customerSearch.value) {
      const match = state.customers.find(c => c.fullName === customerSearch.value || c.documentNumber === customerSearch.value)
      if (match) {
        selectedCustomerId.value = match.id
      } else {
        selectedCustomerId.value = null
      }
    } else {
      selectedCustomerId.value = null
    }
  },
  { immediate: true }
)

watch(selectedCustomerId, (id) => {
  if (id) {
    const cust = state.customers.find(c => c.id === id)
    if (cust) {
      mobileMenuOpen.value = false
      void router.push({ name: 'customers', query: { q: cust.fullName } })
    }
  } else if (!customerSearch.value) {
    // If cleared, maybe go to customers without filter?
    // Actually just do nothing.
  }
})

const handleLogout = () => {
  logout()
  mobileMenuOpen.value = false
  void router.push('/login')
}


</script>

<style scoped>
.sidebar-user {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  width: 100%;
}

/* A squircle rather than a circle, and flat rather than the indigo gradient it
   used to carry: the avatar is an identifier, not a brand mark. */
.sidebar-user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.1);
  color: var(--sidebar-text);
  font-weight: 700;
  font-size: var(--fs-sm);
  flex-shrink: 0;
}

.sidebar-user-info {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.sidebar-user-name {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--sidebar-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Lightened from the previous cool slate, which sat at 3.3:1 on the sidebar and failed AA
   for the one label that tells an operator which permissions they hold. */
.sidebar-user-role {
  font-size: var(--fs-xs);
  color: var(--sidebar-muted);
  text-transform: capitalize;
}
</style>

