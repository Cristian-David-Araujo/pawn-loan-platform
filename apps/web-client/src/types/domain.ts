export type LoanType = 'pawn' | 'personal'
export type LoanStatus = 'active' | 'overdue' | 'closed'

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
}

export interface Loan {
  id: number
  customerId: number
  loanType: LoanType
  principalAmount: number
  outstandingPrincipal: number
  monthlyInterestRate: number
  disbursementDate: string
  dueDay: number
  status: LoanStatus
}

export interface CollateralItem {
  id: number
  loanId: number
  description: string
  appraisedValue: number
  custodyCode: string
  storageLocation: string
  status: 'in-custody' | 'released' | 'liquidated'
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
}
