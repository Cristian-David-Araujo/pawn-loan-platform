import { computed, reactive } from 'vue'

import { apiClient } from '../services/api'
import type { CollateralItem, Customer, GlobalSettings, Loan, LoanType, Payment } from '../types/domain'
import { setGlobalDateFormat } from '../utils/date'

interface BackendCustomer {
  id: number
  first_name: string
  last_name: string
  document_type: string
  document_number: string
  phone: string
  email: string
  address: string
  city: string
  status: string
  created_at: string
  updated_at: string
}

interface BackendLoan {
  id: number
  customer_id: number
  loan_type: LoanType
  principal_amount: number
  outstanding_principal: number
  monthly_interest_rate: number
  late_penalty_rate: number
  disbursement_date: string
  due_day: number
  status: Loan['status']
}

interface BackendCollateral {
  id: number
  loan_id: number
  description: string
  appraised_value: number
  custody_code: string
  storage_location: string
  status: 'in_custody' | 'released' | 'liquidated'
}

interface BackendPayment {
  id: number
  loan_id: number
  payment_date: string
  total_amount: number
  allocated_to_penalty: number
  allocated_to_interest: number
  allocated_to_fees: number
  allocated_to_principal: number
  payment_method: Payment['paymentMethod']
}

interface BackendGlobalSettings {
  id: number
  currency_code: string
  timezone: string
  date_format: string
  default_late_penalty_rate: number
}

interface CreateCustomerPayload {
  fullName: string
  documentType: string
  documentNumber: string
  phone: string
  city: string
}

interface UpdateCustomerPayload {
  id: number
  fullName: string
  phone: string
  email: string
  address: string
  city: string
  status: 'active' | 'archived'
}

interface CreateLoanPayload {
  customerId: number
  loanType: LoanType
  principalAmount: number
  monthlyInterestRate: number
  latePenaltyRate: number
  dueDay: number
}

interface CreateCollateralPayload {
  loanId: number
  description: string
  appraisedValue: number
  storageLocation: string
}

interface UpdateLoanPayload {
  id: number
  monthlyInterestRate: number
  dueDay: number
  status: Loan['status']
}

interface UpdateCollateralPayload {
  id: number
  loanId: number
  description: string
  appraisedValue: number
  storageLocation: string
  status: CollateralItem['status']
}

interface CreatePaymentPayload {
  loanId: number
  totalAmount: number
  allocatedToPenalty: number
  allocatedToInterest: number
  allocatedToFees: number
  allocatedToPrincipal: number
  paymentMethod: 'cash' | 'bank-transfer' | 'other'
}

interface UpdateGlobalSettingsPayload {
  currencyCode: string
  timezone: string
  dateFormat: string
  defaultLatePenaltyRate: number
}

const state = reactive({
  customers: [] as Customer[],
  loans: [] as Loan[],
  collateralItems: [] as CollateralItem[],
  payments: [] as Payment[],
  globalSettings: null as GlobalSettings | null,
  initialized: false,
  loading: false,
  loadError: ''
})

const mapCustomer = (item: BackendCustomer): Customer => ({
  id: item.id,
  fullName: `${item.first_name} ${item.last_name}`,
  documentType: item.document_type,
  documentNumber: item.document_number,
  phone: item.phone,
  email: item.email,
  address: item.address,
  city: item.city,
  status: item.status === 'active' ? 'active' : 'archived',
  createdAt: item.created_at,
  updatedAt: item.updated_at
})

const mapLoan = (item: BackendLoan): Loan => ({
  id: item.id,
  customerId: item.customer_id,
  loanType: item.loan_type,
  principalAmount: item.principal_amount,
  outstandingPrincipal: item.outstanding_principal,
  monthlyInterestRate: item.monthly_interest_rate,
  latePenaltyRate: item.late_penalty_rate,
  disbursementDate: item.disbursement_date,
  dueDay: item.due_day,
  status: item.status
})

const mapCollateral = (item: BackendCollateral): CollateralItem => ({
  id: item.id,
  loanId: item.loan_id,
  description: item.description,
  appraisedValue: item.appraised_value,
  custodyCode: item.custody_code,
  storageLocation: item.storage_location,
  status: item.status === 'in_custody' ? 'in-custody' : item.status
})

const mapPayment = (item: BackendPayment): Payment => ({
  id: item.id,
  loanId: item.loan_id,
  paymentDate: item.payment_date,
  totalAmount: item.total_amount,
  allocatedToPenalty: item.allocated_to_penalty,
  allocatedToInterest: item.allocated_to_interest,
  allocatedToFees: item.allocated_to_fees,
  allocatedToPrincipal: item.allocated_to_principal,
  paymentMethod: item.payment_method
})

const mapGlobalSettings = (item: BackendGlobalSettings): GlobalSettings => ({
  id: item.id,
  currencyCode: item.currency_code,
  timezone: item.timezone,
  dateFormat: item.date_format,
  defaultLatePenaltyRate: item.default_late_penalty_rate
})

const splitName = (fullName: string) => {
  const parts = fullName.trim().split(/\s+/)
  if (parts.length <= 1) {
    return { first_name: parts[0] ?? fullName, last_name: '-' }
  }
  return {
    first_name: parts.slice(0, -1).join(' '),
    last_name: parts.at(-1) ?? '-'
  }
}

const refreshAll = async () => {
  state.loading = true
  state.loadError = ''
  try {
    const [customers, loans, collateralItems, payments, globalSettings] = await Promise.all([
      apiClient.request<BackendCustomer[]>('/customers'),
      apiClient.request<BackendLoan[]>('/loans'),
      apiClient.request<BackendCollateral[]>('/collateral-items'),
      apiClient.request<BackendPayment[]>('/payments'),
      apiClient.request<BackendGlobalSettings>('/settings')
    ])

    state.customers = customers.map(mapCustomer)
    state.loans = loans.map(mapLoan)
    state.collateralItems = collateralItems.map(mapCollateral)
    state.payments = payments.map(mapPayment)
    state.globalSettings = mapGlobalSettings(globalSettings)
    setGlobalDateFormat(state.globalSettings.dateFormat)
    state.initialized = true
  } catch (error) {
    state.initialized = false
    state.loadError = error instanceof Error ? error.message : 'Unable to load data'
    throw error
  } finally {
    state.loading = false
  }
}

const ensureInitialized = async () => {
  if (state.initialized || state.loading) {
    return
  }

  const maxAttempts = 60
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      await refreshAll()
      return
    } catch {
      if (attempt === maxAttempts) {
        return
      }
      await new Promise((resolve) => setTimeout(resolve, 2000))
    }
  }
}

const getCustomerName = (customerId: number) => {
  const customer = state.customers.find((item) => item.id === customerId)
  return customer?.fullName ?? '__UNKNOWN_CUSTOMER__'
}

const getCustomerById = (customerId: number) => state.customers.find((item) => item.id === customerId) ?? null

const createCustomer = async (payload: CreateCustomerPayload) => {
  const duplicate = state.customers.some(
    (item) => item.documentType === payload.documentType && item.documentNumber === payload.documentNumber
  )

  if (duplicate) {
    return { ok: false, messageKey: 'messages.customerDocumentExists' }
  }

  const nameParts = splitName(payload.fullName)

  await apiClient.request<BackendCustomer>('/customers', {
    method: 'POST',
    body: JSON.stringify({
      ...nameParts,
      document_type: payload.documentType,
      document_number: payload.documentNumber,
      phone: payload.phone,
      city: payload.city
    })
  })

  await refreshAll()
  return { ok: true, messageKey: 'messages.customerCreated' }
}

const updateCustomer = async (payload: UpdateCustomerPayload) => {
  const current = state.customers.find((item) => item.id === payload.id)
  if (!current) {
    return { ok: false, messageKey: 'messages.customerNotFound' }
  }

  const nameParts = splitName(payload.fullName)

  await apiClient.request<BackendCustomer>(`/customers/${payload.id}`, {
    method: 'PUT',
    body: JSON.stringify({
      ...nameParts,
      phone: payload.phone,
      email: payload.email,
      address: payload.address,
      city: payload.city,
      status: payload.status
    })
  })

  await refreshAll()
  return { ok: true, messageKey: 'messages.customerUpdated' }
}

const createLoan = async (payload: CreateLoanPayload) => {
  await apiClient.request<BackendLoan>('/loans', {
    method: 'POST',
    body: JSON.stringify({
      customer_id: payload.customerId,
      loan_type: payload.loanType,
      principal_amount: payload.principalAmount,
      monthly_interest_rate: payload.monthlyInterestRate,
      late_penalty_rate: payload.latePenaltyRate,
      disbursement_date: new Date().toISOString().slice(0, 10),
      due_day: payload.dueDay
    })
  })

  await refreshAll()
}

const createCollateral = async (payload: CreateCollateralPayload) => {
  await apiClient.request<BackendCollateral>('/collateral-items', {
    method: 'POST',
    body: JSON.stringify({
      loan_id: payload.loanId,
      description: payload.description,
      appraised_value: payload.appraisedValue,
      storage_location: payload.storageLocation
    })
  })

  await refreshAll()
}

const createPayment = async (payload: CreatePaymentPayload) => {
  const allocationSum =
    payload.allocatedToPenalty +
    payload.allocatedToInterest +
    payload.allocatedToFees +
    payload.allocatedToPrincipal

  if (Math.round(allocationSum * 100) !== Math.round(payload.totalAmount * 100)) {
    return { ok: false, messageKey: 'messages.allocationMustEqualTotal' }
  }

  await apiClient.request<BackendPayment>('/payments', {
    method: 'POST',
    body: JSON.stringify({
      loan_id: payload.loanId,
      payment_date: new Date().toISOString().slice(0, 10),
      total_amount: payload.totalAmount,
      allocated_to_penalty: payload.allocatedToPenalty,
      allocated_to_interest: payload.allocatedToInterest,
      allocated_to_fees: payload.allocatedToFees,
      allocated_to_principal: payload.allocatedToPrincipal,
      payment_method: payload.paymentMethod
    })
  })

  await refreshAll()
  return { ok: true, messageKey: 'messages.paymentRegistered' }
}

const updateGlobalSettings = async (payload: UpdateGlobalSettingsPayload) => {
  await apiClient.request<BackendGlobalSettings>('/settings', {
    method: 'PUT',
    body: JSON.stringify({
      currency_code: payload.currencyCode,
      timezone: payload.timezone,
      date_format: payload.dateFormat,
      default_late_penalty_rate: payload.defaultLatePenaltyRate
    })
  })

  setGlobalDateFormat(payload.dateFormat)
  await refreshAll()
  return { ok: true, messageKey: 'messages.settingsUpdated' }
}

const updateLoan = async (payload: UpdateLoanPayload) => {
  await apiClient.request<BackendLoan>(`/loans/${payload.id}`, {
    method: 'PUT',
    body: JSON.stringify({
      monthly_interest_rate: payload.monthlyInterestRate,
      due_day: payload.dueDay,
      status: payload.status
    })
  })

  await refreshAll()
  return { ok: true, messageKey: 'messages.loanUpdated' }
}

const updateCollateral = async (payload: UpdateCollateralPayload) => {
  await apiClient.request<BackendCollateral>(`/collateral-items/${payload.id}`, {
    method: 'PUT',
    body: JSON.stringify({
      loan_id: payload.loanId,
      description: payload.description,
      appraised_value: payload.appraisedValue,
      storage_location: payload.storageLocation,
      status: payload.status === 'in-custody' ? 'in_custody' : payload.status
    })
  })

  await refreshAll()
  return { ok: true, messageKey: 'messages.collateralUpdated' }
}

const dashboardStats = computed(() => {
  const activeLoans = state.loans.filter((item) => item.status === 'active').length
  const overdueLoans = state.loans.filter((item) => item.status === 'overdue').length
  const portfolioOutstanding = state.loans.reduce((sum, item) => sum + item.outstandingPrincipal, 0)
  const cashCollected = state.payments.reduce((sum, item) => sum + item.totalAmount, 0)

  return {
    customers: state.customers.length,
    activeLoans,
    overdueLoans,
    collateralInCustody: state.collateralItems.filter((item) => item.status === 'in-custody').length,
    portfolioOutstanding,
    cashCollected
  }
})

export const useMockPlatformStore = () => ({
  state,
  dashboardStats,
  getCustomerName,
  getCustomerById,
  ensureInitialized,
  refreshAll,
  createCustomer,
  updateCustomer,
  createLoan,
  updateLoan,
  createCollateral,
  updateCollateral,
  createPayment,
  updateGlobalSettings
})
