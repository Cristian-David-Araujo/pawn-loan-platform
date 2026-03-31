<template>
  <section>
    <h2>{{ t('customers.title') }}</h2>
    <p class="muted">{{ t('customers.subtitle') }}</p>

    <form class="card form mt-16" @submit.prevent="handleCreateCustomer">
      <div class="grid grid-3">
        <label>
          {{ t('customers.fullName') }}
          <input v-model="form.fullName" required />
        </label>
        <label>
          {{ t('customers.documentType') }}
          <input v-model="form.documentType" required />
        </label>
        <label>
          {{ t('customers.documentNumber') }}
          <input v-model="form.documentNumber" required />
        </label>
        <label>
          {{ t('common.phone') }}
          <input v-model="form.phone" required />
        </label>
        <label>
          {{ t('common.city') }}
          <input v-model="form.city" required />
        </label>
      </div>
      <button class="btn" type="submit">{{ t('customers.createCustomer') }}</button>
      <p v-if="message" class="notice">{{ message }}</p>
    </form>

    <div class="card mt-16">
      <div class="table-toolbar">
        <input v-model="search" class="table-search" type="text" :placeholder="t('customers.searchPlaceholder')" />
        <span class="muted">{{ t('customers.clickCustomerHint') }}</span>
        <span class="table-count">{{ t('customers.totalRecords', { count: filteredCustomers.length }) }}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>{{ t('common.id') }}</th>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('customers.document') }}</th>
            <th>{{ t('common.phone') }}</th>
            <th>{{ t('common.city') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="customer in filteredCustomers"
            :key="customer.id"
            class="clickable-row"
            :class="{ 'selected-row': customer.id === selectedCustomerId }"
            @click="selectCustomer(customer.id)"
          >
            <td>{{ customer.id }}</td>
            <td>{{ customer.fullName }}</td>
            <td>{{ customer.documentType }} / {{ customer.documentNumber }}</td>
            <td>{{ customer.phone }}</td>
            <td>{{ customer.city }}</td>
            <td>{{ customer.status === 'active' ? t('common.active') : customer.status }}</td>
            <td>
              <button class="btn btn-secondary" type="button" @click.stop="selectCustomer(customer.id)">
                {{ t('customers.editCustomer') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card mt-16">
      <h3>{{ t('customers.customerDetail') }}</h3>
      <p v-if="selectedCustomer" class="muted">{{ t('customers.selectedCustomer', { id: selectedCustomer.id }) }}</p>
      <p v-else class="muted">{{ t('customers.noCustomerSelected') }}</p>

      <form v-if="selectedCustomer" class="form mt-16" @submit.prevent="handleUpdateCustomer">
        <div class="grid grid-3">
          <label>
            {{ t('customers.fullName') }}
            <input v-model="editForm.fullName" required />
          </label>
          <label>
            {{ t('customers.document') }}
            <input :value="`${selectedCustomer.documentType} / ${selectedCustomer.documentNumber}`" disabled />
          </label>
          <label>
            {{ t('common.status') }}
            <select v-model="editForm.status" required>
              <option value="active">{{ t('common.active') }}</option>
              <option value="archived">archived</option>
            </select>
          </label>
          <label>
            {{ t('common.phone') }}
            <input v-model="editForm.phone" required />
          </label>
          <label>
            {{ t('customers.email') }}
            <input v-model="editForm.email" type="email" />
          </label>
          <label>
            {{ t('customers.address') }}
            <input v-model="editForm.address" />
          </label>
          <label>
            {{ t('common.city') }}
            <input v-model="editForm.city" required />
          </label>
        </div>
        <button class="btn" type="submit">{{ t('customers.saveChanges') }}</button>
      </form>

      <div v-if="selectedCustomer" class="mt-16">
        <h3>{{ t('customers.customerLoans') }}</h3>
        <p class="muted" v-if="!selectedCustomerLoans.length">{{ t('customers.noLoans') }}</p>
        <table v-else>
          <thead>
            <tr>
              <th>{{ t('common.id') }}</th>
              <th>{{ t('common.type') }}</th>
              <th>{{ t('common.principal') }}</th>
              <th>{{ t('loans.outstanding') }}</th>
              <th>{{ t('loans.rate') }}</th>
              <th>{{ t('common.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="loan in selectedCustomerLoans" :key="loan.id">
              <td>#{{ loan.id }}</td>
              <td>{{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</td>
              <td>{{ formatCurrency(loan.principalAmount) }}</td>
              <td>{{ formatCurrency(loan.outstandingPrincipal) }}</td>
              <td>{{ loan.monthlyInterestRate }}%</td>
              <td>{{ t(`common.${loan.status}`) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="selectedCustomer" class="mt-16">
        <h3>{{ t('customers.customerPayments') }}</h3>
        <p class="muted">{{ t('customers.totalPaid', { amount: formatCurrency(totalCustomerPaid) }) }}</p>
        <p class="muted" v-if="!selectedCustomerPayments.length">{{ t('customers.noPayments') }}</p>
        <table v-else>
          <thead>
            <tr>
              <th>{{ t('common.id') }}</th>
              <th>{{ t('common.loan') }}</th>
              <th>{{ t('common.date') }}</th>
              <th>{{ t('common.total') }}</th>
              <th>{{ t('payments.penalty') }}</th>
              <th>{{ t('common.interest') }}</th>
              <th>{{ t('common.fees') }}</th>
              <th>{{ t('common.principal') }}</th>
              <th>{{ t('common.method') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="payment in selectedCustomerPayments" :key="payment.id">
              <td>#{{ payment.id }}</td>
              <td>#{{ payment.loanId }}</td>
              <td>{{ payment.paymentDate }}</td>
              <td>{{ formatCurrency(payment.totalAmount) }}</td>
              <td>{{ formatCurrency(payment.allocatedToPenalty) }}</td>
              <td>{{ formatCurrency(payment.allocatedToInterest) }}</td>
              <td>{{ formatCurrency(payment.allocatedToFees) }}</td>
              <td>{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
              <td>
                {{
                  payment.paymentMethod === 'cash'
                    ? t('common.cash')
                    : payment.paymentMethod === 'bank-transfer'
                      ? t('common.bankTransfer')
                      : t('common.other')
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="selectedCustomer" class="mt-16">
        <h3>{{ t('customers.customerCollateral') }}</h3>
        <p class="muted" v-if="!selectedCustomerCollateral.length">{{ t('customers.noCollateral') }}</p>
        <table v-else>
          <thead>
            <tr>
              <th>{{ t('common.id') }}</th>
              <th>{{ t('common.loan') }}</th>
              <th>{{ t('common.description') }}</th>
              <th>{{ t('collateral.appraisedValue') }}</th>
              <th>{{ t('collateral.custodyCode') }}</th>
              <th>{{ t('common.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in selectedCustomerCollateral" :key="item.id">
              <td>#{{ item.id }}</td>
              <td>#{{ item.loanId }}</td>
              <td>{{ item.description }}</td>
              <td>{{ formatCurrency(item.appraisedValue) }}</td>
              <td>{{ item.custodyCode }}</td>
              <td>{{ item.status === 'in-custody' ? t('common.inCustody') : t(`common.${item.status}`) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMockPlatformStore } from '../stores/mockPlatformStore'

const { state, createCustomer, updateCustomer, getCustomerById, ensureInitialized } = useMockPlatformStore()
const { t, locale } = useI18n()
const message = ref('')
const search = ref('')
const selectedCustomerId = ref<number | null>(null)
const isSaving = ref(false)

onMounted(async () => {
  await ensureInitialized()
})

const form = reactive({
  fullName: '',
  documentType: 'ID',
  documentNumber: '',
  phone: '',
  city: ''
})

const editForm = reactive({
  fullName: '',
  phone: '',
  email: '',
  address: '',
  city: '',
  status: 'active' as 'active' | 'archived'
})

const selectedCustomer = computed(() =>
  selectedCustomerId.value === null ? null : getCustomerById(selectedCustomerId.value)
)

const selectedCustomerLoans = computed(() => {
  if (!selectedCustomer.value) {
    return []
  }
  return state.loans.filter((loan) => loan.customerId === selectedCustomer.value?.id)
})

const selectedCustomerLoanIds = computed(() => new Set(selectedCustomerLoans.value.map((loan) => loan.id)))

const selectedCustomerPayments = computed(() =>
  state.payments.filter((payment) => selectedCustomerLoanIds.value.has(payment.loanId))
)

const selectedCustomerCollateral = computed(() =>
  state.collateralItems.filter((item) => selectedCustomerLoanIds.value.has(item.loanId))
)

const totalCustomerPaid = computed(() =>
  selectedCustomerPayments.value.reduce((sum, payment) => sum + payment.totalAmount, 0)
)

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat(locale.value === 'es' ? 'es-MX' : 'en-US', { style: 'currency', currency: 'USD' }).format(
    amount
  )

const syncEditForm = () => {
  if (!selectedCustomer.value) {
    return
  }

  editForm.fullName = selectedCustomer.value.fullName
  editForm.phone = selectedCustomer.value.phone
  editForm.email = selectedCustomer.value.email
  editForm.address = selectedCustomer.value.address
  editForm.city = selectedCustomer.value.city
  editForm.status = selectedCustomer.value.status
}

const selectCustomer = (customerId: number) => {
  selectedCustomerId.value = customerId
  syncEditForm()
}

const handleCreateCustomer = async () => {
  try {
    const result = await createCustomer({ ...form })
    message.value = t(result.messageKey)

    if (result.ok) {
      form.fullName = ''
      form.documentType = 'ID'
      form.documentNumber = ''
      form.phone = ''
      form.city = ''
    }
  } catch {
    message.value = t('messages.operationFailed')
  }
}

const handleUpdateCustomer = async () => {
  if (!selectedCustomer.value || isSaving.value) {
    return
  }

  isSaving.value = true
  try {
    const result = await updateCustomer({
      id: selectedCustomer.value.id,
      fullName: editForm.fullName,
      phone: editForm.phone,
      email: editForm.email,
      address: editForm.address,
      city: editForm.city,
      status: editForm.status
    })

    message.value = t(result.messageKey)
    if (result.ok) {
      syncEditForm()
    }
  } catch {
    message.value = t('messages.operationFailed')
  } finally {
    isSaving.value = false
  }
}

const filteredCustomers = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) {
    return state.customers
  }

  return state.customers.filter((customer) =>
    [customer.fullName, customer.documentNumber, customer.phone, customer.city].some((value) =>
      value.toLowerCase().includes(query)
    )
  )
})
</script>
