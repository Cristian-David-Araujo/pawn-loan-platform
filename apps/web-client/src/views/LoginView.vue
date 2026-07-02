<template>
  <main class="login-page">
    <section class="login-card card">
      <div class="login-brand">
        <span class="login-brand-icon">
          <Shield :size="28" />
        </span>
      </div>
      <header class="login-header">
        <h1 class="page-title">{{ appName || t('auth.title') }}</h1>
        <p v-if="companyName" class="page-subtitle">{{ companyName }}</p>
      </header>

      <p v-if="error" class="notice notice-error">{{ error }}</p>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label>
          {{ t('auth.username') }}
          <input v-model="form.username" type="text" autocomplete="username" required />
        </label>

        <label>
          {{ t('auth.password') }}
          <PasswordInput v-model="form.password" autocomplete="current-password" required />
        </label>

        <div style="text-align: right; margin-top: -0.2rem; margin-bottom: 0.5rem;">
          <router-link to="/forgot-password" style="font-size: 0.85rem; color: var(--color-primary, #2563eb); text-decoration: none; font-weight: 500;">
            {{ t('auth.forgotPassword') }}
          </router-link>
        </div>

        <button class="btn" type="submit" :disabled="isSubmitting" style="width: 100%; justify-content: center;">
          <LogIn v-if="!isSubmitting" :size="16" />
          {{ isSubmitting ? t('auth.signingIn') : t('auth.signIn') }}
        </button>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Shield, LogIn } from 'lucide-vue-next'
import PasswordInput from '../components/PasswordInput.vue'
import { useAuthState } from '../modules/authentication/authState'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { login } = useAuthState()

const isSubmitting = ref(false)
const error = ref('')
const appName = ref('')
const companyName = ref('')
const form = reactive({
  username: '',
  password: ''
})

const fetchSettings = async () => {
  try {
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
    const response = await fetch(`${API_BASE_URL}/settings`)
    if (response.ok) {
      const settings = await response.json()
      appName.value = settings.app_name
      companyName.value = settings.company_name
    }
  } catch (err) {
    // ignore
  }
}

fetchSettings()

const handleSubmit = async () => {
  if (isSubmitting.value) {
    return
  }

  isSubmitting.value = true
  error.value = ''

  try {
    await login({ username: form.username, password: form.password })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.replace(redirect)
  } catch {
    error.value = t('auth.invalidCredentials')
  } finally {
    isSubmitting.value = false
  }
}
</script>
