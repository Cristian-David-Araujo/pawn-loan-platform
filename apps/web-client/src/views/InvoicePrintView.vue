<template>
  <div class="print-container">
    <div class="actions-bar no-print">
      <button class="btn btn-secondary" @click="router.back()">← {{ t('common.returnToSystem') }}</button>
      <button class="btn" @click="printDocument()">{{ t('common.printAgain') }}</button>
    </div>
    <div class="invoice-box" v-if="ready">
      <div class="invoice-header">
        <div class="company-details">
          <h2>{{ t('app.title') }}</h2>
          <p v-if="globalSettings?.currencyCode">
            {{ t('settings.currencyCode') }}: {{ globalSettings.currencyCode }}
          </p>
        </div>
        <div class="invoice-meta">
          <h1 v-if="isPayment">{{ t('payments.receiptTitle', 'Recibo de Pago') }}</h1>
          <h1 v-else>{{ t('loans.invoiceTitle', 'Factura de Préstamo') }}</h1>
          <p><strong>Nº:</strong> {{ idString }}</p>
          <p><strong>Fecha:</strong> {{ dateString }}</p>
        </div>
      </div>

      <!-- Customer info -->
      <div class="customer-info" v-if="customer">
        <h3>Datos del Cliente</h3>
        <p><strong>Nombre:</strong> {{ customer.fullName }}</p>
        <p><strong>{{ customer.documentType }}:</strong> {{ customer.documentNumber }}</p>
        <p><strong>Teléfono:</strong> {{ customer.phone }}</p>
      </div>

      <!-- Loan context (payment receipts) -->
      <div class="loan-info mt-16" v-if="isPayment && loan">
        <h3>{{ t('common.loanInfo') }}</h3>
        <div class="loan-info-grid">
          <p><strong>{{ t('common.loanNumber') }}:</strong> LN-{{ loan.id.toString().padStart(6, '0') }}</p>
          <p v-if="loan.description"><strong>{{ t('common.description') }}:</strong> {{ loan.description }}</p>
          <p><strong>{{ t('common.type') }}:</strong> {{ loan.loanType === 'pawn' ? t('common.pawn') : t('common.personal') }}</p>
          <p v-if="payment"><strong>{{ t('common.receiptPaymentType') }}:</strong> {{ getPaymentTypeLabel(payment) }}</p>
        </div>
      </div>

      <!-- Payment details table -->
      <div class="invoice-details mt-16">
        <template v-if="isPayment && payment">
          <table class="print-table">
            <thead>
              <tr>
                <th>Concepto</th>
                <th class="text-right">Monto</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="payment.allocatedToPrincipal > 0">
                <td>Abono a Capital</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
              </tr>
              <tr v-if="payment.allocatedToInterest > 0">
                <td>Intereses</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToInterest) }}</td>
              </tr>
              <tr v-if="payment.allocatedToPenalty > 0">
                <td>Mora / Penalización</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToPenalty) }}</td>
              </tr>
              <tr v-if="payment.allocatedToFees > 0">
                <td>Cargos / Comisiones</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToFees) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <th>TOTAL PAGADO</th>
                <th class="text-right">{{ formatCurrency(payment.totalAmount) }}</th>
              </tr>
            </tfoot>
          </table>
          <div class="payment-notes mt-16">
            <p><strong>Método de Pago:</strong> {{ payment.paymentMethod }}</p>
            <p v-if="payment.notes"><strong>Notas:</strong> {{ payment.notes }}</p>
          </div>
        </template>

        <template v-else-if="!isPayment && loan">
          <table class="print-table">
            <thead>
              <tr>
                <th>Detalles del Préstamo</th>
                <th class="text-right">Valor</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Monto Principal</td>
                <td class="text-right">{{ formatCurrency(loan.principalAmount) }}</td>
              </tr>
              <tr>
                <td>Tasa de Interés Mensual</td>
                <td class="text-right">{{ loan.monthlyInterestRate }}%</td>
              </tr>
              <tr v-if="loan.latePenaltyRate > 0">
                <td>Tasa de Penalización por Mora</td>
                <td class="text-right">{{ loan.latePenaltyRate }}%</td>
              </tr>
              <tr>
                <td>Día de Pago</td>
                <td class="text-right">{{ loan.dueDay }} de cada mes</td>
              </tr>
            </tbody>
          </table>
          <div class="payment-notes mt-16" v-if="loan.description">
            <p><strong>Descripción:</strong> {{ loan.description }}</p>
          </div>
        </template>
      </div>

      <!-- ── POST-PAYMENT BALANCES (the main new section) ── -->
      <div class="balances-section mt-16" v-if="isPayment && loan">
        <h3>{{ t('common.remainingBalancesTitle') }}</h3>
        <table class="print-table balances-table">
          <tbody>
            <tr>
              <td>{{ t('common.remainingPrincipal') }}</td>
              <td class="text-right balance-value" :class="{ 'balance-zero': loan.outstandingPrincipal === 0 }">
                {{ formatCurrency(loan.outstandingPrincipal) }}
              </td>
            </tr>
            <tr v-if="pendingInterestAfterPayment !== null">
              <td>{{ t('common.remainingInterest') }}</td>
              <td class="text-right balance-value" :class="{ 'balance-zero': pendingInterestAfterPayment === 0 }">
                {{ formatCurrency(pendingInterestAfterPayment) }}
              </td>
            </tr>
            <tr v-if="pendingPenaltyAfterPayment !== null && pendingPenaltyAfterPayment > 0">
              <td>{{ t('common.remainingPenalty') }}</td>
              <td class="text-right balance-value">
                {{ formatCurrency(pendingPenaltyAfterPayment) }}
              </td>
            </tr>
            <tr class="balance-total-row">
              <td><strong>{{ t('common.loanStatus') }}</strong></td>
              <td class="text-right">
                <span class="status-badge" :class="loanStatusClass">{{ loanStatusLabel }}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Loan closed notice -->
        <div class="closed-notice" v-if="loan.status === 'closed'">
          ✅ Este préstamo ha sido <strong>liquidado en su totalidad</strong>. ¡Gracias!
        </div>
      </div>

      <div class="invoice-footer">
        <p>Gracias por su confianza.</p>
        <p class="muted">Documento generado por {{ t('app.title') }}</p>
      </div>
    </div>
    
    <div v-else class="loading">
      Cargando documento...
    </div>

    <!-- The user prints from the browser, we auto-trigger on load -->
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platformStore'
import { formatDateDMY } from '../utils/date'
import { apiClient } from '../services/api'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { state, ensureInitialized } = usePlatformStore()

const type = computed(() => route.params.type as string)
const id = computed(() => Number(route.params.id))

const isPayment = computed(() => type.value === 'payment')
const ready = ref(false)

// Post-payment pending interest/penalty fetched from the API
const pendingInterestAfterPayment = ref<number | null>(null)
const pendingPenaltyAfterPayment = ref<number | null>(null)

const printDocument = () => {
  window.print()
}

const payment = computed(() => state.payments.find(p => p.id === id.value))
const loan = computed(() => {
  if (isPayment.value && payment.value) {
    return state.loans.find(l => l.id === payment.value!.loanId)
  } else if (!isPayment.value) {
    return state.loans.find(l => l.id === id.value)
  }
  return undefined
})
const customer = computed(() => {
  if (loan.value) {
    return state.customers.find(c => c.id === loan.value!.customerId)
  }
  return undefined
})

const globalSettings = computed(() => state.globalSettings)

const idString = computed(() => {
  if (isPayment.value) return `PAY-${id.value.toString().padStart(6, '0')}`
  return `LN-${id.value.toString().padStart(6, '0')}`
})

const dateString = computed(() => {
  if (isPayment.value && payment.value) {
    return formatDateDMY(payment.value.paymentDate)
  } else if (!isPayment.value && loan.value) {
    return formatDateDMY(loan.value.disbursementDate)
  }
  return ''
})

const formatCurrency = (val: number) => {
  const code = globalSettings.value?.currencyCode || 'COP'
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: code }).format(val)
}

/**
 * Human-readable label for the payment type derived from the allocation breakdown.
 * We infer the type from what was allocated since Payment model doesn't carry an explicit type field.
 */
const getPaymentTypeLabel = (p: typeof payment.value) => {
  if (!p) return ''
  if (p.allocatedToPrincipal > 0 && p.allocatedToInterest === 0) return 'Pago de Capital'
  if (p.allocatedToInterest > 0 && p.allocatedToPrincipal === 0) return 'Pago de Interés'
  if (p.allocatedToPenalty > 0 && p.allocatedToPrincipal === 0 && p.allocatedToInterest === 0) return 'Pago de Mora'
  return 'Pago Mixto'
}

const loanStatusLabel = computed(() => {
  if (!loan.value) return ''
  const map: Record<string, string> = {
    active: 'Activo',
    overdue: 'Vencido',
    closed: 'Liquidado'
  }
  return map[loan.value.status] ?? loan.value.status
})

const loanStatusClass = computed(() => {
  if (!loan.value) return ''
  return {
    'status-active': loan.value.status === 'active',
    'status-overdue': loan.value.status === 'overdue',
    'status-closed': loan.value.status === 'closed'
  }
})

onMounted(async () => {
  await ensureInitialized()

  // For payment receipts, fetch current interest/penalty pending for the customer
  // so we can show "remaining balances AFTER this payment" on the receipt
  if (isPayment.value && payment.value && loan.value) {
    try {
      const customerId = loan.value.customerId
      const res = await apiClient.request<{
        total_pending_interest: number
        total_pending_penalty: number
      }>(`/payments/customers/${customerId}/interest-pending`)
      pendingInterestAfterPayment.value = res.total_pending_interest
      pendingPenaltyAfterPayment.value = res.total_pending_penalty
    } catch {
      // Non-critical — if the call fails we simply don't show pending interest row
      pendingInterestAfterPayment.value = null
    }
  }

  ready.value = true
  setTimeout(() => {
    window.print()
  }, 500)
})
</script>

<style scoped>
.print-container {
  background: #f1f5f9;
  min-height: 100vh;
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.actions-bar {
  display: flex;
  justify-content: space-between;
  width: 100%;
  max-width: 800px;
  margin-bottom: 20px;
}

.invoice-box {
  background: white;
  width: 100%;
  max-width: 800px;
  padding: 40px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  color: #334155;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.invoice-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 20px;
  margin-bottom: 20px;
}

.company-details h2 {
  margin: 0 0 5px 0;
  color: #0f172a;
}

.invoice-meta h1 {
  margin: 0 0 10px 0;
  color: #3b82f6;
  font-size: 24px;
  text-align: right;
}

.invoice-meta p {
  margin: 0;
  text-align: right;
}

.customer-info h3, .loan-info h3, .balances-section h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 5px;
}

.customer-info p, .loan-info p {
  margin: 5px 0;
}

.loan-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 16px;
}

.print-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.print-table th, .print-table td {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.print-table th {
  background-color: #f8fafc;
  font-weight: 600;
  color: #475569;
}

.print-table tfoot th {
  background-color: #f1f5f9;
  font-size: 18px;
  color: #0f172a;
}

/* Balances section */
.balances-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
}

.balances-section h3 {
  color: #1e40af;
  border-bottom-color: #bfdbfe;
}

.balances-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
}

.balances-table .balance-total-row td {
  border-bottom: none;
  padding-top: 14px;
}

.balance-value {
  font-weight: 700;
  font-size: 1.05em;
  color: #0f172a;
}

.balance-zero {
  color: #16a34a !important;
}

/* Status badge */
.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.85em;
  font-weight: 600;
}

.status-active {
  background: #dcfce7;
  color: #15803d;
}

.status-overdue {
  background: #fee2e2;
  color: #dc2626;
}

.status-closed {
  background: #d1fae5;
  color: #065f46;
}

/* Closed notice */
.closed-notice {
  margin-top: 12px;
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  border-radius: 6px;
  padding: 12px 16px;
  color: #065f46;
  font-size: 0.95em;
}

.text-right {
  text-align: right !important;
}

.payment-notes {
  background: #f8fafc;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #3b82f6;
}

.invoice-footer {
  margin-top: 50px;
  text-align: center;
  border-top: 1px solid #e2e8f0;
  padding-top: 20px;
}

.muted {
  color: #94a3b8;
  font-size: 12px;
}

.loading {
  font-size: 1.2rem;
  color: #64748b;
  text-align: center;
  width: 100%;
  padding-top: 100px;
}

@media print {
  body * {
    visibility: hidden;
  }
  .no-print {
    display: none !important;
  }
  .print-container {
    background: transparent;
    padding: 0;
  }
  .invoice-box, .invoice-box * {
    visibility: visible;
  }
  .invoice-box {
    position: absolute;
    left: 0;
    top: 0;
    box-shadow: none;
    padding: 0;
    max-width: none;
    width: 100%;
  }
  @page {
    margin: 1.5cm;
  }
}
</style>
