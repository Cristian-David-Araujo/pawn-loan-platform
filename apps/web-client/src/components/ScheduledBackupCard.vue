<template>
  <article class="card mt-16">
    <h3>{{ t('backups.title') }}</h3>
    <p class="muted">{{ t('backups.hint') }}</p>

    <p v-if="message" class="notice mt-16" :class="{ 'notice-error': messageIsError }">{{ message }}</p>

    <!-- The state of the schedule comes first: whether copies are actually being made is the
         question this screen exists to answer, and it must not be below a form. -->
    <div class="backup-status mt-16">
      <span class="pill" :class="statusPillClass">{{ statusLabel }}</span>
      <span v-if="schedule?.enabled && schedule.next_run_at" class="muted">
        {{ t('backups.nextRun') }}: {{ formatDateTime(schedule.next_run_at) }}
      </span>
      <span v-if="lastSuccess" class="muted">
        {{ t('backups.lastCopy') }}: {{ formatDateTime(lastSuccess.started_at) }}
      </span>
      <span v-else class="muted">{{ t('backups.neverRun') }}</span>
    </div>

    <p v-if="lastRunFailed" class="notice notice-error mt-8">
      {{ t('backups.lastAttemptFailed') }}: {{ schedule?.last_run?.error }}
    </p>

    <form class="form mt-16" @submit.prevent="handleSave">
      <div class="form-section">
        <div class="form-section-head">
          <h4 class="form-section-title">{{ t('backups.scheduleTitle') }}</h4>
          <p class="muted">{{ t('backups.scheduleHint') }}</p>
        </div>

        <label class="checkbox-row">
          <input v-model="form.enabled" type="checkbox" />
          <span>{{ t('backups.enabled') }}</span>
        </label>

        <div class="grid grid-2">
          <label>
            <span class="field-label-row">{{ t('backups.frequency') }}</span>
            <CustomSelect v-model="form.frequency" :options="frequencyOptions" />
          </label>
          <label>
            <span class="field-label-row">{{ t('backups.hour') }}</span>
            <CustomSelect v-model="form.hour" :options="hourOptions" />
          </label>
          <label v-if="form.frequency === 'weekly'">
            <span class="field-label-row">{{ t('backups.dayOfWeek') }}</span>
            <CustomSelect v-model="form.dayOfWeek" :options="weekdayOptions" />
          </label>
          <label v-if="form.frequency === 'monthly'" :title="t('backups.dayOfMonthHelp')">
            <span class="field-label-row">
              {{ t('backups.dayOfMonth') }}
              <span class="field-help" aria-hidden="true">ⓘ</span>
            </span>
            <CustomSelect v-model="form.dayOfMonth" :options="monthDayOptions" />
          </label>
          <label :title="t('backups.retentionHelp')">
            <span class="field-label-row">
              {{ t('backups.retention') }}
              <span class="field-help" aria-hidden="true">ⓘ</span>
            </span>
            <input v-model.number="form.retentionCopies" type="number" min="0" max="365" step="1" />
          </label>
        </div>
      </div>

      <div class="form-section">
        <div class="form-section-head">
          <h4 class="form-section-title">{{ t('backups.destinationTitle') }}</h4>
          <p class="muted">{{ t('backups.destinationHint') }}</p>
        </div>

        <div class="grid grid-2">
          <label>
            <span class="field-label-row">{{ t('backups.destination') }}</span>
            <CustomSelect v-model="form.destination" :options="destinationOptions" />
          </label>
          <label v-if="form.destination === 'local_directory'" :title="t('backups.localDirectoryHelp')">
            <span class="field-label-row">
              {{ t('backups.localDirectory') }}
              <span class="field-help" aria-hidden="true">ⓘ</span>
            </span>
            <!-- Empty means "follow the deployment default", so the effective path is the
                 placeholder rather than the value: filling it in would silently pin it. -->
            <input v-model="form.localDirectory" :placeholder="schedule?.local_directory_effective" />
          </label>
        </div>

        <template v-if="form.destination === 'google_drive'">
          <p class="muted">{{ t('backups.driveScopeNote') }}</p>

          <template v-if="schedule?.drive_connected">
            <p class="form-static-value">
              {{ t('backups.driveConnectedAs', { account: schedule.drive_account_email ?? t('backups.driveUnknownAccount') }) }}
            </p>
            <p class="muted">{{ t('backups.driveFolder') }}: {{ schedule.drive_folder_name }}</p>
            <div class="quick-actions">
              <button class="btn btn-secondary" type="button" :disabled="busy" @click="handleDisconnect">
                <Unlink :size="16" />
                {{ t('backups.driveDisconnect') }}
              </button>
            </div>
          </template>

          <template v-else>
            <p class="notice notice-warning">{{ t('backups.driveNotConnected') }}</p>
            <ol class="backup-steps muted">
              <li>{{ t('backups.driveStepProject') }}</li>
              <li>{{ t('backups.driveStepPublish') }}</li>
              <li>{{ t('backups.driveStepRedirect') }}</li>
            </ol>

            <label>
              <span class="field-label-row">{{ t('backups.driveRedirectUri') }}</span>
              <p class="form-static-value">{{ redirectUri }}</p>
            </label>

            <div class="grid grid-2">
              <label>
                <span class="field-label-row">{{ t('backups.driveClientId') }}</span>
                <input v-model="drive.clientId" autocomplete="off" />
              </label>
              <label>
                <span class="field-label-row">{{ t('backups.driveClientSecret') }}</span>
                <PasswordInput v-model="drive.clientSecret" autocomplete="off" />
              </label>
            </div>

            <div class="quick-actions">
              <button
                class="btn btn-secondary"
                type="button"
                :disabled="busy || !drive.clientId.trim() || !drive.clientSecret.trim()"
                @click="handleAuthorize"
              >
                <Link2 :size="16" />
                {{ t('backups.driveConnect') }}
              </button>
            </div>
          </template>
        </template>
      </div>

      <div class="quick-actions">
        <button class="btn" type="submit" :disabled="busy">
          <Save :size="16" />
          {{ t('backups.save') }}
        </button>
        <button class="btn btn-secondary" type="button" :disabled="busy" @click="handleTestDestination">
          <PlugZap :size="16" />
          {{ t('backups.testDestination') }}
        </button>
        <button class="btn btn-secondary" type="button" :disabled="busy" @click="handleRunNow">
          <DatabaseBackup :size="16" />
          {{ running ? t('backups.runningNow') : t('backups.runNow') }}
        </button>
      </div>
    </form>

    <div class="form-section mt-16">
      <div class="form-section-head">
        <h4 class="form-section-title">{{ t('backups.historyTitle') }}</h4>
        <p class="muted">{{ t('backups.historyHint') }}</p>
      </div>

      <div v-if="runs.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ t('backups.runStarted') }}</th>
              <th>{{ t('backups.runStatus') }}</th>
              <th>{{ t('backups.runTrigger') }}</th>
              <th>{{ t('backups.runDestination') }}</th>
              <th class="text-right">{{ t('backups.runSize') }}</th>
              <th>{{ t('backups.runDetail') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in runs" :key="run.id">
              <td>{{ formatDateTime(run.started_at) }}</td>
              <td>
                <span class="pill" :class="run.status === 'success' ? 'pill-current' : 'pill-overdue'">
                  {{ t(`backups.status.${run.status}`) }}
                </span>
              </td>
              <td>{{ t(`backups.trigger.${run.trigger}`) }}</td>
              <td>{{ t(`backups.destinations.${run.destination}`) }}</td>
              <td class="text-right">{{ formatSize(run.size_bytes) }}</td>
              <td class="run-detail">{{ run.error || run.filename || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="empty-state">
        <p>{{ t('backups.historyEmpty') }}</p>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { DatabaseBackup, Link2, PlugZap, Save, Unlink } from 'lucide-vue-next'
import CustomSelect from './CustomSelect.vue'
import PasswordInput from './PasswordInput.vue'
import { apiClient, apiErrorMessage } from '../services/api'
import { formatDateTime } from '../utils/date'

interface BackupRun {
  id: number
  started_at: string
  finished_at: string | null
  status: string
  trigger: string
  destination: string
  filename: string | null
  size_bytes: number | null
  total_rows: number | null
  location: string | null
  error: string | null
  triggered_by: string | null
}

interface BackupSchedule {
  enabled: boolean
  frequency: string
  hour: number
  day_of_week: number
  day_of_month: number
  destination: string
  local_directory: string
  local_directory_effective: string
  retention_copies: number
  drive_connected: boolean
  drive_account_email: string | null
  drive_folder_name: string
  drive_folder_id: string | null
  next_run_at: string | null
  last_run: BackupRun | null
  last_successful_run: BackupRun | null
}

// The consent flow leaves and comes back through the browser, so the value that proves the
// returning code is the one we asked for cannot live in this component's state.
const OAUTH_STATE_KEY = 'backup-drive-oauth-state'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const schedule = ref<BackupSchedule | null>(null)
const runs = ref<BackupRun[]>([])
const message = ref('')
const messageIsError = ref(false)
const busy = ref(false)
const running = ref(false)

const form = reactive({
  enabled: false,
  frequency: 'daily',
  hour: 2,
  dayOfWeek: 1,
  dayOfMonth: 1,
  destination: 'local_directory',
  localDirectory: '',
  retentionCopies: 7
})

const drive = reactive({ clientId: '', clientSecret: '' })

const redirectUri = computed(() => `${window.location.origin}/settings`)

const frequencyOptions = computed(() =>
  ['daily', 'weekly', 'monthly'].map((value) => ({ value, label: t(`backups.frequencies.${value}`) }))
)

const destinationOptions = computed(() =>
  ['local_directory', 'google_drive'].map((value) => ({ value, label: t(`backups.destinations.${value}`) }))
)

const hourOptions = Array.from({ length: 24 }, (_, hour) => ({
  value: hour,
  label: `${String(hour).padStart(2, '0')}:00`
}))

const weekdayOptions = computed(() =>
  [1, 2, 3, 4, 5, 6, 7].map((value) => ({ value, label: t(`backups.weekdays.${value}`) }))
)

// Capped at 28 like the API: "the 31st" would skip February without saying so.
const monthDayOptions = Array.from({ length: 28 }, (_, index) => ({ value: index + 1, label: String(index + 1) }))

const lastSuccess = computed(() => schedule.value?.last_successful_run ?? null)

const lastRunFailed = computed(() => schedule.value?.last_run?.status === 'failed')

const statusLabel = computed(() => {
  if (!schedule.value?.enabled) {
    return t('backups.statusOff')
  }
  return lastRunFailed.value ? t('backups.statusFailing') : t('backups.statusOn')
})

const statusPillClass = computed(() => {
  if (!schedule.value?.enabled) {
    return ''
  }
  return lastRunFailed.value ? 'pill-overdue' : 'pill-current'
})

const formatSize = (bytes: number | null) => {
  if (bytes === null || bytes === undefined) {
    return '-'
  }
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const applySchedule = (loaded: BackupSchedule) => {
  schedule.value = loaded
  form.enabled = loaded.enabled
  form.frequency = loaded.frequency
  form.hour = loaded.hour
  form.dayOfWeek = loaded.day_of_week
  form.dayOfMonth = loaded.day_of_month
  form.destination = loaded.destination
  form.localDirectory = loaded.local_directory
  form.retentionCopies = loaded.retention_copies
}

const report = (text: string, isError = false) => {
  message.value = text
  messageIsError.value = isError
}

const loadRuns = async () => {
  runs.value = await apiClient.request<BackupRun[]>('/backup/runs')
}

const load = async () => {
  applySchedule(await apiClient.request<BackupSchedule>('/backup/schedule'))
  await loadRuns()
}

const handleSave = async () => {
  busy.value = true
  report('')
  try {
    const saved = await apiClient.request<BackupSchedule>('/backup/schedule', {
      method: 'PUT',
      body: JSON.stringify({
        enabled: form.enabled,
        frequency: form.frequency,
        hour: form.hour,
        day_of_week: form.dayOfWeek,
        day_of_month: form.dayOfMonth,
        destination: form.destination,
        local_directory: form.localDirectory || null,
        retention_copies: form.retentionCopies,
        drive_folder_name: schedule.value?.drive_folder_name ?? null
      })
    })
    applySchedule(saved)
    report(t('backups.saved'))
  } catch (error) {
    report(apiErrorMessage(error), true)
  } finally {
    busy.value = false
  }
}

const handleRunNow = async () => {
  busy.value = true
  running.value = true
  report('')
  try {
    const run = await apiClient.request<BackupRun>('/backup/schedule/run-now', { method: 'POST' })
    // A failed attempt comes back as a run, not as an error: it is reported here the same way
    // the schedule reports it, rather than as a generic "operation failed".
    if (run.status === 'success') {
      report(t('backups.runFinished', { size: formatSize(run.size_bytes) }))
    } else {
      report(`${t('backups.runFailed')}: ${run.error ?? ''}`, true)
    }
    await load()
  } catch (error) {
    report(apiErrorMessage(error), true)
  } finally {
    busy.value = false
    running.value = false
  }
}

const handleTestDestination = async () => {
  busy.value = true
  report('')
  try {
    const result = await apiClient.request<{ ok: boolean; detail: string }>('/backup/destination/test', {
      method: 'POST'
    })
    report(
      result.ok ? t('backups.testOk', { detail: result.detail }) : `${t('backups.testFailed')}: ${result.detail}`,
      !result.ok
    )
  } catch (error) {
    report(apiErrorMessage(error), true)
  } finally {
    busy.value = false
  }
}

const handleAuthorize = async () => {
  busy.value = true
  report('')
  try {
    const started = await apiClient.request<{ authorization_url: string; state: string }>(
      '/backup/drive/authorize',
      {
        method: 'POST',
        body: JSON.stringify({
          client_id: drive.clientId.trim(),
          client_secret: drive.clientSecret.trim(),
          redirect_uri: redirectUri.value
        })
      }
    )

    sessionStorage.setItem(OAUTH_STATE_KEY, started.state)
    window.location.assign(started.authorization_url)
  } catch (error) {
    report(apiErrorMessage(error), true)
    busy.value = false
  }
}

const handleDisconnect = async () => {
  busy.value = true
  report('')
  try {
    applySchedule(await apiClient.request<BackupSchedule>('/backup/drive/disconnect', { method: 'POST' }))
    report(t('backups.driveDisconnected'))
  } catch (error) {
    report(apiErrorMessage(error), true)
  } finally {
    busy.value = false
  }
}

/**
 * Finish the consent flow when Google sends the browser back to `/settings?code=...`.
 *
 * The `state` is compared against what was stored before leaving. Without that check a link
 * crafted with somebody else's `code` would connect this installation to their Drive, and
 * every backup from then on would be uploaded to a stranger's account.
 */
const completeDriveAuthorization = async () => {
  const code = typeof route.query.code === 'string' ? route.query.code : ''
  const state = typeof route.query.state === 'string' ? route.query.state : ''
  const expected = sessionStorage.getItem(OAUTH_STATE_KEY)
  const deniedByUser = typeof route.query.error === 'string' ? route.query.error : ''

  if (!code && !deniedByUser) {
    return
  }

  sessionStorage.removeItem(OAUTH_STATE_KEY)
  // The code is single use and already spent; leaving it in the URL would retry on reload.
  await router.replace({ path: '/settings' })

  if (deniedByUser) {
    report(t('backups.driveAuthorizationCancelled'), true)
    return
  }

  if (!expected || state !== expected) {
    report(t('backups.driveStateMismatch'), true)
    return
  }

  busy.value = true
  try {
    applySchedule(
      await apiClient.request<BackupSchedule>('/backup/drive/connect', {
        method: 'POST',
        body: JSON.stringify({ code, redirect_uri: redirectUri.value, state })
      })
    )
    form.destination = 'google_drive'
    report(t('backups.driveConnected', { account: schedule.value?.drive_account_email ?? '' }))
  } catch (error) {
    report(apiErrorMessage(error), true)
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    await load()
    await completeDriveAuthorization()
  } catch (error) {
    report(apiErrorMessage(error), true)
  }
})
</script>

<style scoped>
.backup-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.backup-steps {
  margin: 0;
  padding-left: 1.2rem;
  display: grid;
  gap: 0.3rem;
  font-size: 0.85rem;
}

/* An error message can be a full sentence from Google; it wraps rather than stretching the
   table past the viewport. */
.run-detail {
  max-width: 22rem;
  word-break: break-word;
}
</style>
