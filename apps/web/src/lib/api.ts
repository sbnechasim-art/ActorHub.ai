import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: API_URL,
  timeout: 120000, // 2 minutes timeout for face recognition
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface Identity {
  id: string
  user_id: string
  name: string
  display_name?: string
  bio?: string
  category?: string
  status: 'PENDING' | 'VERIFIED' | 'PROTECTED' | 'SUSPENDED'
  protection_level: 'BASIC' | 'STANDARD' | 'PREMIUM'
  is_public: boolean
  created_at: string
  updated_at: string
  verified_at?: string
  deleted_at?: string
  actor_pack?: ActorPack
  total_verifications?: number
  total_revenue?: number
}

export interface ActorPack {
  id: string
  identity_id: string
  training_status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  training_progress: number
  training_started_at?: string
  training_completed_at?: string
  training_error?: string
  quality_score?: number
  authenticity_score?: number
  consistency_score?: number
  is_available: boolean
}

export interface License {
  id: string
  identity_id: string
  licensee_id: string
  license_type: 'SINGLE_USE' | 'SUBSCRIPTION' | 'UNLIMITED' | 'CUSTOM'
  usage_type: 'PERSONAL' | 'COMMERCIAL' | 'EDITORIAL' | 'EDUCATIONAL'
  price_usd: number
  currency: string
  is_active: boolean
  payment_status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'REFUNDED' | 'DISPUTED'
  valid_from?: string
  valid_until?: string
  paid_at?: string
  created_at: string
  identity?: Identity
  // Computed (from backend)
  is_valid?: boolean
}

export interface Notification {
  id: string
  type: 'SYSTEM' | 'MARKETING' | 'SECURITY' | 'BILLING' | 'IDENTITY' | 'TRAINING' | 'DETECTION'
  title: string
  message: string
  action_url?: string
  is_read: boolean
  created_at: string
}

export interface AnalyticsDashboard {
  usage: {
    total_verifications: number
    total_generations: number
    total_api_calls: number
    period_start: string
    period_end: string
  }
  revenue: {
    total_revenue: number
    total_payouts: number
    net_earnings: number
    transaction_count: number
    currency: string
  }
  top_identities: Array<{
    identity_id: string
    identity_name: string
    verifications: number
    licenses_sold: number
    revenue: number
  }>
  usage_trend: Array<{ date: string; value: number }>
  revenue_trend: Array<{ date: string; value: number }>
}

export interface Payout {
  id: string
  amount: number
  currency: string
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  method: string
  created_at: string
  completed_at?: string
}

// Add auth token to requests
api.interceptors.request.use((config) => {
  // Get token from localStorage (set during login)
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/sign-in'
      }
    }
    return Promise.reject(error)
  }
)

// API functions
export const identityApi = {
  getMyIdentities: () => api.get('/identity/mine').then((r) => r.data),
  getIdentity: (id: string) => api.get(`/identity/${id}`).then((r) => r.data),
  register: (formData: FormData) =>
    api.post('/identity/register', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data),
  update: (id: string, data: any) =>
    api.patch(`/identity/${id}`, data).then((r) => r.data),
  verify: (data: { image_url?: string; image_base64?: string }) =>
    api.post('/identity/verify', data).then((r) => r.data),
}

export const userApi = {
  getMe: () => api.get('/users/me').then((r) => r.data),
  getDashboard: () => api.get('/users/me/dashboard').then((r) => r.data),
  updateMe: (data: any) => api.patch('/users/me', data).then((r) => r.data),
  getApiKeys: () => api.get('/users/api-keys').then((r) => r.data),
  createApiKey: (data: any) => api.post('/users/api-keys', data).then((r) => r.data),
  revokeApiKey: (id: string) => api.delete(`/users/api-keys/${id}`).then((r) => r.data),
}

export const marketplaceApi = {
  getListings: (params?: any) =>
    api.get('/marketplace/listings', { params }).then((r) => r.data),
  getListing: (id: string) =>
    api.get(`/marketplace/listings/${id}`).then((r) => r.data),
  createListing: (data: any) =>
    api.post('/marketplace/listings', data).then((r) => r.data),
  getLicensePrice: (data: any) =>
    api.post('/marketplace/license/price', data).then((r) => r.data),
  purchaseLicense: (data: any) =>
    api.post('/marketplace/license/purchase', data).then((r) => r.data),
  getMyLicenses: () =>
    api.get('/marketplace/licenses/mine').then((r) => r.data),
}

export const actorPackApi = {
  getPublic: (params?: any) =>
    api.get('/actor-pack/public', { params }).then((r) => r.data),
  getStatus: (id: string) =>
    api.get(`/actor-pack/status/${id}`).then((r) => r.data),
  initTraining: (formData: FormData) =>
    api.post('/actor-pack/train', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data),
  download: (identityId: string) =>
    api.get(`/actor-pack/download/${identityId}`).then((r) => r.data),
}

export const analyticsApi = {
  getDashboard: (days = 30) =>
    api.get<AnalyticsDashboard>('/analytics/dashboard', { params: { days } }).then((r) => r.data),
  getUsage: (days = 30, identityId?: string) =>
    api.get('/analytics/usage', { params: { days, identity_id: identityId } }).then((r) => r.data),
  getRevenue: (days = 30) =>
    api.get('/analytics/revenue', { params: { days } }).then((r) => r.data),
  getIdentityAnalytics: (identityId: string, days = 30) =>
    api.get(`/analytics/identity/${identityId}`, { params: { days } }).then((r) => r.data),
}

export const notificationsApi = {
  getAll: (params?: { is_read?: boolean; type?: string; limit?: number; offset?: number }) =>
    api.get<{ notifications: Notification[]; total: number; unread_count: number }>(
      '/notifications',
      { params }
    ).then((r) => r.data),
  getUnreadCount: () =>
    api.get<{ unread_count: number }>('/notifications/unread-count').then((r) => r.data),
  markAsRead: (id: string) =>
    api.post(`/notifications/${id}/read`).then((r) => r.data),
  markAllAsRead: () =>
    api.post('/notifications/read-all').then((r) => r.data),
  delete: (id: string) =>
    api.delete(`/notifications/${id}`).then((r) => r.data),
  getPreferences: () =>
    api.get('/notifications/preferences').then((r) => r.data),
  updatePreferences: (data: Record<string, boolean>) =>
    api.put('/notifications/preferences', data).then((r) => r.data),
}

export const subscriptionsApi = {
  getCurrent: () =>
    api.get('/subscriptions/current').then((r) => r.data),
  getPlans: () =>
    api.get('/subscriptions/plans').then((r) => r.data),
  getUsage: () =>
    api.get('/subscriptions/usage').then((r) => r.data),
  createCheckout: (data: { plan: string; interval: string }) =>
    api.post('/subscriptions/checkout', data).then((r) => r.data),
  cancel: () =>
    api.post('/subscriptions/cancel').then((r) => r.data),
  reactivate: () =>
    api.post('/subscriptions/reactivate').then((r) => r.data),
}

export const payoutsApi = {
  getSettings: () =>
    api.get('/users/payout-settings').then((r) => r.data),
  updateSettings: (data: Record<string, unknown>) =>
    api.put('/users/payout-settings', data).then((r) => r.data),
  getHistory: (params?: { limit?: number; offset?: number }) =>
    api.get<{ payouts: Payout[]; total: number }>('/admin/payouts/history', { params }).then((r) => r.data),
  requestPayout: () =>
    api.post('/users/request-payout').then((r) => r.data),
}

export interface ConnectStatus {
  connected: boolean
  details_submitted: boolean
  payouts_enabled: boolean
  charges_enabled?: boolean
  account_id: string | null
  requirements?: string[]
}

export interface ConnectOnboardingResponse {
  status: 'created' | 'pending' | 'complete'
  url?: string
  account_id: string
  message?: string
}

export const connectApi = {
  // Start Stripe Connect onboarding
  startOnboarding: () =>
    api.post<ConnectOnboardingResponse>('/users/connect/onboarding').then((r) => r.data),
  // Get Connect account status
  getStatus: () =>
    api.get<ConnectStatus>('/users/connect/status').then((r) => r.data),
  // Get link to Stripe Express dashboard
  getDashboardLink: () =>
    api.post<{ url: string }>('/users/connect/dashboard').then((r) => r.data),
}

export const licensesApi = {
  getMine: (params?: { status?: string; limit?: number; offset?: number }) =>
    api.get<{ licenses: License[]; total: number }>('/marketplace/licenses/mine', { params }).then((r) => r.data),
  getDetails: (id: string) =>
    api.get<License>(`/marketplace/licenses/${id}`).then((r) => r.data),
}

// ==========================================
// Admin API
// ==========================================

export interface AdminDashboardStats {
  total_users: number
  active_users: number
  total_identities: number
  total_actor_packs: number
  total_revenue: number
  revenue_this_month: number
  api_calls_today: number
  active_subscriptions: number
}

export interface AdminUser {
  id: string
  email: string
  display_name?: string
  first_name?: string
  last_name?: string
  role: 'USER' | 'CREATOR' | 'ADMIN'
  tier: 'FREE' | 'PRO' | 'ENTERPRISE'
  is_active: boolean
  is_verified?: boolean
  created_at: string
  last_login_at?: string
}

export interface AuditLogEntry {
  id: string
  user_email?: string
  action: string
  resource_type: string
  resource_id?: string
  description?: string
  ip_address?: string
  success: boolean
  created_at: string
}

export interface WebhookEvent {
  id: string
  event_id: string
  source: 'STRIPE' | 'CLERK' | 'REPLICATE'
  event_type: string
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  attempts: number
  error_message?: string
  created_at: string
}

export interface AdminPayout {
  id: string
  user_email: string
  amount: number
  currency: string
  method: string
  transaction_count: number
  requested_at: string
  status?: string
}

export const adminApi = {
  // Dashboard
  getDashboard: () =>
    api.get<AdminDashboardStats>('/admin/dashboard').then((r) => r.data),

  // Users
  getUsers: (params?: {
    role?: string
    tier?: string
    is_active?: boolean
    search?: string
    limit?: number
    offset?: number
  }) =>
    api.get<{ users: AdminUser[]; total: number }>('/admin/users', { params }).then((r) => r.data),

  getUser: (id: string) =>
    api.get<{ user: AdminUser; stats: { identities_count: number; total_spent: number } }>(`/admin/users/${id}`).then((r) => r.data),

  updateUser: (id: string, data: { role?: string; tier?: string; is_active?: boolean }) =>
    api.patch(`/admin/users/${id}`, null, { params: data }).then((r) => r.data),

  // Audit Logs
  getAuditLogs: (params?: {
    user_id?: string
    action?: string
    resource_type?: string
    limit?: number
    offset?: number
  }) =>
    api.get<{ logs: AuditLogEntry[]; total: number }>('/admin/audit-logs', { params }).then((r) => r.data),

  // Webhooks
  getWebhooks: (params?: {
    source?: string
    status?: string
    limit?: number
    offset?: number
  }) =>
    api.get<{ events: WebhookEvent[]; total: number }>('/admin/webhooks', { params }).then((r) => r.data),

  retryWebhook: (id: string) =>
    api.post(`/admin/webhooks/${id}/retry`).then((r) => r.data),

  // Payouts
  getPendingPayouts: () =>
    api.get<{ payouts: AdminPayout[] }>('/admin/payouts/pending').then((r) => r.data),

  approvePayout: (id: string) =>
    api.post<{ status: string; message: string; stripe_transfer_id?: string }>(`/admin/payouts/${id}/approve`).then((r) => r.data),
}
