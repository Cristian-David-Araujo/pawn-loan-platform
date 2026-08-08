<template>
  <main class="login-page">
    <!-- Not only so this screen can be read: the recovery email is written in whatever is
         selected here, and this is the last moment the operator can say. -->
    <div class="login-page-toolbar">
      <LocaleSelect id="forgot-locale" />
    </div>

    <section class="login-card card">
      <div class="login-brand">
        <span class="login-brand-icon">
          <BrandMark :size="30" />
        </span>
      </div>
      <header class="login-header">
        <h1 class="page-title">{{ t('auth.forgotPasswordTitle') }}</h1>
        <p class="page-subtitle">{{ t('auth.forgotPasswordSubtitle') }}</p>
      </header>

      <p v-if="error" class="notice notice-error">{{ error }}</p>
      <p v-if="successMessage" class="notice notice-success">{{ successMessage }}</p>

      <div v-if="devResetToken" class="notice notice-info auth-dev-token">
        <span>{{ t('auth.devModeNotice') }}: </span>
        <router-link :to="`/reset-password?token=${devResetToken}`">
          {{ devResetToken }}
        </router-link>
      </div>

      <form v-if="!successMessage || devResetToken" class="login-form mt-24" @submit.prevent="handleSubmit">
        <label>
          {{ t('auth.usernameOrEmail') }}
          <input v-model="identifier" type="text" autocomplete="username" required />
        </label>

        <button class="btn" type="submit" :disabled="isSubmitting" :class="{ 'is-loading': isSubmitting }">
          <Send v-if="!isSubmitting" :size="16" aria-hidden="true" />
          {{ isSubmitting ? t('auth.sendingLink') : t('auth.sendResetLink') }}
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
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Send, ArrowLeft } from 'lucide-vue-next'
import BrandMark from '../components/BrandMark.vue'
import LocaleSelect from '../components/LocaleSelect.vue'
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
    /* Deliberately ignores `res.message`. The API answers with one hardcoded Spanish
       sentence, and it is always present — so the `||` fallback never ran and the translated
       key was dead: an operator working in English submitted this form and was answered in
       Spanish. The anti-enumeration guarantee is unaffected, because this is one constant
       string shown for every outcome, exactly like the server's. */
    successMessage.value = t('auth.recoverySentNotice')
    if (res.reset_token) {
      devResetToken.value = res.reset_token
    }
  } catch {
    /* This endpoint answers 200 for every identifier, so the only way to land here is that
       the request never got an answer. It used to print the raw thrown message — a browser's
       untranslated "Failed to fetch" — and fall back to "invalid credentials", which names a
       rejection that cannot happen on this screen. */
    error.value = t('auth.serviceUnreachable')
  } finally {
    isSubmitting.value = false
  }
}
</script>
