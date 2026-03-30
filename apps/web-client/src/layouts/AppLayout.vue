<template>
  <div class="app-shell">
    <aside class="sidebar">
      <h1 class="brand">{{ t('app.title') }}</h1>
      <nav class="nav">
        <RouterLink to="/dashboard" class="nav-link">{{ t('app.dashboard') }}</RouterLink>
        <RouterLink to="/customers" class="nav-link">{{ t('app.customers') }}</RouterLink>
        <RouterLink to="/loans" class="nav-link">{{ t('app.loans') }}</RouterLink>
        <RouterLink to="/collateral" class="nav-link">{{ t('app.collateral') }}</RouterLink>
        <RouterLink to="/payments" class="nav-link">{{ t('app.payments') }}</RouterLink>
        <RouterLink to="/reporting" class="nav-link">{{ t('app.reporting') }}</RouterLink>
      </nav>
    </aside>

    <main class="content">
      <header class="topbar">
        <span>{{ t('app.subtitle') }}</span>
        <div class="topbar-actions">
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
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { persistLocale, type AppLocale } from '../i18n'

const { t, locale } = useI18n()
const selectedLocale = ref(locale.value as AppLocale)

const onLocaleChange = () => {
  locale.value = selectedLocale.value
  persistLocale(selectedLocale.value)
}
</script>
