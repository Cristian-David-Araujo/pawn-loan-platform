export type LoanType = 'pawn' | 'personal'
export type LoanStatus = 'active' | 'overdue' | 'defaulted' | 'closed'

export interface UserSummary {
  id: number
  username: string
  full_name: string
}

export interface Customer {
  id: number
  fullName: string
  documentType: string
  documentNumber: string
  phone: string
  email: string
  address: string
  city: string
  status: 'active' | 'archived'
  createdAt: string
  updatedAt: string
  created_by?: UserSummary | null
}

export interface Loan {
  id: number
  customerId: number
  loanType: LoanType
  description: string
  principalAmount: number
  outstandingPrincipal: number
  monthlyInterestRate: number
  latePenaltyRate: number
  disbursementDate: string
  dueDay: number
  interestDue?: number
  collateralsCount?: number
  status: LoanStatus
  /* Pausing the interest clock is a flag, not a status: a paused loan is still `active` or
     `overdue`, so the status alone cannot show it and cannot be used to find it again. */
  interestPaused: boolean
  interestPauseReason: string
  /* A settlement closes the loan as `closed`. These separate "paid off" from "we took what
     we could and wrote off the rest". */
  settledAt: string | null
  settlementAmount: number | null
  writtenOffPrincipal: number | null
  writtenOffInterest: number | null
  created_by?: UserSummary | null
}

export interface CollateralItem {
  id: number
  loanId: number
  itemType: string
  description: string
  serialNumber: string
  appraisedValue: number
  custodyCode: string
  storageLocation: string
  status: 'in-custody' | 'released' | 'liquidated' | 'for_sale' | 'sold' | 'returned'
  salePrice?: number | null
  soldAt?: string | null
  loanStatus?: string
  loanPrincipal?: number
  loanOutstanding?: number
  loanInterestDue?: number
  loanRate?: number
}

/** Shared so the collection form and its callers cannot disagree on the allowed values. */
export type PaymentMethod = 'cash' | 'bank-transfer' | 'other'

export interface Payment {
  id: number
  loanId: number
  paymentDate: string
  totalAmount: number
  allocatedToPenalty: number
  allocatedToInterest: number
  allocatedToFees: number
  allocatedToPrincipal: number
  paymentMethod: PaymentMethod
  notes: string
  isReversed: boolean
  reversedAt?: string | null
  reversalReason?: string
  receiver?: UserSummary | null
  reverser?: UserSummary | null
}

export interface GlobalSettings {
  id: number
  appName: string
  companyName: string | null
  companyDocumentType: string | null
  companyDocumentNumber: string | null
  companyAddress: string | null
  companyPhone: string | null
  companyEmail: string | null
  currencyCode: string
  timezone: string
  dateFormat: string
  defaultLatePenaltyRate: number
  interestGenerationLeadDays: number
  defaultGraceDays: number
}
