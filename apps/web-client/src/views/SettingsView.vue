<template>
  <section>
    <PageHeader :title="t('settings.title')" :subtitle="t('settings.subtitle')">
      <template #icon>
        <Settings :size="18" />
      </template>
    </PageHeader>

    <p v-if="message" class="notice mt-16">{{ message }}</p>

    <article class="card mt-16">
      <h3>{{ t('settings.colombiaPresetTitle') }}</h3>
      <p class="muted">{{ t('settings.colombiaPresetHint') }}</p>
      <button class="btn btn-secondary mt-16" type="button" @click="applyColombiaPreset">
        <Sparkles :size="16" />
        {{ t('settings.applyColombiaPreset') }}
      </button>
    </article>

    <form class="form mt-16" @submit.prevent="handleSaveSettings">
      <div class="card mb-16">
        <h3>{{ t('settings.companyInfoTitle') }}</h3>
        <p class="muted">{{ t('settings.companyInfoHint') }}</p>
        <div class="grid grid-2 mt-16">
          <label :title="t('settings.appNameHelp')">
            <span class="field-label-row">
              {{ t('settings.appName') }}
              <span class="field-help" aria-hidden="true">ⓘ</span>
            </span>
            <input v-model="form.appName" required :title="t('settings.appNameHelp')" />
          </label>
          <label>
            <span class="field-label-row">
              {{ t('settings.companyName') }}
            </span>
            <input v-model="form.companyName" />
          </label>
          <label>
            <span class="field-label-row">
              {{ t('settings.companyDocumentType') }}
            </span>
            <CustomSelect v-model="form.companyDocumentType" :options="documentTypeOptions" />
          </label>
          <label>
            <span class="field-label-row">
              {{ t('settings.companyDocumentNumber') }}
            </span>
            <input v-model="form.companyDocumentNumber" />
          </label>
          <label>
            <span class="field-label-row">
              {{ t('settings.companyAddress') }}
            </span>
            <input v-model="form.companyAddress" />
          </label>
          <label>
            <span class="field-label-row">
              {{ t('settings.companyPhone') }}
            </span>
            <input v-model="form.companyPhone" />
          </label>
          <label>
            <span class="field-label-row">
              {{ t('settings.companyEmail') }}
            </span>
            <input v-model="form.companyEmail" type="email" />
          </label>
        </div>
      </div>

      <div class="card">
        <div class="grid grid-2">
        <label :title="t('settings.currencyCodeHelp')">
          <span class="field-label-row">
            {{ t('settings.currencyCode') }}
            <span class="field-help" aria-hidden="true">ⓘ</span>
          </span>
          <CustomSelect v-model="form.currencyCode" :options="currencyOptions" />
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
          <CustomSelect v-model="form.dateFormat" :options="dateFormatOptions" />
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
      </div>

      <div class="mt-16 text-right">
        <button class="btn" type="submit">
          <Save :size="16" />
          {{ t('settings.saveSettings') }}
        </button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import CustomSelect from '../components/CustomSelect.vue'
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Save, Settings, Sparkles } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { usePlatformStore } from '../stores/platformStore'

const { state, ensureInitialized, updateGlobalSettings } = usePlatformStore()
const { t } = useI18n()
const message = ref('')

const currencyOptions = [
  { value: 'COP', label: 'COP' },
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' }
]

const dateFormatOptions = [
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' },
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' }
]

const documentTypeOptions = ['CC', 'TI', 'NIT', 'CE', 'PAS', 'RUT'].map(o => ({
  value: o,
  label: o
}))

const form = reactive({
  appName: 'PawnPlatform',
  companyName: '',
  companyDocumentType: 'NIT',
  companyDocumentNumber: '',
  companyAddress: '',
  companyPhone: '',
  companyEmail: '',
  currencyCode: 'COP',
  timezone: 'America/Bogota',
  dateFormat: 'DD/MM/YYYY',
  defaultLatePenaltyRate: 0,
  interestGenerationLeadDays: 10
})

onMounted(async () => {
  await ensureInitialized()
  if (state.globalSettings) {
    form.appName = state.globalSettings.appName || 'PawnPlatform'
    form.companyName = state.globalSettings.companyName || ''
    form.companyDocumentType = state.globalSettings.companyDocumentType || 'NIT'
    form.companyDocumentNumber = state.globalSettings.companyDocumentNumber || ''
    form.companyAddress = state.globalSettings.companyAddress || ''
    form.companyPhone = state.globalSettings.companyPhone || ''
    form.companyEmail = state.globalSettings.companyEmail || ''
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

const applyColombiaPreset = () => {
  form.currencyCode = 'COP'
  form.timezone = 'America/Bogota'
  form.dateFormat = 'DD/MM/YYYY'
}
</script>
