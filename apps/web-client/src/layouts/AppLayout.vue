<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'sidebar-open': mobileMenuOpen }">
      <div class="brand-wrap">
        <span class="brand-logo">
          <Shield :size="18" />
        </span>
        <div>
          <h1 class="brand">{{ t('app.title') }}</h1>
          <p class="brand-subtitle">{{ t('app.subtitle') }}</p>
        </div>
      </div>

      <p class="nav-title">{{ t('app.navigation') }}</p>
      <nav class="nav">
        <RouterLink
          v-for="item in filteredNavItems"
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
        <span class="badge">{{ t('app.noBackendMode') }}</span>
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
          <label class="locale-label" for="nav-filter">{{ t('common.search') }}</label>
          <input
            id="nav-filter"
            v-model="navFilter"
            class="topbar-search"
            type="text"
            :placeholder="t('app.searchPlaceholder')"
          />
          <label class="locale-label" for="locale-select">{{ t('app.language') }}</label>
          <select id="locale-select" v-model="selectedLocale" class="locale-select" @change="onLocaleChange">
            <option value="en">English</option>
            <option value="es">Espanol</option>
          </select>
        </div>
      </header>
      <section class="page">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import {
  BarChart3,
  HandCoins,
  LayoutDashboard,
  PanelLeft,
  ReceiptText,
  Shield,
  Users
} from 'lucide-vue-next'
import { persistLocale, type AppLocale } from '../i18n'

const { t, locale } = useI18n()
const route = useRoute()

const navItems = [
  { to: '/dashboard', labelKey: 'app.dashboard', icon: LayoutDashboard },
  { to: '/customers', labelKey: 'app.customers', icon: Users },
  { to: '/loans', labelKey: 'app.loans', icon: HandCoins },
  { to: '/payments', labelKey: 'app.payments', icon: ReceiptText },
  { to: '/reporting', labelKey: 'app.reporting', icon: BarChart3 }
]

const selectedLocale = ref(locale.value as AppLocale)
const navFilter = ref('')
const mobileMenuOpen = ref(false)

const currentRouteLabel = computed(() => {
  const labelKey = (route.meta.labelKey as string | undefined) ?? 'app.dashboard'
  return t(labelKey)
})

const filteredNavItems = computed(() => {
  const query = navFilter.value.trim().toLowerCase()
  if (!query) {
    return navItems
  }

  return navItems.filter((item) => t(item.labelKey).toLowerCase().includes(query))
})

const onLocaleChange = () => {
  locale.value = selectedLocale.value
  persistLocale(selectedLocale.value)
}
</script>
