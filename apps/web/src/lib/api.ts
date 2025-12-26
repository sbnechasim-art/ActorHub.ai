import axios from 'axios'
import {
  setupRetryInterceptor,
  setupRateLimitInterceptor,
  setupOfflineInterceptor,
} from './api-utils'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Debug: Log API URL on initialization
if (typeof window !== 'undefined') {
  if (process.env.NODE_ENV === 'development') console.log('[API Client] Initialized with baseURL:', API_URL)
}

export const api = axios.create({
  baseURL: API_URL,
  timeout: 120000, // 2 minutes timeout for face recognition
  headers: {
    'Content-Type': 'application/json',
  },
  // SECURITY: Use cookies for auth instead of localStorage
  // This enables httpOnly cookies to be sent automatically
  withCredentials: true,
})

// Setup interceptors for resilience
setupOfflineInterceptor(api)      // Check offline before requests
setupRateLimitInterceptor(api)    // Prevent API abuse
setupRetryInterceptor(api, {      // Auto-retry on failures
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
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
  is_public?: boolean // deprecated, use show_in_public_gallery
  show_in_public_gallery?: boolean
  allow_commercial_use?: boolean
  allow_ai_training?: boolean
  profile_image_url?: string
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
  identity_id?: string
  training_status: 'PENDING' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  training_progress: number
  training_started_at?: string
  training_completed_at?: string
  training_error?: string
  quality_score?: number
  authenticity_score?: number
  consistency_score?: number
  voice_quality_score?: number
  is_available: boolean
  components?: {
    face?: boolean
    voice?: boolean
    motion?: boolean
  }
  training_images_count?: number
  version?: string
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

// Helper to get cookie value
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null
  return null
}

// Request interceptor - cookies are sent automatically via withCredentials
// CSRF token must be read from cookie and sent in header
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    // Debug logging only in development
    if (process.env.NODE_ENV === 'development') {
      console.debug('[API Request]', config.method?.toUpperCase(), config.url)
    }

    // Add CSRF token for state-changing requests (POST, PUT, PATCH, DELETE)
    const method = config.method?.toUpperCase()
    if (method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const csrfToken = getCookie('_csrf')
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken
      }
    }
  }
  return config
})

// Handle errors with improved messaging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Import dynamically to avoid circular dependencies
    const status = error.response?.status
    const data = error.response?.data

    // Handle authentication errors
    if (status === 401) {
      // Only redirect if not already on auth pages
      if (typeof window !== 'undefined') {
        const isAuthPage = window.location.pathname.includes('/sign-in') ||
                          window.location.pathname.includes('/sign-up')
        if (!isAuthPage) {
          // Store current URL for redirect after login
          sessionStorage.setItem('redirectAfterLogin', window.location.pathname)
          window.location.href = '/sign-in'
        }
      }
    }

    // Enhance error message based on response
    if (data?.error?.message) {
      error.message = data.error.message
    } else if (data?.detail) {
      if (typeof data.detail === 'string') {
        error.message = data.detail
      } else if (Array.isArray(data.detail)) {
        error.message = data.detail.map((d: { msg: string }) => d.msg).join(', ')
      }
    }

    // Log errors in development
    if (process.env.NODE_ENV === 'development') {
      console.error('[API Error]', {
        status,
        url: error.config?.url,
        message: error.message,
        data: data,
      })
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
  delete: (id: string) =>
    api.delete(`/identity/${id}`).then((r) => r.data),
  verify: (data: { image_url?: string; image_base64?: string }) =>
    api.post('/identity/verify', data).then((r) => r.data),
  getPublicGallery: (skip = 0, limit = 50) =>
    api.get(`/identity/gallery?skip=${skip}&limit=${limit}`).then((r) => r.data),
}

export const userApi = {
  getMe: () => api.get('/users/me').then((r) => r.data),
  getDashboard: () => api.get('/users/me/dashboard').then((r) => r.data),
  updateMe: (data: any) => api.patch('/users/me', data).then((r) => r.data),
  getApiKeys: () => api.get('/users/api-keys').then((r) => r.data),
  createApiKey: (data: any) => api.post('/users/api-keys', data).then((r) => r.data),
  revokeApiKey: (id: string) => api.delete(`/users/api-keys/${id}`).then((r) => r.data),
  // Delete account (soft delete)
  deleteAccount: () => api.delete('/users/me').then((r) => r.data),
}

export const marketplaceApi = {
  getListings: (params?: any) =>
    api.get('/marketplace/listings', { params }).then((r) => r.data),
  getListing: (id: string) =>
    api.get(`/marketplace/listings/${id}`).then((r) => r.data),
  createListing: (data: any) =>
    api.post('/marketplace/listings', data).then((r) => r.data),
  deleteListing: (id: string) =>
    api.delete(`/marketplace/listings/${id}`).then((r) => r.data),
  getLicensePrice: (data: any) =>
    api.post('/marketplace/license/price', data).then((r) => r.data),
  purchaseLicense: (data: any) =>
    api.post('/marketplace/license/purchase', data).then((r) => r.data),
  getMyLicenses: () =>
    api.get('/marketplace/licenses/mine').then((r) => r.data),
  revokeLicense: (id: string) =>
    api.delete(`/marketplace/licenses/${id}`).then((r) => r.data),
}

export const refundApi = {
  requestRefund: (licenseId: string, reason: string) =>
    api.post('/refunds/request', { license_id: licenseId, reason }).then((r) => r.data),
  getRefundStatus: (refundId: string) =>
    api.get(`/refunds/status/${refundId}`).then((r) => r.data),
  getRefundHistory: () =>
    api.get('/refunds/history').then((r) => r.data),
  getRefundPolicy: () =>
    api.get('/refunds/policy').then((r) => r.data),
}

export interface ActorPackDownload {
  download_url: string
  expires_in_seconds: number
  file_size_mb: number
  version: string
  components: {
    face?: boolean
    voice?: boolean
    motion?: boolean
  }
  checksum?: string
}

export const actorPackApi = {
  getPublic: (params?: any) =>
    api.get('/actor-packs/public', { params }).then((r) => r.data),
  getStatus: (id: string) =>
    api.get(`/actor-packs/status/${id}`).then((r) => r.data),
  initTraining: (formData: FormData) =>
    api.post('/actor-packs/train', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data),
  // Download Actor Pack as licensee (requires valid license)
  download: (identityId: string): Promise<ActorPackDownload> =>
    api.get(`/actor-packs/download/${identityId}`).then((r) => r.data),
  // Download your own Actor Pack (for identity owners, no license needed)
  downloadOwn: (identityId: string): Promise<ActorPackDownload> =>
    api.get(`/actor-packs/download-own/${identityId}`).then((r) => r.data),
  pollTraining: (packId: string): Promise<ActorPack> =>
    api.post(`/actor-packs/poll-training/${packId}`).then((r) => r.data),
  // Get all user's actor packs with training status
  getMyPacks: (): Promise<ActorPack[]> =>
    api.get('/actor-packs/mine').then((r) => r.data),
  // Cancel an in-progress training
  cancelTraining: (packId: string) =>
    api.post(`/actor-packs/cancel/${packId}`).then((r) => r.data),
  // Delete an actor pack
  delete: (packId: string) =>
    api.delete(`/actor-packs/${packId}`).then((r) => r.data),
}

// Content Generation API
export interface GenerationRequest {
  license_id: string
  content_type: 'face' | 'voice' | 'motion'
  prompt: string
  negative_prompt?: string
  num_outputs?: number
}

export interface GenerationResponse {
  job_id: string
  status: string
  content_type: string
  outputs?: string[]
  output_url?: string
  estimated_time?: string
  error?: string
}

export const generationApi = {
  generate: (request: GenerationRequest) =>
    api.post<GenerationResponse>('/generate/generate', request).then((r) => r.data),
  getStatus: (jobId: string) =>
    api.get<GenerationResponse>(`/generate/status/${jobId}`).then((r) => r.data),
  getMyJobs: (limit = 10) =>
    api.get('/generate/my-jobs', { params: { limit } }).then((r) => r.data),
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
  // Get Stripe portal URL for subscription management
  getPortalUrl: () =>
    api.post<{ url: string }>('/subscriptions/portal').then((r) => r.data),
}

// 2FA Authentication API
export const twoFactorApi = {
  // Start 2FA setup - returns QR code and secret
  enable: () =>
    api.post<{ secret: string; qr_code: string; backup_codes: string[] }>('/auth/2fa/enable').then((r) => r.data),
  // Verify 2FA code to complete setup
  verify: (code: string) =>
    api.post('/auth/2fa/verify', { code }).then((r) => r.data),
  // Disable 2FA
  disable: (code: string) =>
    api.post('/auth/2fa/disable', { code }).then((r) => r.data),
  // Get 2FA status
  getStatus: () =>
    api.get<{ enabled: boolean; backup_codes_remaining: number }>('/auth/2fa/status').then((r) => r.data),
}

export interface CreatorEarning {
  id: string
  net_amount: number
  gross_amount: number
  platform_fee: number
  status: 'PENDING' | 'AVAILABLE' | 'PAID' | 'REFUNDED'
  description: string
  earned_at: string
  available_at?: string
  paid_at?: string
}

export interface EarningsSummary {
  pending_balance: number
  available_balance: number
  total_earned: number
  total_paid: number
  total_refunded: number
  currency: string
  minimum_payout: number
  holding_days: number
  next_available?: string
  can_request_payout: boolean
  recent_earnings: CreatorEarning[]
}

export const earningsApi = {
  getSummary: () =>
    api.get<EarningsSummary>('/users/earnings').then((r) => r.data),
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
