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

    <p v-if="message" class="notice mt-16">{{ message }}</p>
    <p v-if="error" class="notice notice-error mt-16">{{ error }}</p>

    <div class="card mt-16">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ t('common.id', 'ID') }}</th>
              <th>{{ t('users.username', 'Username') }}</th>
              <th>{{ t('users.role', 'Role') }}</th>
              <th>{{ t('common.status', 'Status') }}</th>
              <th>{{ t('common.actions', 'Actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.id }}</td>
              <td>{{ user.username }}</td>
              <td>{{ t('roles.' + user.role, user.role) }}</td>
              <td>
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
            <tr v-if="!users.length && !loading">
              <td colspan="5">{{ t('users.noUsers', 'No users found.') }}</td>
            </tr>
            <tr v-if="loading">
              <td colspan="5">{{ t('common.loading', 'Loading...') }}</td>
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
            {{ t('users.username', 'Username') }}
            <input v-model="form.username" required :disabled="!!editingUser" />
          </label>
          <label v-if="!editingUser">
            {{ t('users.password', 'Password') }}
            <input type="password" v-model="form.password" required />
          </label>
          <label v-if="editingUser">
            {{ t('users.newPassword', 'New Password (Optional)') }}
            <input type="password" v-model="form.password" :placeholder="t('users.leaveBlankToKeep', 'Leave blank to keep current')" />
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
import { apiClient } from '../services/api'
import { type UserProfile } from '../modules/authentication/authState'

const { t } = useI18n()

const users = ref<UserProfile[]>([])
const loading = ref(false)
const showModal = ref(false)
const editingUser = ref<UserProfile | null>(null)
const isSaving = ref(false)
const message = ref('')
const error = ref('')

const form = ref({
  username: '',
  password: '',
  role: 'loan_officer',
  is_active: true
})

const roleOptions = [
  { value: 'administrator', label: t('roles.administrator', 'Administrator') },
  { value: 'loan_officer', label: t('roles.loan_officer', 'Loan Officer') },
  { value: 'collector', label: t('roles.collector', 'Collector') }
]

const fetchUsers = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await apiClient.request<UserProfile[]>('/users')
    users.value = data
  } catch (err: any) {
    error.value = err.message || 'Failed to load users'
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  editingUser.value = null
  form.value = {
    username: '',
    password: '',
    role: 'loan_officer',
    is_active: true
  }
  showModal.value = true
}

const openEditModal = (user: UserProfile) => {
  editingUser.value = user
  form.value = {
    username: user.username,
    password: '',
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
  message.value = ''
  error.value = ''

  try {
    if (editingUser.value) {
      const payload: any = {
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
      message.value = t('users.updatedSuccess', 'User updated successfully')
    } else {
      await apiClient.request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          username: form.value.username,
          password: form.value.password,
          role: form.value.role
        })
      })
      message.value = t('users.createdSuccess', 'User created successfully')
    }
    closeModal()
    await fetchUsers()
  } catch (err: any) {
    error.value = err.message || 'Action failed'
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
