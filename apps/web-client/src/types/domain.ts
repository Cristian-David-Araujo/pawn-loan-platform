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

export interface Payment {
  id: number
  loanId: number
  paymentDate: string
  totalAmount: number
  allocatedToPenalty: number
  allocatedToInterest: number
  allocatedToFees: number
  allocatedToPrincipal: number
  paymentMethod: 'cash' | 'bank-transfer' | 'other'
  notes: string
  isReversed: boolean
  receiver?: UserSummary | null
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
}
