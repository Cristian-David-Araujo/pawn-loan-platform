import axios from 'axios'

const API_BASE = '/api/v1'

const http = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' }
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const authApi = {
  async login(username: string, password: string) {
    const params = new URLSearchParams({ username, password })
    const res = await axios.post(`${API_BASE}/auth/login`, params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    return res.data
  },
  async getMe() {
    const res = await http.get('/users/me')
    return res.data
  }
}

// Customers
export const customersApi = {
  async list(params?: Record<string, unknown>) {
    const res = await http.get('/customers', { params })
    return res.data
  },
  async get(id: string) {
    const res = await http.get(`/customers/${id}`)
    return res.data
  },
  async create(data: Record<string, unknown>) {
    const res = await http.post('/customers', data)
    return res.data
  },
  async update(id: string, data: Record<string, unknown>) {
    const res = await http.put(`/customers/${id}`, data)
    return res.data
  }
}

// Loan Applications
export const loanApplicationsApi = {
  async list(params?: Record<string, unknown>) {
    const res = await http.get('/loan-applications', { params })
    return res.data
  },
  async create(data: Record<string, unknown>) {
    const res = await http.post('/loan-applications', data)
    return res.data
  },
  async approve(id: string) {
    const res = await http.post(`/loan-applications/${id}/approve`)
    return res.data
  },
  async reject(id: string, reason: string) {
    const res = await http.post(`/loan-applications/${id}/reject`, { rejection_reason: reason })
    return res.data
  }
}

// Loans
export const loansApi = {
  async list(params?: Record<string, unknown>) {
    const res = await http.get('/loans', { params })
    return res.data
  },
  async get(id: string) {
    const res = await http.get(`/loans/${id}`)
    return res.data
  },
  async create(data: Record<string, unknown>) {
    const res = await http.post('/loans', data)
    return res.data
  },
  async close(id: string) {
    const res = await http.post(`/loans/${id}/close`)
    return res.data
  },
  async renew(id: string, termMonths: number) {
    const res = await http.post(`/loans/${id}/renew?term_months=${termMonths}`)
    return res.data
  }
}

// Payments
export const paymentsApi = {
  async list(params?: Record<string, unknown>) {
    const res = await http.get('/payments', { params })
    return res.data
  },
  async create(data: Record<string, unknown>) {
    const res = await http.post('/payments', data)
    return res.data
  },
  async reverse(id: string, reason: string) {
    const res = await http.post(`/payments/${id}/reverse`, { reason })
    return res.data
  }
}

// Collateral
export const collateralApi = {
  async list(params?: Record<string, unknown>) {
    const res = await http.get('/collateral-items', { params })
    return res.data
  },
  async create(data: Record<string, unknown>) {
    const res = await http.post('/collateral-items', data)
    return res.data
  },
  async release(id: string) {
    const res = await http.post(`/collateral-items/${id}/release`, {})
    return res.data
  },
  async liquidate(id: string, saleAmount?: number) {
    const res = await http.post(`/collateral-items/${id}/liquidate`, { sale_amount: saleAmount })
    return res.data
  }
}

// Reports
export const reportsApi = {
  async activeLoans() {
    const res = await http.get('/reports/active-loans')
    return res.data
  },
  async overdueLoans() {
    const res = await http.get('/reports/overdue-loans')
    return res.data
  },
  async collateralCustody() {
    const res = await http.get('/reports/collateral-custody')
    return res.data
  },
  async cashSummary(dateFrom?: string, dateTo?: string) {
    const res = await http.get('/reports/cash-summary', { params: { date_from: dateFrom, date_to: dateTo } })
    return res.data
  }
}

export default http
