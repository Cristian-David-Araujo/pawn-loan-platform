<template>
  <div class="print-container">
    <div class="actions-bar no-print">
      <button class="btn btn-secondary" @click="router.back()">← Volver al sistema</button>
      <button class="btn" @click="printDocument()">Imprimir Nuevamente</button>
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

      <div class="customer-info" v-if="customer">
        <h3>Datos del Cliente</h3>
        <p><strong>Nombre:</strong> {{ customer.fullName }}</p>
        <p><strong>{{ customer.documentType }}:</strong> {{ customer.documentNumber }}</p>
        <p><strong>Teléfono:</strong> {{ customer.phone }}</p>
      </div>

      <div class="loan-info mt-16" v-if="isPayment && loan">
        <h3>Información del Préstamo</h3>
        <p><strong>Nº Préstamo:</strong> LN-{{ loan.id.toString().padStart(6, '0') }}</p>
        <p v-if="loan.description"><strong>Descripción:</strong> {{ loan.description }}</p>
        <p><strong>Tipo de Préstamo:</strong> {{ loan.loanType === 'pawn' ? 'Prendario' : 'Personal' }}</p>
        <p><strong>Nuevo Saldo a Capital:</strong> {{ formatCurrency(loan.outstandingPrincipal) }}</p>
      </div>

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
              <tr>
                <td>Abono a Capital</td>
                <td class="text-right">{{ formatCurrency(payment.allocatedToPrincipal) }}</td>
              </tr>
              <tr>
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

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { state, ensureInitialized } = usePlatformStore()

const type = computed(() => route.params.type as string)
const id = computed(() => Number(route.params.id))

const isPayment = computed(() => type.value === 'payment')
const ready = ref(false)

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

onMounted(async () => {
  await ensureInitialized()
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

.customer-info h3, .loan-info h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 5px;
}

.customer-info p, .loan-info p {
  margin: 5px 0;
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
