<template>
  <main class="login-page">
    <section class="login-card card">
      <div class="login-brand">
        <span class="login-brand-icon">
          <BrandMark :size="30" />
        </span>
      </div>
      <header class="login-header">
        <h1 class="page-title">{{ t('auth.resetPasswordTitle') }}</h1>
        <p class="page-subtitle">{{ t('auth.resetPasswordSubtitle') }}</p>
      </header>

      <p v-if="error" class="notice notice-error">{{ error }}</p>
      <p v-if="successMessage" class="notice notice-success">{{ successMessage }}</p>

      <form v-if="!successMessage" class="login-form mt-24" @submit.prevent="handleSubmit">
        <label>
          {{ t('auth.newPassword') }}
          <PasswordInput v-model="form.newPassword" autocomplete="new-password" required minlength="8" />
        </label>

        <label>
          {{ t('auth.confirmPassword') }}
          <PasswordInput v-model="form.confirmPassword" autocomplete="new-password" required minlength="8" />
        </label>

        <button class="btn" type="submit" :disabled="isSubmitting" :class="{ 'is-loading': isSubmitting }">
          <CheckCircle2 v-if="!isSubmitting" :size="16" aria-hidden="true" />
          {{ isSubmitting ? t('auth.resettingPassword') : t('auth.resetPasswordTitle') }}
        </button>
      </form>

      <div class="auth-link-center">
        <router-link class="auth-link" to="/login">
          <ArrowLeft :size="16" aria-hidden="true" />
          {{ t('auth.backToLogin') }}
        </router-link>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { CheckCircle2, ArrowLeft } from 'lucide-vue-next'
import BrandMark from '../components/BrandMark.vue'
import PasswordInput from '../components/PasswordInput.vue'
import { useAuthState } from '../modules/authentication/authState'

const { t } = useI18n()
const route = useRoute()
const { resetPassword } = useAuthState()

const token = ref('')
const isSubmitting = ref(false)
const error = ref('')
const successMessage = ref('')

const form = reactive({
  newPassword: '',
  confirmPassword: ''
})

onMounted(() => {
  if (typeof route.query.token === 'string') {
    token.value = route.query.token
  }
})

const handleSubmit = async () => {
  if (isSubmitting.value) return

  error.value = ''
  successMessage.value = ''

  // Was a hardcoded Spanish literal, so an English session was answered in Spanish.
  if (!token.value) {
    error.value = t('auth.missingResetToken')
    return
  }

  if (form.newPassword.length < 8) {
    error.value = t('auth.passwordTooShort')
    return
  }

  if (form.newPassword !== form.confirmPassword) {
    error.value = t('auth.passwordMismatch')
    return
  }

  isSubmitting.value = true

  try {
    const res = await resetPassword(token.value, form.newPassword)
    successMessage.value = res.message || t('auth.passwordResetSuccess')
  } catch (err: any) {
    error.value = err.message || t('auth.resetPasswordFailed')
  } finally {
    isSubmitting.value = false
  }
}
</script>
