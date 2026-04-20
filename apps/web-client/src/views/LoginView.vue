<template>
  <main class="login-page">
    <section class="login-card card">
      <div class="login-brand">
        <span class="login-brand-icon">
          <Shield :size="28" />
        </span>
      </div>
      <header class="login-header">
        <h1 class="page-title">{{ t('auth.title') }}</h1>
        <p class="page-subtitle">{{ t('auth.subtitle') }}</p>
      </header>

      <p v-if="error" class="notice" style="background: var(--danger-soft); color: #b91c1c; border-color: var(--danger-border);">{{ error }}</p>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label>
          {{ t('auth.username') }}
          <input v-model="form.username" type="text" autocomplete="username" required />
        </label>

        <label>
          {{ t('auth.password') }}
          <input v-model="form.password" type="password" autocomplete="current-password" required />
        </label>

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
import { useAuthState } from '../modules/authentication/authState'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { login } = useAuthState()

const isSubmitting = ref(false)
const error = ref('')
const form = reactive({
  username: '',
  password: ''
})

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
