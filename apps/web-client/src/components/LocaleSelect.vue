<template>
  <CustomSelect
    :id="id"
    v-model="selected"
    :options="localeOptions"
    :inputClass="inputClass"
    :ariaLabel="t('app.language')"
    @change="onChange"
  />
</template>

<script setup lang="ts">
/*
  The language switcher, in one place.

  It exists as a component rather than as markup in AppLayout because the sign-in screens need
  it too, and they are outside AppLayout: a browser detected as English lands an operator on a
  login page they cannot read, with no control anywhere on it. That also decides something the
  operator cannot revisit later — the language of the password recovery email, which
  `forgot-password` sends along with the identifier while there is still no session.

  Changing it goes through `setLocale`, which applies, stores and updates <html lang> together.
*/
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import CustomSelect from './CustomSelect.vue'
import { setLocale, type AppLocale } from '../i18n'

defineProps<{
  id?: string
  inputClass?: string
}>()

const { t, locale } = useI18n()

const localeOptions = [
  // Endonyms: a reader who cannot read the current interface language can still find their own.
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'English' }
]

const selected = ref(locale.value as AppLocale)

// Two of these can be mounted at once (the app bar has one, a modal or the auth screen
// another), and the locale can also change from elsewhere. Following the global value keeps
// every copy showing the same answer.
watch(locale, (value) => {
  selected.value = value as AppLocale
})

const onChange = (value: string | number | null) => {
  if (value === 'en' || value === 'es') {
    setLocale(value)
  }
}
</script>
