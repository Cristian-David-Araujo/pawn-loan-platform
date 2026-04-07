<template>
  <main class="login-page">
    <section class="login-card card">
      <header class="login-header">
        <h1 class="page-title">{{ t('auth.title') }}</h1>
        <p class="page-subtitle">{{ t('auth.subtitle') }}</p>
      </header>

      <p v-if="error" class="notice">{{ error }}</p>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label>
          {{ t('auth.username') }}
          <input v-model="form.username" type="text" autocomplete="username" required />
        </label>

        <label>
          {{ t('auth.password') }}
          <input v-model="form.password" type="password" autocomplete="current-password" required />
        </label>

        <button class="btn" type="submit" :disabled="isSubmitting">
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

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1.25rem;
}

.login-card {
  width: min(460px, 100%);
}

.login-header {
  margin-bottom: 1rem;
}

.login-form {
  display: grid;
  gap: 0.85rem;
}

.login-form label {
  display: grid;
  gap: 0.35rem;
  font-weight: 600;
}
</style>
