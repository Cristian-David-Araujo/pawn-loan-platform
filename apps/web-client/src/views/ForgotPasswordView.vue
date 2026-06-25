<template>
  <main class="login-page">
    <section class="login-card card">
      <div class="login-brand">
        <span class="login-brand-icon">
          <KeyRound :size="28" />
        </span>
      </div>
      <header class="login-header">
        <h1 class="page-title">{{ t('auth.forgotPasswordTitle') }}</h1>
        <p class="page-subtitle">{{ t('auth.forgotPasswordSubtitle') }}</p>
      </header>

      <p v-if="error" class="notice notice-error">{{ error }}</p>
      <p v-if="successMessage" class="notice notice-success">{{ successMessage }}</p>

      <div v-if="devResetToken" class="notice notice-info" style="margin-top: 1rem; word-break: break-all; font-size: 0.9rem;">
        <span>{{ t('auth.devModeNotice') }}: </span>
        <router-link :to="`/reset-password?token=${devResetToken}`" style="font-weight: bold; text-decoration: underline; color: inherit;">
          {{ devResetToken }}
        </router-link>
      </div>

      <form v-if="!successMessage || devResetToken" class="login-form" style="margin-top: 1.5rem;" @submit.prevent="handleSubmit">
        <label>
          {{ t('auth.usernameOrEmail') }}
          <input v-model="identifier" type="text" autocomplete="username" required />
        </label>

        <button class="btn" type="submit" :disabled="isSubmitting" style="width: 100%; justify-content: center; margin-top: 0.5rem;">
          <Send v-if="!isSubmitting" :size="16" />
          {{ isSubmitting ? t('auth.sendingLink') : t('auth.sendResetLink') }}
        </button>
      </form>

      <div style="margin-top: 1.5rem; text-align: center;">
        <router-link to="/login" style="display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.9rem; color: var(--color-primary, #2563eb); text-decoration: none; font-weight: 500;">
          <ArrowLeft :size="16" />
          {{ t('auth.backToLogin') }}
        </router-link>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { KeyRound, Send, ArrowLeft } from 'lucide-vue-next'
import { useAuthState } from '../modules/authentication/authState'

const { t } = useI18n()
const { forgotPassword } = useAuthState()

const identifier = ref('')
const isSubmitting = ref(false)
const error = ref('')
const successMessage = ref('')
const devResetToken = ref<string | null>(null)

const handleSubmit = async () => {
  if (isSubmitting.value || !identifier.value.trim()) return

  isSubmitting.value = true
  error.value = ''
  successMessage.value = ''
  devResetToken.value = null

  try {
    const res = await forgotPassword(identifier.value.trim())
    successMessage.value = res.message || t('auth.recoverySentNotice')
    if (res.reset_token) {
      devResetToken.value = res.reset_token
    }
  } catch (err: any) {
    error.value = err.message || t('auth.invalidCredentials')
  } finally {
    isSubmitting.value = false
  }
}
</script>
