import { computed, ref } from 'vue'

function isoDate(value = new Date()) {
  return value.toISOString().slice(0, 10)
}

function cycleKey(dateString) {
  const d = new Date(dateString)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  return `${d.getFullYear()}-${month}`
}

function addDays(dateString, days) {
  const d = new Date(dateString)
  d.setDate(d.getDate() + days)
  return isoDate(d)
}

function nextMonthDate(dateString) {
  const d = new Date(dateString)
  d.setMonth(d.getMonth() + 1)
  return isoDate(d)
}

const customers = ref([
  {
    id: 'C-001',
    firstName: 'Maria',
    lastName: 'Torres',
    documentType: 'ID',
    documentNumber: '10001',
    phone: '555-0101',
    email: 'maria.torres@demo.local',
    city: 'Bogota',
    status: 'active',
    createdAt: addDays(isoDate(), -140),
    updatedAt: addDays(isoDate(), -2),
  },
  {
    id: 'C-002',
    firstName: 'Juan',
    lastName: 'Rios',
    documentType: 'ID',
    documentNumber: '10002',
    phone: '555-0102',
    email: 'juan.rios@demo.local',
    city: 'Medellin',
    status: 'active',
    createdAt: addDays(isoDate(), -112),
    updatedAt: addDays(isoDate(), -1),
  },
  {
    id: 'C-003',
    firstName: 'Sofia',
    lastName: 'Herrera',
    documentType: 'ID',
    documentNumber: '10003',
    phone: '555-0103',
    email: 'sofia.herrera@demo.local',
    city: 'Cali',
    status: 'active',
    createdAt: addDays(isoDate(), -95),
    updatedAt: addDays(isoDate(), -4),
  },
  {
    id: 'C-004',
    firstName: 'Luis',
    lastName: 'Mendoza',
    documentType: 'ID',
    documentNumber: '10004',
    phone: '555-0104',
    email: 'luis.mendoza@demo.local',
    city: 'Barranquilla',
    status: 'inactive',
    createdAt: addDays(isoDate(), -75),
    updatedAt: addDays(isoDate(), -10),
  },
  {
    id: 'C-005',
    firstName: 'Camila',
    lastName: 'Diaz',
    documentType: 'ID',
    documentNumber: '10005',
    phone: '555-0105',
    email: 'camila.diaz@demo.local',
    city: 'Pereira',
    status: 'active',
    createdAt: addDays(isoDate(), -53),
    updatedAt: addDays(isoDate(), -3),
  },
])

const applications = ref([
  {
    id: 'APP-001',
    customerId: 'C-001',
    loanType: 'pawn',
    requestedAmount: 1200,
    monthlyInterestRate: 7.5,
    termMonths: 6,
    notes: 'Gold jewelry backup',
    status: 'approved',
    reviewedBy: 'admin',
    approvedBy: 'admin',
    createdAt: addDays(isoDate(), -35),
    updatedAt: addDays(isoDate(), -33),
  },
  {
    id: 'APP-002',
    customerId: 'C-002',
    loanType: 'personal',
    requestedAmount: 900,
    monthlyInterestRate: 6.0,
    termMonths: 5,
    notes: 'Working capital',
    status: 'submitted',
    reviewedBy: null,
    approvedBy: null,
    createdAt: addDays(isoDate(), -3),
    updatedAt: addDays(isoDate(), -3),
  },
  {
    id: 'APP-003',
    customerId: 'C-003',
    loanType: 'pawn',
    requestedAmount: 2000,
    monthlyInterestRate: 6.5,
    termMonths: 8,
    notes: 'Electronics and watch collateral',
    status: 'approved',
    reviewedBy: 'officer_1',
    approvedBy: 'admin',
    createdAt: addDays(isoDate(), -28),
    updatedAt: addDays(isoDate(), -27),
  },
  {
    id: 'APP-004',
    customerId: 'C-005',
    loanType: 'personal',
    requestedAmount: 600,
    monthlyInterestRate: 7.0,
    termMonths: 4,
    notes: 'Seasonal inventory',
    status: 'rejected',
    reviewedBy: 'officer_2',
    approvedBy: null,
    createdAt: addDays(isoDate(), -16),
    updatedAt: addDays(isoDate(), -15),
  },
])

const loans = ref([
  {
    id: 'LN-001',
    applicationId: 'APP-001',
    customerId: 'C-001',
    loanType: 'pawn',
    principalAmount: 1200,
    outstandingPrincipal: 980,
    monthlyInterestRate: 7.5,
    disbursementDate: addDays(isoDate(), -33),
    nextDueDate: addDays(isoDate(), 6),
    status: 'active',
    accruedPenalty: 0,
    accruedInterest: 73.5,
    accruedFees: 5,
    lastInterestCycle: cycleKey(isoDate()),
    renewalOf: null,
    createdAt: addDays(isoDate(), -33),
    updatedAt: addDays(isoDate(), -2),
  },
  {
    id: 'LN-002',
    applicationId: 'APP-003',
    customerId: 'C-003',
    loanType: 'pawn',
    principalAmount: 2000,
    outstandingPrincipal: 1850,
    monthlyInterestRate: 6.5,
    disbursementDate: addDays(isoDate(), -27),
    nextDueDate: addDays(isoDate(), -12),
    status: 'overdue',
    accruedPenalty: 31,
    accruedInterest: 120.25,
    accruedFees: 12,
    lastInterestCycle: cycleKey(addDays(isoDate(), -1)),
    renewalOf: null,
    createdAt: addDays(isoDate(), -27),
    updatedAt: addDays(isoDate(), -1),
  },
  {
    id: 'LN-003',
    applicationId: 'APP-010',
    customerId: 'C-002',
    loanType: 'personal',
    principalAmount: 1500,
    outstandingPrincipal: 620,
    monthlyInterestRate: 6.2,
    disbursementDate: addDays(isoDate(), -62),
    nextDueDate: addDays(isoDate(), 2),
    status: 'active',
    accruedPenalty: 0,
    accruedInterest: 39.5,
    accruedFees: 0,
    lastInterestCycle: cycleKey(isoDate()),
    renewalOf: 'LN-000',
    createdAt: addDays(isoDate(), -62),
    updatedAt: addDays(isoDate(), -5),
  },
])

const collateralItems = ref([
  {
    id: 'COL-001',
    loanId: 'LN-001',
    description: '18K gold ring',
    serialNumber: 'GR-18K-100',
    appraisedValue: 1800,
    physicalCondition: 'good',
    custodyCode: 'A1-001',
    storageLocation: 'Shelf A1',
    status: 'in custody',
    createdAt: addDays(isoDate(), -33),
    updatedAt: addDays(isoDate(), -2),
  },
  {
    id: 'COL-002',
    loanId: 'LN-002',
    description: 'Gaming laptop',
    serialNumber: 'LP-GM-5521',
    appraisedValue: 2300,
    physicalCondition: 'fair',
    custodyCode: 'B4-014',
    storageLocation: 'Shelf B4',
    status: 'in custody',
    createdAt: addDays(isoDate(), -27),
    updatedAt: addDays(isoDate(), -3),
  },
  {
    id: 'COL-003',
    loanId: 'LN-002',
    description: 'Luxury watch',
    serialNumber: 'WT-LX-884',
    appraisedValue: 1400,
    physicalCondition: 'good',
    custodyCode: 'B4-015',
    storageLocation: 'Shelf B4',
    status: 'in custody',
    createdAt: addDays(isoDate(), -27),
    updatedAt: addDays(isoDate(), -3),
  },
])

const interestCharges = ref([
  {
    id: 'INT-0001',
    loanId: 'LN-001',
    periodStart: `${cycleKey(addDays(isoDate(), -1))}-01`,
    periodEnd: isoDate(),
    chargeDate: isoDate(),
    amount: 73.5,
    status: 'generated',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'INT-0002',
    loanId: 'LN-002',
    periodStart: `${cycleKey(addDays(isoDate(), -1))}-01`,
    periodEnd: addDays(isoDate(), -1),
    chargeDate: addDays(isoDate(), -1),
    amount: 120.25,
    status: 'generated',
    createdAt: new Date().toISOString(),
  },
])

const payments = ref([
  {
    id: 'PAY-0001',
    loanId: 'LN-001',
    paymentDate: addDays(isoDate(), -7),
    totalAmount: 220,
    allocatedToPenalty: 0,
    allocatedToInterest: 60,
    allocatedToFees: 5,
    allocatedToPrincipal: 155,
    paymentMethod: 'cash',
    receivedBy: 'cashier_1',
    status: 'applied',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'PAY-0002',
    loanId: 'LN-003',
    paymentDate: addDays(isoDate(), -2),
    totalAmount: 310,
    allocatedToPenalty: 0,
    allocatedToInterest: 39.5,
    allocatedToFees: 0,
    allocatedToPrincipal: 270.5,
    paymentMethod: 'bank_transfer',
    receivedBy: 'cashier_2',
    status: 'applied',
    createdAt: new Date().toISOString(),
  },
])

const auditLogs = ref([
  {
    id: 'AUD-0001',
    userId: 'admin',
    action: 'application.approved',
    entityType: 'LoanApplication',
    entityId: 'APP-001',
    oldData: null,
    newData: { status: 'approved' },
    createdAt: new Date().toISOString(),
  },
  {
    id: 'AUD-0002',
    userId: 'admin',
    action: 'loan.created',
    entityType: 'Loan',
    entityId: 'LN-001',
    oldData: null,
    newData: { status: 'active' },
    createdAt: new Date().toISOString(),
  },
  {
    id: 'AUD-0003',
    userId: 'cashier_1',
    action: 'payment.registered',
    entityType: 'Payment',
    entityId: 'PAY-0001',
    oldData: null,
    newData: { totalAmount: 220 },
    createdAt: new Date().toISOString(),
  },
])

function addAudit(action, entityType, entityId, oldData, newData) {
    auditLogs.value.unshift({
      id: `AUD-${String(auditLogs.value.length + 1).padStart(4, '0')}`,
      userId: 'admin',
      action,
      entityType,
      entityId,
      oldData,
      newData,
      createdAt: new Date().toISOString(),
    })
  }

function getCustomerName(customerId) {
    const customer = customers.value.find((item) => item.id === customerId)
    return customer ? `${customer.firstName} ${customer.lastName}` : 'Unknown'
  }

function createCustomer(payload) {
    const exists = customers.value.some(
      (item) => item.documentNumber === payload.documentNumber,
    )
    if (exists) {
      throw new Error('Document number already exists')
    }

    const newCustomer = {
      id: `C-${String(customers.value.length + 1).padStart(3, '0')}`,
      firstName: payload.firstName,
      lastName: payload.lastName,
      documentType: payload.documentType,
      documentNumber: payload.documentNumber,
      phone: payload.phone,
      email: payload.email,
      city: payload.city,
      status: 'active',
      createdAt: isoDate(),
      updatedAt: isoDate(),
    }

    customers.value.unshift(newCustomer)
    addAudit('customer.created', 'Customer', newCustomer.id, null, newCustomer)
  }

function createApplication(payload) {
    const application = {
      id: `APP-${String(applications.value.length + 1).padStart(3, '0')}`,
      customerId: payload.customerId,
      loanType: payload.loanType,
      requestedAmount: Number(payload.requestedAmount),
      monthlyInterestRate: Number(payload.monthlyInterestRate),
      termMonths: Number(payload.termMonths),
      notes: payload.notes || '',
      status: 'submitted',
      reviewedBy: null,
      approvedBy: null,
      createdAt: isoDate(),
      updatedAt: isoDate(),
    }

    applications.value.unshift(application)
    addAudit('application.created', 'LoanApplication', application.id, null, application)
  }

function reviewApplication(applicationId, decision, user = 'admin') {
    const application = applications.value.find((item) => item.id === applicationId)
    if (!application) return

    const oldData = { ...application }
    application.status = decision === 'approve' ? 'approved' : 'rejected'
    application.reviewedBy = user
    application.approvedBy = decision === 'approve' ? user : null
    application.updatedAt = isoDate()

    addAudit(
      `application.${decision}d`,
      'LoanApplication',
      application.id,
      oldData,
      { ...application },
    )
  }

function createLoanFromApplication(applicationId, payload = {}) {
    const application = applications.value.find((item) => item.id === applicationId)
    if (!application) {
      throw new Error('Application not found')
    }
    if (application.status !== 'approved') {
      throw new Error('Only approved applications can create loans')
    }

    const loan = {
      id: `LN-${String(loans.value.length + 1).padStart(3, '0')}`,
      applicationId: application.id,
      customerId: application.customerId,
      loanType: application.loanType,
      principalAmount: Number(payload.principalAmount || application.requestedAmount),
      outstandingPrincipal: Number(payload.principalAmount || application.requestedAmount),
      monthlyInterestRate: Number(payload.monthlyInterestRate || application.monthlyInterestRate),
      disbursementDate: payload.disbursementDate || isoDate(),
      nextDueDate: payload.nextDueDate || addDays(isoDate(), 30),
      status: 'active',
      accruedPenalty: 0,
      accruedInterest: 0,
      accruedFees: 0,
      lastInterestCycle: null,
      renewalOf: payload.renewalOf || null,
      createdAt: isoDate(),
      updatedAt: isoDate(),
    }

    loans.value.unshift(loan)
    addAudit('loan.created', 'Loan', loan.id, null, loan)
  }

function registerCollateral(payload) {
    const loan = loans.value.find((item) => item.id === payload.loanId)
    if (!loan) {
      throw new Error('Loan not found')
    }
    if (loan.loanType !== 'pawn') {
      throw new Error('Collateral is only allowed for pawn loans')
    }

    const item = {
      id: `COL-${String(collateralItems.value.length + 1).padStart(3, '0')}`,
      loanId: payload.loanId,
      description: payload.description,
      serialNumber: payload.serialNumber,
      appraisedValue: Number(payload.appraisedValue),
      physicalCondition: payload.physicalCondition || 'good',
      custodyCode: payload.custodyCode,
      storageLocation: payload.storageLocation,
      status: 'in custody',
      createdAt: isoDate(),
      updatedAt: isoDate(),
    }

    collateralItems.value.unshift(item)
    addAudit('collateral.registered', 'CollateralItem', item.id, null, item)
  }

function generateMonthlyInterest(referenceDate = isoDate()) {
    const cycle = cycleKey(referenceDate)
    let processed = 0

    loans.value.forEach((loan) => {
      if (loan.status !== 'active') return
      if (loan.lastInterestCycle === cycle) return

      const amount = Number(
        ((loan.outstandingPrincipal * loan.monthlyInterestRate) / 100).toFixed(2),
      )
      loan.accruedInterest = Number((loan.accruedInterest + amount).toFixed(2))
      loan.lastInterestCycle = cycle
      loan.updatedAt = isoDate()

      const charge = {
        id: `INT-${String(interestCharges.value.length + 1).padStart(4, '0')}`,
        loanId: loan.id,
        periodStart: `${cycle}-01`,
        periodEnd: referenceDate,
        chargeDate: referenceDate,
        amount,
        status: 'generated',
        createdAt: new Date().toISOString(),
      }
      interestCharges.value.unshift(charge)

      addAudit('interest.generated', 'InterestCharge', charge.id, null, charge)
      processed += 1
    })

    return processed
  }

function applyOverdue(graceDays = 0, referenceDate = isoDate()) {
    let affected = 0
    const now = new Date(referenceDate)

    loans.value.forEach((loan) => {
      if (loan.status !== 'active') return
      const dueDate = new Date(loan.nextDueDate)
      dueDate.setDate(dueDate.getDate() + Number(graceDays))

      if (now > dueDate) {
        loan.status = 'overdue'
        loan.updatedAt = isoDate()
        affected += 1
      }
    })

    return affected
  }

function allocatePayment(loan, totalAmount) {
    let remaining = Number(totalAmount)
    const allocation = {
      penalty: 0,
      interest: 0,
      fees: 0,
      principal: 0,
    }

    const penaltyPay = Math.min(remaining, loan.accruedPenalty)
    allocation.penalty = Number(penaltyPay.toFixed(2))
    loan.accruedPenalty = Number((loan.accruedPenalty - penaltyPay).toFixed(2))
    remaining = Number((remaining - penaltyPay).toFixed(2))

    const interestPay = Math.min(remaining, loan.accruedInterest)
    allocation.interest = Number(interestPay.toFixed(2))
    loan.accruedInterest = Number((loan.accruedInterest - interestPay).toFixed(2))
    remaining = Number((remaining - interestPay).toFixed(2))

    const feesPay = Math.min(remaining, loan.accruedFees)
    allocation.fees = Number(feesPay.toFixed(2))
    loan.accruedFees = Number((loan.accruedFees - feesPay).toFixed(2))
    remaining = Number((remaining - feesPay).toFixed(2))

    const principalPay = Math.min(remaining, loan.outstandingPrincipal)
    allocation.principal = Number(principalPay.toFixed(2))
    loan.outstandingPrincipal = Number((loan.outstandingPrincipal - principalPay).toFixed(2))

    if (
      loan.outstandingPrincipal <= 0 &&
      loan.accruedPenalty <= 0 &&
      loan.accruedInterest <= 0 &&
      loan.accruedFees <= 0
    ) {
      loan.status = 'closed'
    }

    loan.updatedAt = isoDate()
    return allocation
  }

function registerPayment(payload) {
    const loan = loans.value.find((item) => item.id === payload.loanId)
    if (!loan) {
      throw new Error('Loan not found')
    }

    const total = Number(payload.totalAmount)
    if (!Number.isFinite(total) || total <= 0) {
      throw new Error('Invalid payment amount')
    }

    const allocation = allocatePayment(loan, total)

    const payment = {
      id: `PAY-${String(payments.value.length + 1).padStart(4, '0')}`,
      loanId: payload.loanId,
      paymentDate: payload.paymentDate || isoDate(),
      totalAmount: total,
      allocatedToPenalty: allocation.penalty,
      allocatedToInterest: allocation.interest,
      allocatedToFees: allocation.fees,
      allocatedToPrincipal: allocation.principal,
      paymentMethod: payload.paymentMethod || 'cash',
      receivedBy: payload.receivedBy || 'cashier',
      status: 'applied',
      createdAt: new Date().toISOString(),
    }

    payments.value.unshift(payment)
    addAudit('payment.registered', 'Payment', payment.id, null, payment)
    return payment
  }

function renewLoan(loanId) {
    const loan = loans.value.find((item) => item.id === loanId)
    if (!loan) {
      throw new Error('Loan not found')
    }

    if (loan.outstandingPrincipal <= 0) {
      throw new Error('Cannot renew a fully paid loan')
    }

    const renewed = {
      id: `LN-${String(loans.value.length + 1).padStart(3, '0')}`,
      applicationId: loan.applicationId,
      customerId: loan.customerId,
      loanType: loan.loanType,
      principalAmount: loan.outstandingPrincipal,
      outstandingPrincipal: loan.outstandingPrincipal,
      monthlyInterestRate: loan.monthlyInterestRate,
      disbursementDate: isoDate(),
      nextDueDate: nextMonthDate(isoDate()),
      status: 'active',
      accruedPenalty: 0,
      accruedInterest: 0,
      accruedFees: 0,
      lastInterestCycle: null,
      renewalOf: loan.id,
      createdAt: isoDate(),
      updatedAt: isoDate(),
    }

    loan.status = 'renewed'
    loan.updatedAt = isoDate()
    loans.value.unshift(renewed)

    addAudit('loan.renewed', 'Loan', renewed.id, null, renewed)
  }

const applicationsEnriched = computed(() =>
    applications.value.map((item) => ({
      ...item,
      customerName: getCustomerName(item.customerId),
    })),
  )

const loansEnriched = computed(() =>
    loans.value.map((item) => ({
      ...item,
      customerName: getCustomerName(item.customerId),
      balance:
        item.outstandingPrincipal +
        item.accruedInterest +
        item.accruedPenalty +
        item.accruedFees,
    })),
  )

const dashboard = computed(() => {
    const active = loans.value.filter((item) => item.status === 'active').length
    const overdue = loans.value.filter((item) => item.status === 'overdue').length
    const outstandingPrincipal = loans.value.reduce(
      (sum, item) => sum + item.outstandingPrincipal,
      0,
    )
    const accruedInterest = loans.value.reduce(
      (sum, item) => sum + item.accruedInterest,
      0,
    )

    return {
      active,
      overdue,
      outstandingPrincipal,
      accruedInterest,
      collateralInCustody: collateralItems.value.filter((item) => item.status === 'in custody')
        .length,
      paymentsCount: payments.value.length,
    }
  })

const agingBuckets = computed(() => {
    const result = {
      '1-30': 0,
      '31-60': 0,
      '61-90': 0,
      '90+': 0,
    }

    const today = new Date()
    loans.value.forEach((loan) => {
      if (loan.status !== 'overdue') return
      const due = new Date(loan.nextDueDate)
      const days = Math.floor((today - due) / (1000 * 60 * 60 * 24))
      if (days <= 30) result['1-30'] += 1
      else if (days <= 60) result['31-60'] += 1
      else if (days <= 90) result['61-90'] += 1
      else result['90+'] += 1
    })

    return result
  })

export function useLoanStore() {
  return {
    customers,
    applications,
    loans,
    collateralItems,
    interestCharges,
    payments,
    auditLogs,
    applicationsEnriched,
    loansEnriched,
    dashboard,
    agingBuckets,
    createCustomer,
    createApplication,
    reviewApplication,
    createLoanFromApplication,
    registerCollateral,
    generateMonthlyInterest,
    applyOverdue,
    registerPayment,
    renewLoan,
  }
}
