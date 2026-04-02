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
        <label :title="t('settings.currencyCodeHelp')">
          <span class="field-label-row">
            {{ t('settings.currencyCode') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
          <select v-model="form.currencyCode" required>
            <option value="COP">COP</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
          </select>
        </label>
        <label :title="t('settings.timezoneHelp')">
          <span class="field-label-row">
            {{ t('settings.timezone') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
          <input v-model="form.timezone" required :title="t('settings.timezoneHelp')" />
        </label>
        <label :title="t('settings.dateFormatHelp')">
          <span class="field-label-row">
            {{ t('settings.dateFormat') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
          <select v-model="form.dateFormat" required>
            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
          </select>
        </label>
        <label :title="t('settings.defaultLatePenaltyRateHelp')">
          <span class="field-label-row">
            {{ t('settings.defaultLatePenaltyRate') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
          <input
            v-model.number="form.defaultLatePenaltyRate"
            type="number"
            min="0"
            step="0.1"
            required
            :title="t('settings.defaultLatePenaltyRateHelp')"
          />
        </label>
        <label :title="t('settings.interestGenerationLeadDaysHelp')">
          <span class="field-label-row">
            {{ t('settings.interestGenerationLeadDays') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
          <input
            v-model.number="form.interestGenerationLeadDays"
            type="number"
            min="0"
            max="31"
            step="1"
            required
            :title="t('settings.interestGenerationLeadDaysHelp')"
          />
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
  defaultLatePenaltyRate: 0,
  interestGenerationLeadDays: 0
})

onMounted(async () => {
  await ensureInitialized()
  if (state.globalSettings) {
    form.currencyCode = state.globalSettings.currencyCode
    form.timezone = state.globalSettings.timezone
    form.dateFormat = state.globalSettings.dateFormat
    form.defaultLatePenaltyRate = state.globalSettings.defaultLatePenaltyRate
    form.interestGenerationLeadDays = state.globalSettings.interestGenerationLeadDays
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
