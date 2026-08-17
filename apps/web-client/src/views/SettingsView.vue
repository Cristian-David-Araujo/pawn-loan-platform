<template>
  <section>
    <PageHeader :title="t('settings.title')" :subtitle="t('settings.subtitle')">
      <template #icon>
        <Settings :size="18" />
      </template>
    </PageHeader>

    <p v-if="message" :class="[messageClass, 'mt-16']">{{ message }}</p>

    <!--
      Order matters on this page more than on any other.

      It used to open with a preset button, then Export, then the scheduled backup, and then
      the full-replace Import with its row-count table — and only after all of that, the
      settings the page is named after, with Save at the very bottom. An administrator
      coming here to change the grace days or the company name printed on receipts had to
      scroll past a destructive restore tool to reach them.

      Now: the settings and their Save first, then a Data section, with Import last because
      it is the most dangerous thing here.
    -->
    <form class="form mt-16" @submit.prevent="handleSaveSettings">
      <div class="card mb-16">
        <h3>{{ t('settings.companyInfoTitle') }}</h3>
        <p class="muted">{{ t('settings.companyInfoHint') }}</p>
        <div class="grid grid-2 mt-16">
          <!-- No hay campo para el nombre de la aplicación: Mutuum es el nombre del producto,
               no algo que cada instalación elija. El que sí es de la instalación es el de la
               empresa, aquí abajo, y tenerlos juntos en el mismo formulario fue lo que
               permitió renombrar el producto desde ajustes. -->
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

      <!-- Six fields sat in an unlabelled card while every other block on the page had a
           heading and a hint. Two of them — grace days and interest lead days — reach every
           loan in the book, so the card says so. -->
      <div class="card">
        <div class="section-head-split">
          <div>
            <h3>{{ t('settings.portfolioPolicyTitle') }}</h3>
            <p class="muted">{{ t('settings.portfolioPolicyHint') }}</p>
          </div>
          <!-- Moved here from the top of the page, where it was the first control an admin
               met and silently changed three fields 600px below it. -->
          <button class="btn btn-secondary" type="button" @click="applyColombiaPreset">
            <Sparkles :size="16" />
            {{ t('settings.applyColombiaPreset') }}
          </button>
        </div>
        <div class="grid grid-2 mt-16">
        <label :title="t('settings.currencyCodeHelp')">
          <span class="field-label-row">
            {{ t('settings.currencyCode') }}
            <Info class="field-help" :size="13" aria-hidden="true" />
          </span>
          <CustomSelect v-model="form.currencyCode" :options="currencyOptions" />
        </label>
        <label :title="t('settings.timezoneHelp')">
          <span class="field-label-row">
            {{ t('settings.timezone') }}
            <Info class="field-help" :size="13" aria-hidden="true" />
          </span>
          <input v-model="form.timezone" required :title="t('settings.timezoneHelp')" />
        </label>
        <label :title="t('settings.dateFormatHelp')">
          <span class="field-label-row">
            {{ t('settings.dateFormat') }}
            <Info class="field-help" :size="13" aria-hidden="true" />
          </span>
          <CustomSelect v-model="form.dateFormat" :options="dateFormatOptions" />
        </label>
        <label :title="t('settings.defaultLatePenaltyRateHelp')">
          <span class="field-label-row">
            {{ t('settings.defaultLatePenaltyRate') }}
            <Info class="field-help" :size="13" aria-hidden="true" />
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
            <Info class="field-help" :size="13" aria-hidden="true" />
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
        <label :title="t('settings.defaultGraceDaysHelp')">
          <span class="field-label-row">
            {{ t('settings.defaultGraceDays') }}
            <Info class="field-help" :size="13" aria-hidden="true" />
          </span>
          <input
            v-model.number="form.defaultGraceDays"
            type="number"
            min="0"
            max="31"
            step="1"
            required
            :title="t('settings.defaultGraceDaysHelp')"
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

    <h3 class="group-title mt-24">{{ t('settings.dataSectionTitle') }}</h3>
    <p class="muted">{{ t('settings.dataSectionHint') }}</p>

    <article class="card mt-16">
      <h3>{{ t('settings.exportDataTitle') }}</h3>
      <p class="muted">{{ t('settings.exportDataHint') }}</p>
      <p class="muted mt-8">{{ t('settings.exportDataWarning') }}</p>
      <button class="btn btn-secondary mt-16" type="button" :disabled="exporting" @click="handleExportData">
        <Download :size="16" />
        {{ exporting ? t('settings.exportDataInProgress') : t('settings.exportData') }}
      </button>
    </article>

    <ScheduledBackupCard />

    <!-- Last on the page. It wipes every table and reloads from the archive. -->
    <article class="card mt-16 import-card">
      <h3>{{ t('settings.importDataTitle') }}</h3>
      <p class="muted">{{ t('settings.importDataHint') }}</p>
      <p class="muted mt-8"><strong>{{ t('settings.importDataWarning') }}</strong></p>

      <label class="mt-16">
        <span class="field-label-row">{{ t('settings.importFile') }}</span>
        <input type="file" accept=".zip,application/zip" :disabled="importing" @change="handleFileSelected" />
      </label>

      <p v-if="analyzing" class="muted mt-8">{{ t('settings.importAnalyzing') }}</p>

      <div v-if="analysis" class="mt-16">
        <p v-if="!analysis.can_import" class="notice">{{ t('settings.importNotPossible') }}</p>

        <ul v-if="analysis.errors.length" class="mt-8">
          <li v-for="error in analysis.errors" :key="error">{{ error }}</li>
        </ul>
        <ul v-if="analysis.warnings.length" class="mt-8">
          <li v-for="warning in analysis.warnings" :key="warning" class="muted">{{ warning }}</li>
        </ul>

        <p class="mt-8">
          {{ t('settings.importArchiveDate') }}: {{ formatDateDMY(analysis.archive_generated_at) }} ·
          {{ t('settings.importSchemaRevision') }}: {{ analysis.archive_schema_revision ?? '-' }}
        </p>

        <div class="table-wrap mt-8">
          <table>
            <thead>
              <tr>
                <th>{{ t('settings.importTable') }}</th>
                <th class="text-right">{{ t('settings.importCurrentRows') }}</th>
                <th class="text-right">{{ t('settings.importIncomingRows') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="plan in analysis.tables" :key="plan.name">
                <td>{{ plan.name }}</td>
                <td class="text-right">{{ plan.current_rows }}</td>
                <td class="text-right">{{ plan.incoming_rows }}</td>
              </tr>
              <tr>
                <td><strong>{{ t('settings.importTotal') }}</strong></td>
                <td class="text-right"><strong>{{ analysis.total_current_rows }}</strong></td>
                <td class="text-right"><strong>{{ analysis.total_incoming_rows }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>

        <label v-if="analysis.can_import" class="mt-16">
          <span class="field-label-row">
            {{ t('settings.importConfirmationLabel', { phrase: IMPORT_CONFIRMATION }) }}
          </span>
          <input v-model="confirmation" :placeholder="IMPORT_CONFIRMATION" :disabled="importing" />
        </label>

        <button
          v-if="analysis.can_import"
          class="btn btn-danger mt-16"
          type="button"
          :disabled="importing || confirmation !== IMPORT_CONFIRMATION"
          @click="handleImportData"
        >
          <Upload :size="16" />
          {{ importing ? t('settings.importInProgress') : t('settings.importData') }}
        </button>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import CustomSelect from '../components/CustomSelect.vue'
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, Info, Save, Settings, Sparkles, Upload } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import ScheduledBackupCard from '../components/ScheduledBackupCard.vue'
import { usePageMessage } from '../composables/usePageMessage'
import { apiClient } from '../services/api'
import { usePlatformStore } from '../stores/platformStore'
import { formatDateDMY } from '../utils/date'

const { state, ensureInitialized, updateGlobalSettings, refreshAll } = usePlatformStore()
const { t } = useI18n()
const { message, messageClass, notify, fail, report, clearMessage } = usePageMessage()
const exporting = ref(false)

const IMPORT_CONFIRMATION = 'REPLACE ALL DATA'

interface ImportTablePlan {
  name: string
  current_rows: number
  incoming_rows: number
}

interface ImportResult {
  imported: boolean
  can_import: boolean
  format_version: string | null
  archive_schema_revision: string | null
  database_schema_revision: string | null
  archive_generated_at: string | null
  total_current_rows: number
  total_incoming_rows: number
  tables: ImportTablePlan[]
  errors: string[]
  warnings: string[]
}

const selectedFile = ref<File | null>(null)
const analysis = ref<ImportResult | null>(null)
const analyzing = ref(false)
const importing = ref(false)
const confirmation = ref('')

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
  interestGenerationLeadDays: 10,
  defaultGraceDays: 0
})

onMounted(async () => {
  await ensureInitialized()
  if (state.globalSettings) {
    form.companyName = state.globalSettings.companyName || ''
    form.companyDocumentType = state.globalSettings.companyDocumentType || 'NIT'
    form.companyDocumentNumber = state.globalSettings.companyDocumentNumber || ''
    form.companyAddress = state.globalSettings.companyAddress || ''
    form.companyPhone = state.globalSettings.companyPhone || ''
    form.companyEmail = state.globalSettings.companyEmail || ''
    /* Keep the initialised default when the server did not send a value. The fields beside
       these already did (`|| ''`); these six wrote `undefined` straight through, which blanks
       the dropdown — CustomSelect finds no matching option and falls back to its placeholder
       — and then sends `undefined` back on the next save. Vue was warning about it on every
       mount and nobody was reading the console. */
    form.currencyCode = state.globalSettings.currencyCode ?? form.currencyCode
    form.timezone = state.globalSettings.timezone ?? form.timezone
    form.dateFormat = state.globalSettings.dateFormat ?? form.dateFormat
    form.defaultLatePenaltyRate = state.globalSettings.defaultLatePenaltyRate ?? form.defaultLatePenaltyRate
    form.interestGenerationLeadDays =
      state.globalSettings.interestGenerationLeadDays ?? form.interestGenerationLeadDays
    form.defaultGraceDays = state.globalSettings.defaultGraceDays ?? form.defaultGraceDays
  }
})

const handleSaveSettings = async () => {
  try {
    const result = await updateGlobalSettings({ ...form })
    report(result, t)
  } catch {
    fail(t('messages.operationFailed'))
  }
}

const handleExportData = async () => {
  exporting.value = true
  clearMessage()
  try {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '-')
    const { blob, filename } = await apiClient.requestFile('/backup/export', `export-${timestamp}.zip`)

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)

    notify(t('messages.dataExported'))
  } catch {
    fail(t('messages.operationFailed'))
  } finally {
    exporting.value = false
  }
}

const handleFileSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null

  selectedFile.value = file
  analysis.value = null
  confirmation.value = ''
  clearMessage()

  if (!file) {
    return
  }

  analyzing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('validate_only', 'true')
    analysis.value = await apiClient.requestUpload<ImportResult>('/backup/import', formData)
  } catch (error) {
    fail(error instanceof Error && error.message ? error.message : t('messages.operationFailed'))
  } finally {
    analyzing.value = false
  }
}

const handleImportData = async () => {
  if (!selectedFile.value || confirmation.value !== IMPORT_CONFIRMATION) {
    return
  }

  importing.value = true
  clearMessage()
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('confirmation', confirmation.value)
    formData.append('validate_only', 'false')

    const result = await apiClient.requestUpload<ImportResult>('/backup/import', formData)
    analysis.value = result
    confirmation.value = ''
    notify(t('messages.dataImported', { rows: result.total_incoming_rows }))

    // Everything in memory belongs to the replaced dataset.
    await refreshAll()
  } catch (error) {
    fail(error instanceof Error && error.message ? error.message : t('messages.operationFailed'))
  } finally {
    importing.value = false
  }
}

/* Fills three fields; it does not save. That was invisible before — the button sat at the
   top of the page and changed values far below it, so pressing it and leaving looked like
   it had done something and had not. */
const applyColombiaPreset = () => {
  form.currencyCode = 'COP'
  form.timezone = 'America/Bogota'
  form.dateFormat = 'DD/MM/YYYY'
  notify(t('settings.presetApplied'))
}
</script>
