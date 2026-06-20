<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'sidebar-open': mobileMenuOpen }">
      <div class="brand-wrap">
        <span class="brand-logo">
          <Shield :size="18" />
        </span>
        <div>
          <h1 class="brand">{{ state.globalSettings?.appName || t('app.title') }}</h1>
          <p v-if="state.globalSettings?.companyName" class="brand-subtitle">{{ state.globalSettings.companyName }}</p>
        </div>
      </div>

      <p class="nav-title">{{ t('app.navigation') }}</p>
      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          @click="mobileMenuOpen = false"
        >
          <component :is="item.icon" :size="16" />
          <span>{{ t(item.labelKey) }}</span>
        </RouterLink>
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

    <main class="content">
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
          />
          <CustomSelect 
            id="locale-select" 
            v-model="selectedLocale" 
            inputClass="locale-select" 
            :options="localeOptions"
            @change="onLocaleChange" 
          />
          <button class="btn btn-secondary" type="button" @click="handleLogout">
            <LogOut :size="15" />
            {{ t('app.signOut') }}
          </button>
        </div>
      </header>
      <section class="page fade-in-up">
        <RouterView />
      </section>
    </main>
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
  PanelLeft,
  Package,
  ReceiptText,
  Settings,
  Shield,
  Users
} from 'lucide-vue-next'
import { persistLocale, type AppLocale } from '../i18n'
import { useAuthState, UserRole } from '../modules/authentication/authState'
import { usePlatformStore } from '../stores/platformStore'
import CustomerAutocomplete from '../components/CustomerAutocomplete.vue'
import CustomSelect from '../components/CustomSelect.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const { state: authState, logout, hasRole } = useAuthState()

const navItems = computed(() => {
  const items = [
    { to: '/dashboard', labelKey: 'app.dashboard', icon: LayoutDashboard },
    { to: '/customers', labelKey: 'app.customers', icon: Users },
    { to: '/loans', labelKey: 'app.loans', icon: HandCoins },
    { to: '/collaterals', labelKey: 'app.collateral', icon: Shield },
    { to: '/payments', labelKey: 'app.payments', icon: ReceiptText }
  ]
  if (hasRole([UserRole.Administrator, UserRole.LoanOfficer])) {
    items.push({ to: '/reporting', labelKey: 'app.reporting', icon: BarChart3 })
  }
  if (hasRole([UserRole.Administrator])) {
    items.push({ to: '/settings', labelKey: 'app.settings', icon: Settings })
    items.push({ to: '/users', labelKey: 'app.users', icon: Shield })
  }
  return items
})

const { state } = usePlatformStore()

const selectedLocale = ref(locale.value as AppLocale)
const localeOptions = [
  { value: 'en', label: 'EN' },
  { value: 'es', label: 'ES' }
]
const customerSearch = ref('')
const selectedCustomerId = ref<number | null>(null)
const mobileMenuOpen = ref(false)
const currentUsername = computed(() => authState.currentUser?.full_name || authState.username || 'admin')
const userInitial = computed(() => currentUsername.value.charAt(0).toUpperCase())

const currentRouteLabel = computed(() => {
  const labelKey = (route.meta.labelKey as string | undefined) ?? 'app.dashboard'
  return t(labelKey)
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

const onLocaleChange = () => {
  locale.value = selectedLocale.value
  persistLocale(selectedLocale.value)
}

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

.sidebar-user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  font-weight: 700;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.sidebar-user-info {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.sidebar-user-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #f1f5f9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-user-role {
  font-size: 0.72rem;
  color: #64748b;
}
</style>

