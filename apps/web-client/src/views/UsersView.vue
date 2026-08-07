<template>
  <section>
    <PageHeader :title="t('users.title', 'User Management')" :subtitle="t('users.subtitle', 'Manage system users and access roles')">
      <template #icon>
        <Shield :size="18" />
      </template>
      <template #actions>
        <button class="btn" type="button" @click="openCreateModal">
          <UserPlus :size="16" />
          {{ t('users.createUser', 'Create User') }}
        </button>
      </template>
    </PageHeader>

    <p v-if="message" :class="[messageClass, 'mt-16']">{{ message }}</p>

    <div class="card mt-16">
      <!-- Skeleton in the shape of the table, then a real empty state. Both used to be a
           single bare cell under six headings. -->
      <div v-if="loading" class="table-wrap" role="status" :aria-label="t('common.loading')">
        <div v-for="row in 4" :key="row" class="skeleton-row">
          <span class="skeleton" v-for="cell in 5" :key="cell"></span>
        </div>
      </div>
      <div v-else-if="!users.length" class="empty-state">
        <div class="empty-state-icon"><Shield :size="22" /></div>
        <p class="empty-state-title">{{ t('users.noUsers') }}</p>
        <p class="empty-state-hint">{{ t('users.noUsersHint') }}</p>
        <button class="btn" type="button" @click="openCreateModal">
          <UserPlus :size="16" />
          {{ t('users.createUser') }}
        </button>
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ t('common.id', 'ID') }}</th>
              <th>{{ t('users.username', 'Username') }}</th>
              <th>{{ t('users.fullName', 'Full Name') }}</th>
              <th>{{ t('users.role', 'Role') }}</th>
              <th>{{ t('common.status', 'Status') }}</th>
              <th>{{ t('common.actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td :data-label="t('common.id', 'ID')">{{ user.id }}</td>
              <td :data-label="t('users.username', 'Username')">{{ user.username }}</td>
              <td :data-label="t('users.fullName', 'Full Name')">{{ user.full_name || user.email }}</td>
              <td :data-label="t('users.role', 'Role')">{{ t('roles.' + user.role, user.role) }}</td>
              <td :data-label="t('common.status', 'Status')">
                <span class="pill" :class="user.is_active ? 'pill-current' : 'pill-overdue'">
                  {{ user.is_active ? t('common.active', 'Active') : t('users.inactive', 'Inactive') }}
                </span>
              </td>
              <td>
                <div class="form-inline">
                  <button class="btn btn-secondary btn-icon" type="button" @click="openEditModal(user)">
                    <Pencil :size="16" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showModal" class="modal-backdrop" @click.self="closeModal">
      <div class="modal-panel card">
        <div class="modal-header">
          <h3>{{ editingUser ? t('users.editUser', 'Edit User') : t('users.createUser', 'Create User') }}</h3>
          <button class="btn btn-secondary btn-icon" type="button" @click="closeModal">
            <X :size="16" />
          </button>
        </div>

        <form class="form mt-16" @submit.prevent="handleSubmit">
          
          <label>
            {{ t('users.fullName', 'Full Name') }}
            <input v-model="form.full_name" />
          </label>
          <div class="form-row">
            <label>
              {{ t('users.email', 'Email') }}
              <input type="email" v-model="form.email" />
            </label>
            <label>
              {{ t('users.phone', 'Phone') }}
              <input v-model="form.phone" />
            </label>
          </div>
          <div class="form-row">
            <label>
              {{ t('users.documentNumber', 'Document Number') }}
              <input v-model="form.document_number" />
            </label>
            <label>
              {{ t('users.address', 'Address') }}
              <input v-model="form.address" />
            </label>
          </div>

          <label>
            {{ t('users.username', 'Username') }}
            <input v-model="form.username" required />
          </label>
          <label v-if="!editingUser">
            {{ t('users.password', 'Password') }}
            <PasswordInput v-model="form.password" required />
          </label>
          <label v-if="editingUser">
            {{ t('users.newPassword', 'New Password (Optional)') }}
            <PasswordInput v-model="form.password" :placeholder="t('users.leaveBlankToKeep', 'Leave blank to keep current')" />
          </label>
          <label>
            {{ t('users.role', 'Role') }}
            <CustomSelect v-model="form.role" :options="roleOptions" />
          </label>
          <label v-if="editingUser" class="checkbox-row mt-16">
            <input type="checkbox" v-model="form.is_active" />
            {{ t('users.isActive', 'User is active') }}
          </label>

          <button class="btn mt-16" type="submit" :disabled="isSaving">
            <Save :size="16" />
            {{ t('common.save', 'Save') }}
          </button>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Shield, UserPlus, Pencil, Save, X } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import CustomSelect from '../components/CustomSelect.vue'
import PasswordInput from '../components/PasswordInput.vue'
import { usePageMessage } from '../composables/usePageMessage'
import { apiClient } from '../services/api'
import { type UserProfile, UserRole } from '../modules/authentication/authState'

const { t } = useI18n()

const users = ref<UserProfile[]>([])
const loading = ref(false)
const showModal = ref(false)
const editingUser = ref<UserProfile | null>(null)
const isSaving = ref(false)

/* This view imported usePageMessage but never called it, keeping a local `message` ref and
   a second `error` ref alongside it. So `messageClass` was undefined in the template and the
   banner rendered with no class at all — not even `.notice` — while failures went to a
   separate paragraph below. One banner, one tone, and the tone cannot be forgotten. */
const { message, messageClass, notify, fail, clearMessage } = usePageMessage()

const form = ref({
  username: '',
  password: '',
  full_name: '',
  email: '',
  phone: '',
  document_number: '',
  address: '',
  role: UserRole.LoanOfficer,
  is_active: true
})

const roleOptions = [
  { value: UserRole.Administrator, label: t('roles.administrator', 'Administrator') },
  { value: UserRole.LoanOfficer, label: t('roles.loan_officer', 'Loan Officer') },
  { value: UserRole.Collector, label: t('roles.collector', 'Collector') }
]

const fetchUsers = async () => {
  loading.value = true
  try {
    const data = await apiClient.request<UserProfile[]>('/users')
    users.value = data
  } catch (err: any) {
    // Was the literal 'Failed to load users' — English, whatever the operator's locale.
    fail(err.message || t('users.loadFailed'))
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  editingUser.value = null
  form.value = {
    username: '',
    password: '',
    full_name: '',
    email: '',
    phone: '',
    document_number: '',
    address: '',
    role: UserRole.LoanOfficer,
    is_active: true
  }
  showModal.value = true
}

const openEditModal = (user: UserProfile) => {
  editingUser.value = user
  form.value = {
    username: user.username,
    password: '',
    full_name: user.full_name,
    email: user.email,
    phone: user.phone,
    document_number: user.document_number,
    address: user.address,
    role: user.role,
    is_active: user.is_active
  }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}

const handleSubmit = async () => {
  isSaving.value = true
  clearMessage()

  try {
    if (editingUser.value) {
      const payload: any = {
        username: form.value.username,
        full_name: form.value.full_name,
        email: form.value.email,
        phone: form.value.phone,
        document_number: form.value.document_number,
        address: form.value.address,
        role: form.value.role,
        is_active: form.value.is_active
      }
      if (form.value.password) {
        payload.password = form.value.password
      }
      await apiClient.request(`/users/${editingUser.value.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      })
      notify(t('users.updatedSuccess'))
    } else {
      await apiClient.request('/users', {
        method: 'POST',
        body: JSON.stringify({
          username: form.value.username,
          password: form.value.password,
          full_name: form.value.full_name,
          email: form.value.email,
          phone: form.value.phone,
          document_number: form.value.document_number,
          address: form.value.address,
          role: form.value.role
        })
      })
      notify(t('users.createdSuccess'))
    }
    closeModal()
    await fetchUsers()
  } catch (err: any) {
    fail(err.message || t('users.actionFailed'))
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
