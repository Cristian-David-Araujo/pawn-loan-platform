<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'sidebar-open': mobileMenuOpen }">
      <h1 class="brand">{{ t('app.title') }}</h1>
      <p class="brand-subtitle">{{ t('app.subtitle') }}</p>
      <p class="nav-title">{{ t('app.navigation') }}</p>
      <nav class="nav">
        <RouterLink
          v-for="item in filteredNavItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          @click="mobileMenuOpen = false"
        >
          {{ t(item.labelKey) }}
        </RouterLink>
      </nav>
    </aside>
    <div v-if="mobileMenuOpen" class="sidebar-backdrop" @click="mobileMenuOpen = false"></div>

    <main class="content">
      <header class="topbar">
        <div class="topbar-left">
          <button class="menu-toggle" type="button" @click="mobileMenuOpen = !mobileMenuOpen">{{ t('app.menu') }}</button>
          <div class="breadcrumbs">
            <span>{{ t('app.home') }}</span>
            <span>/</span>
            <strong>{{ currentRouteLabel }}</strong>
          </div>
        </div>
        <div class="topbar-actions">
          <label class="locale-label" for="quick-nav">{{ t('app.quickGo') }}</label>
          <select id="quick-nav" v-model="quickNav" class="locale-select" @change="onQuickNavigate">
            <option v-for="item in navItems" :key="item.to" :value="item.to">{{ t(item.labelKey) }}</option>
          </select>
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
          <span class="badge">{{ t('app.noBackendMode') }}</span>
        </div>
      </header>
      <section class="page">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { persistLocale, type AppLocale } from '../i18n'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const navItems = [
  { to: '/dashboard', labelKey: 'app.dashboard' },
  { to: '/customers', labelKey: 'app.customers' },
  { to: '/loans', labelKey: 'app.loans' },
  { to: '/collateral', labelKey: 'app.collateral' },
  { to: '/payments', labelKey: 'app.payments' },
  { to: '/reporting', labelKey: 'app.reporting' }
]

const selectedLocale = ref(locale.value as AppLocale)
const quickNav = ref(route.path)
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

watch(
  () => route.path,
  (value) => {
    quickNav.value = value
  }
)

const onLocaleChange = () => {
  locale.value = selectedLocale.value
  persistLocale(selectedLocale.value)
}

const onQuickNavigate = () => {
  router.push(quickNav.value)
}
</script>
