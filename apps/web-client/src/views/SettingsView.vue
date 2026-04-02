<template>
  <section>
    <PageHeader :title="t('settings.title')" :subtitle="t('settings.subtitle')">
      <template #icon>
        <Settings :size="18" />
      </template>
    </PageHeader>

    <p v-if="message" class="notice mt-16">{{ message }}</p>

    <form class="card form mt-16" @submit.prevent="handleSaveSettings">
      <div class="grid grid-2">
        <label>
          {{ t('settings.currencyCode') }}
          <select v-model="form.currencyCode" required>
            <option value="COP">COP</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
          </select>
        </label>
        <label>
          {{ t('settings.timezone') }}
          <input v-model="form.timezone" required />
        </label>
        <label>
          {{ t('settings.dateFormat') }}
          <select v-model="form.dateFormat" required>
            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
          </select>
        </label>
        <label>
          {{ t('settings.defaultLatePenaltyRate') }}
          <input v-model.number="form.defaultLatePenaltyRate" type="number" min="0" step="0.1" required />
        </label>
      </div>
      <button class="btn" type="submit">
        <Save :size="16" />
        {{ t('settings.saveSettings') }}
      </button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Save, Settings } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, ensureInitialized, updateGlobalSettings } = useMockPlatformStore()
const { t } = useI18n()
const message = ref('')

const form = reactive({
  currencyCode: 'COP',
  timezone: 'America/Bogota',
  dateFormat: 'DD/MM/YYYY',
  defaultLatePenaltyRate: 0
})

onMounted(async () => {
  await ensureInitialized()
  if (state.globalSettings) {
    form.currencyCode = state.globalSettings.currencyCode
    form.timezone = state.globalSettings.timezone
    form.dateFormat = state.globalSettings.dateFormat
    form.defaultLatePenaltyRate = state.globalSettings.defaultLatePenaltyRate
  }
})

const handleSaveSettings = async () => {
  try {
    const result = await updateGlobalSettings({ ...form })
    message.value = t(result.messageKey)
  } catch {
    message.value = t('messages.operationFailed')
  }
}
</script>
