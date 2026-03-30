import { computed, reactive } from 'vue'
import type { CollateralItem, Customer, Loan, LoanType, Payment } from '../types/domain'

interface CreateCustomerPayload {
  fullName: string
  documentType: string
  documentNumber: string
  phone: string
  city: string
}

interface CreateLoanPayload {
  customerId: number
  loanType: LoanType
  principalAmount: number
  monthlyInterestRate: number
  dueDay: number
}

interface CreateCollateralPayload {
  loanId: number
  description: string
  appraisedValue: number
  storageLocation: string
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

const state = reactive({
  customers: [
    {
      id: 1,
      fullName: 'Ana Torres',
      documentType: 'ID',
      documentNumber: 'AT-1001',
      phone: '555-1001',
      city: 'Monterrey',
      status: 'active'
    },
    {
      id: 2,
      fullName: 'Luis Medina',
      documentType: 'ID',
      documentNumber: 'LM-2001',
      phone: '555-2001',
      city: 'Guadalajara',
      status: 'active'
    }
  ] as Customer[],
  loans: [
    {
      id: 1,
      customerId: 1,
      loanType: 'pawn',
      principalAmount: 1200,
      outstandingPrincipal: 1000,
      monthlyInterestRate: 8,
      disbursementDate: '2026-03-05',
      dueDay: 5,
      status: 'active'
    },
    {
      id: 2,
      customerId: 2,
      loanType: 'personal',
      principalAmount: 900,
      outstandingPrincipal: 900,
      monthlyInterestRate: 7,
      disbursementDate: '2026-02-20',
      dueDay: 20,
      status: 'overdue'
    }
  ] as Loan[],
  collateralItems: [
    {
      id: 1,
      loanId: 1,
      description: 'Gold chain 14k',
      appraisedValue: 1800,
      custodyCode: 'CUST-1001',
      storageLocation: 'Vault A-01',
      status: 'in-custody'
    }
  ] as CollateralItem[],
  payments: [
    {
      id: 1,
      loanId: 1,
      paymentDate: '2026-03-20',
      totalAmount: 250,
      allocatedToPenalty: 0,
      allocatedToInterest: 80,
      allocatedToFees: 20,
      allocatedToPrincipal: 150,
      paymentMethod: 'cash'
    }
  ] as Payment[]
})

const nextId = (items: { id: number }[]) => (items.length ? Math.max(...items.map((item) => item.id)) + 1 : 1)

const getCustomerName = (customerId: number) => {
  const customer = state.customers.find((item) => item.id === customerId)
  return customer?.fullName ?? '__UNKNOWN_CUSTOMER__'
}

const createCustomer = (payload: CreateCustomerPayload) => {
  const duplicate = state.customers.some(
    (item) => item.documentType === payload.documentType && item.documentNumber === payload.documentNumber
  )

  if (duplicate) {
    return { ok: false, messageKey: 'messages.customerDocumentExists' }
  }

  state.customers.unshift({
    id: nextId(state.customers),
    ...payload,
    status: 'active'
  })

  return { ok: true, messageKey: 'messages.customerCreated' }
}

const createLoan = (payload: CreateLoanPayload) => {
  state.loans.unshift({
    id: nextId(state.loans),
    customerId: payload.customerId,
    loanType: payload.loanType,
    principalAmount: payload.principalAmount,
    outstandingPrincipal: payload.principalAmount,
    monthlyInterestRate: payload.monthlyInterestRate,
    disbursementDate: new Date().toISOString().slice(0, 10),
    dueDay: payload.dueDay,
    status: 'active'
  })
}

const createCollateral = (payload: CreateCollateralPayload) => {
  state.collateralItems.unshift({
    id: nextId(state.collateralItems),
    loanId: payload.loanId,
    description: payload.description,
    appraisedValue: payload.appraisedValue,
    custodyCode: `CUST-${String(nextId(state.collateralItems)).padStart(4, '0')}`,
    storageLocation: payload.storageLocation,
    status: 'in-custody'
  })
}

const createPayment = (payload: CreatePaymentPayload) => {
  const allocationSum =
    payload.allocatedToPenalty +
    payload.allocatedToInterest +
    payload.allocatedToFees +
    payload.allocatedToPrincipal

  if (allocationSum !== payload.totalAmount) {
    return { ok: false, messageKey: 'messages.allocationMustEqualTotal' }
  }

  state.payments.unshift({
    id: nextId(state.payments),
    loanId: payload.loanId,
    paymentDate: new Date().toISOString().slice(0, 10),
    totalAmount: payload.totalAmount,
    allocatedToPenalty: payload.allocatedToPenalty,
    allocatedToInterest: payload.allocatedToInterest,
    allocatedToFees: payload.allocatedToFees,
    allocatedToPrincipal: payload.allocatedToPrincipal,
    paymentMethod: payload.paymentMethod
  })

  const loan = state.loans.find((item) => item.id === payload.loanId)
  if (loan) {
    loan.outstandingPrincipal = Math.max(0, loan.outstandingPrincipal - payload.allocatedToPrincipal)
    if (loan.outstandingPrincipal === 0) {
      loan.status = 'closed'
    }
  }

  return { ok: true, messageKey: 'messages.paymentRegistered' }
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
  createCustomer,
  createLoan,
  createCollateral,
  createPayment
})
